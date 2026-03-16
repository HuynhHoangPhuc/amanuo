"""Workspace CRUD operations — SQLAlchemy ORM."""

import importlib
import uuid
from datetime import datetime

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session_factory
from src.models.workspace import WorkspaceORM

_workspace_models = importlib.import_module("src.models.workspace")
Workspace = _workspace_models.Workspace


def _get_session():
    return get_session_factory()()


async def create_workspace(name: str) -> Workspace:
    """Create a new workspace."""
    ws_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    async with _get_session() as session:
        workspace = WorkspaceORM(id=ws_id, name=name, created_at=now, updated_at=now)
        session.add(workspace)
        await session.commit()

    return Workspace(id=ws_id, name=name, created_at=now, updated_at=now)


async def get_workspace(workspace_id: str) -> Workspace | None:
    """Get workspace by ID."""
    async with _get_session() as session:
        result = await session.execute(
            select(WorkspaceORM).where(WorkspaceORM.id == workspace_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        return Workspace(id=row.id, name=row.name, created_at=row.created_at, updated_at=row.updated_at)


async def list_workspaces() -> list[Workspace]:
    """List all workspaces."""
    async with _get_session() as session:
        result = await session.execute(
            select(WorkspaceORM).order_by(WorkspaceORM.created_at.desc())
        )
        rows = result.scalars().all()
        return [
            Workspace(id=r.id, name=r.name, created_at=r.created_at, updated_at=r.updated_at)
            for r in rows
        ]


async def delete_workspace(workspace_id: str) -> bool:
    """Delete a workspace. Cannot delete 'default'."""
    if workspace_id == "default":
        return False

    async with _get_session() as session:
        result = await session.execute(
            delete(WorkspaceORM).where(WorkspaceORM.id == workspace_id)
        )
        await session.commit()
        return result.rowcount > 0
