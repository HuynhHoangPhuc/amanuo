"""API key CRUD and session auth (email/password + JWT) — SQLAlchemy ORM."""

import hashlib
import importlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_session_factory
from src.models.workspace import ApiKeyORM, UserORM

_workspace_models = importlib.import_module("src.models.workspace")
ApiKey = _workspace_models.ApiKey
ApiKeyCreated = _workspace_models.ApiKeyCreated

# JWT config
_JWT_SECRET = (
    settings.jwt_secret
    if hasattr(settings, "jwt_secret") and settings.jwt_secret
    else secrets.token_urlsafe(32)
)
_JWT_ALGORITHM = "HS256"
_ACCESS_TOKEN_MINUTES = 15
_REFRESH_TOKEN_DAYS = 7


def _get_session():
    return get_session_factory()()


# --- API Key CRUD ---

async def create_api_key(workspace_id: str, name: str) -> ApiKeyCreated:
    """Generate a new API key. Returns the full key (shown only once)."""
    raw_key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = raw_key[:8]
    key_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    async with _get_session() as session:
        api_key = ApiKeyORM(
            id=key_id,
            workspace_id=workspace_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            is_active=1,
            created_at=now,
        )
        session.add(api_key)
        await session.commit()

    return ApiKeyCreated(id=key_id, name=name, key=raw_key, key_prefix=key_prefix)


async def list_api_keys(workspace_id: str) -> list[ApiKey]:
    """List API keys for a workspace (prefix only, never raw key)."""
    async with _get_session() as session:
        result = await session.execute(
            select(ApiKeyORM)
            .where(ApiKeyORM.workspace_id == workspace_id)
            .order_by(ApiKeyORM.created_at.desc())
        )
        rows = result.scalars().all()
        return [
            ApiKey(
                id=r.id,
                workspace_id=r.workspace_id,
                name=r.name,
                key_prefix=r.key_prefix,
                is_active=bool(r.is_active),
                created_at=r.created_at,
                last_used_at=r.last_used_at,
            )
            for r in rows
        ]


async def revoke_api_key(workspace_id: str, key_id: str) -> bool:
    """Revoke an API key (soft delete via is_active=0)."""
    async with _get_session() as session:
        result = await session.execute(
            update(ApiKeyORM)
            .where(ApiKeyORM.id == key_id, ApiKeyORM.workspace_id == workspace_id)
            .values(is_active=0)
        )
        await session.commit()
        return result.rowcount > 0


async def validate_key(key_hash: str) -> dict | None:
    """Lookup API key by hash. Returns dict or None."""
    async with _get_session() as session:
        result = await session.execute(
            select(ApiKeyORM).where(ApiKeyORM.key_hash == key_hash)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        return {"id": row.id, "workspace_id": row.workspace_id, "is_active": bool(row.is_active)}


async def update_key_last_used(key_id: str) -> None:
    """Update last_used_at for an API key (non-critical background call)."""
    try:
        async with _get_session() as session:
            await session.execute(
                update(ApiKeyORM)
                .where(ApiKeyORM.id == key_id)
                .values(last_used_at=datetime.now().isoformat())
            )
            await session.commit()
    except Exception:
        pass


# --- Session Auth (email/password + JWT) ---

async def register_user(email: str, password: str, workspace_id: str = "default") -> dict:
    """Register a new user with bcrypt-hashed password."""
    user_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()

    async with _get_session() as session:
        user = UserORM(
            id=user_id,
            email=email,
            password_hash=password_hash,
            workspace_id=workspace_id,
            is_active=1,
            created_at=now,
            updated_at=now,
        )
        session.add(user)
        await session.commit()

    return {"id": user_id, "email": email, "workspace_id": workspace_id}


async def login_user(email: str, password: str) -> dict | None:
    """Verify credentials and return JWT tokens. Returns None on failure."""
    async with _get_session() as session:
        result = await session.execute(
            select(UserORM).where(UserORM.email == email)
        )
        row = result.scalar_one_or_none()

        if not row or not row.is_active:
            return None
        if not bcrypt.checkpw(password.encode(), row.password_hash.encode()):
            return None

        now = datetime.now(timezone.utc)
        access_payload = {
            "sub": row.id,
            "workspace_id": row.workspace_id,
            "exp": now + timedelta(minutes=_ACCESS_TOKEN_MINUTES),
            "type": "access",
        }
        refresh_payload = {
            "sub": row.id,
            "workspace_id": row.workspace_id,
            "exp": now + timedelta(days=_REFRESH_TOKEN_DAYS),
            "type": "refresh",
        }
        access_token = jwt.encode(access_payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)
        refresh_token = jwt.encode(refresh_payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user_id": row.id,
            "workspace_id": row.workspace_id,
        }


def verify_token(token: str) -> dict | None:
    """Decode and verify JWT token. Returns payload or None."""
    try:
        payload = jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
        return {"user_id": payload["sub"], "workspace_id": payload["workspace_id"]}
    except jwt.PyJWTError:
        return None
