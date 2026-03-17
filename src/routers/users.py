"""User and role management endpoints."""

import importlib

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

_auth = importlib.import_module("src.middleware.auth-middleware")
_role_service = importlib.import_module("src.services.role-service")

router = APIRouter(prefix="/users", tags=["users"])


class AssignRoleRequest(BaseModel):
    role: str


@router.get("/me")
async def get_current_user_profile(
    user: dict = Depends(_auth.get_current_user),
):
    """Get current user profile with roles."""
    return {
        "user_id": user["user_id"],
        "workspace_id": user["workspace_id"],
        "roles": user["roles"],
    }


@router.get("")
async def list_workspace_users(
    user: dict = Depends(_auth.require_role("admin")),
):
    """List all users in workspace with their roles (admin only)."""
    return await _role_service.list_workspace_users(user["workspace_id"])


@router.post("/{user_id}/roles", status_code=201)
async def assign_role(
    user_id: str,
    body: AssignRoleRequest,
    user: dict = Depends(_auth.require_role("admin")),
):
    """Assign a role to a user (admin only)."""
    try:
        return await _role_service.assign_role(
            user_id=user_id,
            workspace_id=user["workspace_id"],
            role=body.role,
            granted_by=user["user_id"],
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/{user_id}/roles/{role}")
async def remove_role(
    user_id: str,
    role: str,
    user: dict = Depends(_auth.require_role("admin")),
):
    """Remove a role from a user (admin only). Cannot remove own admin role."""
    # Prevent admin from removing their own admin role (lockout prevention)
    if user_id == user["user_id"] and role == "admin":
        raise HTTPException(400, "Cannot remove your own admin role")

    removed = await _role_service.remove_role(
        user_id=user_id,
        workspace_id=user["workspace_id"],
        role=role,
    )
    if not removed:
        raise HTTPException(404, "Role assignment not found")
    return {"removed": True}
