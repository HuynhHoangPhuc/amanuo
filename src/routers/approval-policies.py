"""Approval policy CRUD endpoints (admin-only management)."""

import importlib

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

_auth = importlib.import_module("src.middleware.auth-middleware")
_policy_service = importlib.import_module("src.services.approval-policy-service")

router = APIRouter(prefix="/approval-policies", tags=["approval-policies"])


class ApprovalPolicyCreate(BaseModel):
    name: str
    policy_type: str  # "chain" | "quorum"
    config: dict
    deadline_hours: int | None = None


class ApprovalPolicyUpdate(BaseModel):
    name: str | None = None
    config: dict | None = None
    deadline_hours: int | None = None


@router.get("")
async def list_policies(
    user: dict = Depends(_auth.get_current_user),
):
    """List all active approval policies in workspace."""
    return await _policy_service.list_policies(user["workspace_id"])


@router.post("", status_code=201)
async def create_policy(
    body: ApprovalPolicyCreate,
    user: dict = Depends(_auth.require_role("admin")),
):
    """Create a new approval policy (admin only)."""
    try:
        return await _policy_service.create_policy(
            workspace_id=user["workspace_id"],
            name=body.name,
            policy_type=body.policy_type,
            config=body.config,
            deadline_hours=body.deadline_hours,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/{policy_id}")
async def get_policy(
    policy_id: str,
    user: dict = Depends(_auth.get_current_user),
):
    """Get approval policy detail."""
    policy = await _policy_service.get_policy(policy_id, user["workspace_id"])
    if not policy:
        raise HTTPException(404, "Policy not found")
    return policy


@router.put("/{policy_id}")
async def update_policy(
    policy_id: str,
    body: ApprovalPolicyUpdate,
    user: dict = Depends(_auth.require_role("admin")),
):
    """Update an approval policy (admin only)."""
    try:
        result = await _policy_service.update_policy(
            policy_id=policy_id,
            workspace_id=user["workspace_id"],
            name=body.name,
            config=body.config,
            deadline_hours=body.deadline_hours,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not result:
        raise HTTPException(404, "Policy not found")
    return result


@router.delete("/{policy_id}")
async def delete_policy(
    policy_id: str,
    user: dict = Depends(_auth.require_role("admin")),
):
    """Soft-delete an approval policy (admin only)."""
    deleted = await _policy_service.delete_policy(policy_id, user["workspace_id"])
    if not deleted:
        raise HTTPException(404, "Policy not found")
    return {"deleted": True}
