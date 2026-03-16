"""FastAPI dependency for workspace authentication via API key or JWT."""

import asyncio
import hashlib
import logging

from fastapi import HTTPException, Request

from src.config import settings
from src.database import get_connection, get_db_path

logger = logging.getLogger(__name__)


async def get_workspace_id(request: Request) -> str:
    """Extract workspace_id from API key header. Defaults to 'default' workspace."""
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return "default"

    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    db = await get_connection(get_db_path(settings.database_url))
    try:
        cursor = await db.execute(
            "SELECT id, workspace_id, is_active FROM api_keys WHERE key_hash = ?",
            (key_hash,),
        )
        record = await cursor.fetchone()
        if not record or not record["is_active"]:
            raise HTTPException(401, "Invalid or inactive API key")

        asyncio.create_task(_update_last_used(record["id"]))
        return record["workspace_id"]
    finally:
        await db.close()


async def _update_last_used(key_id: str) -> None:
    """Non-critical background update of last_used_at timestamp."""
    try:
        db = await get_connection(get_db_path(settings.database_url))
        try:
            await db.execute(
                "UPDATE api_keys SET last_used_at = datetime('now') WHERE id = ?",
                (key_id,),
            )
            await db.commit()
        finally:
            await db.close()
    except Exception:
        pass
