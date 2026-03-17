"""Role assignment CRUD service (RBAC)."""

import uuid
from datetime import datetime

from sqlalchemy import delete, select

from src.database import get_session_factory
import importlib as _il

_role_model = _il.import_module("src.models.role-assignment")
RoleAssignmentORM = _role_model.RoleAssignmentORM
VALID_ROLES = _role_model.VALID_ROLES


def _get_session():
    return get_session_factory()()


async def assign_role(
    user_id: str,
    workspace_id: str,
    role: str,
    granted_by: str | None = None,
) -> dict:
    """Assign a role to a user in a workspace (idempotent)."""
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role '{role}'. Must be one of: {', '.join(VALID_ROLES)}")

    async with _get_session() as session:
        # Check if already assigned (idempotent)
        existing = await session.execute(
            select(RoleAssignmentORM).where(
                RoleAssignmentORM.user_id == user_id,
                RoleAssignmentORM.workspace_id == workspace_id,
                RoleAssignmentORM.role == role,
            )
        )
        if existing.scalar_one_or_none():
            return {"user_id": user_id, "role": role, "status": "already_assigned"}

        assignment = RoleAssignmentORM(
            id=str(uuid.uuid4()),
            user_id=user_id,
            workspace_id=workspace_id,
            role=role,
            granted_by=granted_by,
            created_at=datetime.now().isoformat(),
        )
        session.add(assignment)
        await session.commit()

    return {"user_id": user_id, "role": role, "status": "assigned"}


async def remove_role(user_id: str, workspace_id: str, role: str) -> bool:
    """Remove a role from a user. Returns True if role was removed."""
    async with _get_session() as session:
        result = await session.execute(
            delete(RoleAssignmentORM).where(
                RoleAssignmentORM.user_id == user_id,
                RoleAssignmentORM.workspace_id == workspace_id,
                RoleAssignmentORM.role == role,
            )
        )
        await session.commit()
        return result.rowcount > 0


async def get_user_roles(user_id: str, workspace_id: str) -> list[str]:
    """Get all roles for a user in a workspace."""
    async with _get_session() as session:
        result = await session.execute(
            select(RoleAssignmentORM.role).where(
                RoleAssignmentORM.user_id == user_id,
                RoleAssignmentORM.workspace_id == workspace_id,
            )
        )
        return [row[0] for row in result.all()]


async def list_workspace_users(workspace_id: str) -> list[dict]:
    """List all users in a workspace with their roles."""
    from src.models.workspace import UserORM

    async with _get_session() as session:
        # Get all users in workspace
        users_result = await session.execute(
            select(UserORM).where(
                UserORM.workspace_id == workspace_id,
                UserORM.is_active == 1,
            )
        )
        users = users_result.scalars().all()

        # Get all role assignments for workspace
        roles_result = await session.execute(
            select(RoleAssignmentORM).where(
                RoleAssignmentORM.workspace_id == workspace_id,
            )
        )
        assignments = roles_result.scalars().all()

        # Group roles by user_id
        user_roles: dict[str, list[str]] = {}
        for a in assignments:
            user_roles.setdefault(a.user_id, []).append(a.role)

        return [
            {
                "id": u.id,
                "email": u.email,
                "display_name": u.display_name,
                "roles": user_roles.get(u.id, []),
                "created_at": u.created_at,
            }
            for u in users
        ]


async def has_role(user_id: str, workspace_id: str, role: str) -> bool:
    """Check if user has a specific role in workspace."""
    async with _get_session() as session:
        result = await session.execute(
            select(RoleAssignmentORM.id).where(
                RoleAssignmentORM.user_id == user_id,
                RoleAssignmentORM.workspace_id == workspace_id,
                RoleAssignmentORM.role == role,
            )
        )
        return result.scalar_one_or_none() is not None


async def check_permission(
    user_id: str, workspace_id: str, required_roles: list[str]
) -> bool:
    """Check if user has any of the required roles."""
    roles = await get_user_roles(user_id, workspace_id)
    # Admin has all permissions
    if "admin" in roles:
        return True
    return any(r in required_roles for r in roles)
