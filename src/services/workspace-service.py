"""Workspace CRUD operations."""

import importlib
import uuid
from datetime import datetime

from src.config import settings
from src.database import get_connection, get_db_path

_workspace_models = importlib.import_module("src.models.workspace")
Workspace = _workspace_models.Workspace


async def _get_db():
    return await get_connection(get_db_path(settings.database_url))


async def create_workspace(name: str) -> Workspace:
    """Create a new workspace."""
    ws_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    db = await _get_db()
    try:
        await db.execute(
            "INSERT INTO workspaces (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (ws_id, name, now, now),
        )
        await db.commit()
    finally:
        await db.close()

    return Workspace(id=ws_id, name=name, created_at=now, updated_at=now)


async def get_workspace(workspace_id: str) -> Workspace | None:
    """Get workspace by ID."""
    db = await _get_db()
    try:
        cursor = await db.execute("SELECT * FROM workspaces WHERE id = ?", (workspace_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return Workspace(id=row["id"], name=row["name"], created_at=row["created_at"], updated_at=row["updated_at"])
    finally:
        await db.close()


async def list_workspaces() -> list[Workspace]:
    """List all workspaces."""
    db = await _get_db()
    try:
        cursor = await db.execute("SELECT * FROM workspaces ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [
            Workspace(id=r["id"], name=r["name"], created_at=r["created_at"], updated_at=r["updated_at"])
            for r in rows
        ]
    finally:
        await db.close()


async def delete_workspace(workspace_id: str) -> bool:
    """Delete a workspace. Cannot delete 'default'."""
    if workspace_id == "default":
        return False

    db = await _get_db()
    try:
        cursor = await db.execute("DELETE FROM workspaces WHERE id = ?", (workspace_id,))
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()
