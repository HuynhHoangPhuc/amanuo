"""API key CRUD and session auth (email/password + JWT)."""

import hashlib
import importlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from src.config import settings
from src.database import get_connection, get_db_path

_workspace_models = importlib.import_module("src.models.workspace")
ApiKey = _workspace_models.ApiKey
ApiKeyCreated = _workspace_models.ApiKeyCreated

# JWT config — operator should set JWT_SECRET in .env for production
_JWT_SECRET = settings.jwt_secret if hasattr(settings, "jwt_secret") and settings.jwt_secret else secrets.token_urlsafe(32)
_JWT_ALGORITHM = "HS256"
_ACCESS_TOKEN_MINUTES = 15
_REFRESH_TOKEN_DAYS = 7


async def _get_db():
    return await get_connection(get_db_path(settings.database_url))


# --- API Key CRUD ---

async def create_api_key(workspace_id: str, name: str) -> ApiKeyCreated:
    """Generate a new API key. Returns the full key (shown only once)."""
    raw_key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = raw_key[:8]
    key_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    db = await _get_db()
    try:
        await db.execute(
            """INSERT INTO api_keys (id, workspace_id, name, key_hash, key_prefix, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (key_id, workspace_id, name, key_hash, key_prefix, now),
        )
        await db.commit()
    finally:
        await db.close()

    return ApiKeyCreated(id=key_id, name=name, key=raw_key, key_prefix=key_prefix)


async def list_api_keys(workspace_id: str) -> list[ApiKey]:
    """List API keys for a workspace (prefix only, never raw key)."""
    db = await _get_db()
    try:
        cursor = await db.execute(
            "SELECT id, workspace_id, name, key_prefix, is_active, created_at, last_used_at "
            "FROM api_keys WHERE workspace_id = ? ORDER BY created_at DESC",
            (workspace_id,),
        )
        rows = await cursor.fetchall()
        return [
            ApiKey(
                id=r["id"], workspace_id=r["workspace_id"], name=r["name"],
                key_prefix=r["key_prefix"], is_active=bool(r["is_active"]),
                created_at=r["created_at"], last_used_at=r["last_used_at"],
            )
            for r in rows
        ]
    finally:
        await db.close()


async def revoke_api_key(workspace_id: str, key_id: str) -> bool:
    """Revoke an API key (soft delete via is_active=0)."""
    db = await _get_db()
    try:
        cursor = await db.execute(
            "UPDATE api_keys SET is_active = 0 WHERE id = ? AND workspace_id = ?",
            (key_id, workspace_id),
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def validate_key(key_hash: str) -> dict | None:
    """Lookup API key by hash. Returns row dict or None."""
    db = await _get_db()
    try:
        cursor = await db.execute(
            "SELECT id, workspace_id, is_active FROM api_keys WHERE key_hash = ?",
            (key_hash,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return {"id": row["id"], "workspace_id": row["workspace_id"], "is_active": bool(row["is_active"])}
    finally:
        await db.close()


# --- Session Auth (email/password + JWT) ---

async def register_user(email: str, password: str, workspace_id: str = "default") -> dict:
    """Register a new user with bcrypt-hashed password."""
    user_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()

    db = await _get_db()
    try:
        await db.execute(
            """INSERT INTO users (id, email, password_hash, workspace_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, email, password_hash, workspace_id, now, now),
        )
        await db.commit()
    finally:
        await db.close()

    return {"id": user_id, "email": email, "workspace_id": workspace_id}


async def login_user(email: str, password: str) -> dict | None:
    """Verify credentials and return JWT tokens. Returns None on failure."""
    db = await _get_db()
    try:
        cursor = await db.execute(
            "SELECT id, email, password_hash, workspace_id, is_active FROM users WHERE email = ?",
            (email,),
        )
        row = await cursor.fetchone()
        if not row or not row["is_active"]:
            return None

        if not bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
            return None

        now = datetime.now(timezone.utc)
        access_payload = {
            "sub": row["id"], "workspace_id": row["workspace_id"],
            "exp": now + timedelta(minutes=_ACCESS_TOKEN_MINUTES), "type": "access",
        }
        refresh_payload = {
            "sub": row["id"], "workspace_id": row["workspace_id"],
            "exp": now + timedelta(days=_REFRESH_TOKEN_DAYS), "type": "refresh",
        }
        access_token = jwt.encode(access_payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)
        refresh_token = jwt.encode(refresh_payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user_id": row["id"],
            "workspace_id": row["workspace_id"],
        }
    finally:
        await db.close()


def verify_token(token: str) -> dict | None:
    """Decode and verify JWT token. Returns payload or None."""
    try:
        payload = jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
        return {"user_id": payload["sub"], "workspace_id": payload["workspace_id"]}
    except jwt.PyJWTError:
        return None
