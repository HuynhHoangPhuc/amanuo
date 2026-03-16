"""FastAPI dependency for workspace authentication via API key or JWT."""

import asyncio
import hashlib
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


def _get_auth_service():
    """Lazy import to avoid circular dependency at startup."""
    import importlib
    return importlib.import_module("src.services.auth-service")
