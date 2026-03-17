"""FastAPI dependency for workspace authentication via API key or JWT."""

import asyncio
import hashlib
import importlib
import logging

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


async def get_workspace_id(request: Request) -> str:
    """Extract workspace_id from API key header. Defaults to 'default' workspace."""
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return "default"

    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    # Import lazily to avoid circular imports at module load time
    _auth_service = _get_auth_service()
    record = await _auth_service.validate_key(key_hash)

    if not record or not record["is_active"]:
        raise HTTPException(401, "Invalid or inactive API key")

    asyncio.create_task(_auth_service.update_key_last_used(record["id"]))
    return record["workspace_id"]


async def get_current_user(request: Request) -> dict:
    """Extract user context from JWT Bearer token or API key.

    Returns dict with user_id, workspace_id, roles.
    For API key auth (no JWT), treats as admin for backward compatibility.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        _auth_service = _get_auth_service()
        payload = _auth_service.verify_token(token)
        if not payload:
            raise HTTPException(401, "Invalid or expired token")
        return {
            "user_id": payload["user_id"],
            "workspace_id": payload["workspace_id"],
            "roles": payload.get("roles", []),
        }

    # Fallback to API key auth — treat as admin (backward compat)
    api_key = request.headers.get("X-API-Key")
    if api_key:
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        _auth_service = _get_auth_service()
        record = await _auth_service.validate_key(key_hash)
        if not record or not record["is_active"]:
            raise HTTPException(401, "Invalid or inactive API key")
        asyncio.create_task(_auth_service.update_key_last_used(record["id"]))
        return {
            "user_id": "api-key",
            "workspace_id": record["workspace_id"],
            "roles": ["admin"],
        }

    raise HTTPException(401, "Authentication required")


def require_role(*roles: str):
    """Dependency factory: returns 403 if user lacks any of the required roles.

    Usage: Depends(require_role('admin', 'reviewer'))
    """
    async def _check_role(request: Request) -> dict:
        user = await get_current_user(request)
        user_roles = user.get("roles", [])
        # Admin always passes
        if "admin" in user_roles:
            return user
        if not any(r in user_roles for r in roles):
            raise HTTPException(403, f"Requires one of: {', '.join(roles)}")
        return user
    return _check_role


def _get_auth_service():
    """Lazy import to avoid circular dependency at startup."""
    return importlib.import_module("src.services.auth-service")
