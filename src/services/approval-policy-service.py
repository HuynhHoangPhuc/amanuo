"""Approval policy CRUD service with config validation."""

import importlib
import json
import uuid
from datetime import datetime

from sqlalchemy import select, update

from src.database import get_session_factory

_policy_model = importlib.import_module("src.models.approval-policy")
ApprovalPolicyORM = _policy_model.ApprovalPolicyORM


def _get_session():
    return get_session_factory()()


def _validate_chain_config(config: dict) -> None:
    """Validate chain policy config: must have steps list with role + label."""
    steps = config.get("steps")
    if not steps or not isinstance(steps, list):
        raise ValueError("Chain config requires 'steps' list")
    for i, step in enumerate(steps):
        if "role" not in step:
            raise ValueError(f"Step {i} missing 'role'")
        if step["role"] not in ("reviewer", "approver"):
            raise ValueError(f"Step {i} role must be 'reviewer' or 'approver'")


def _validate_quorum_config(config: dict) -> None:
    """Validate quorum policy config: required, pool_size, pool_role."""
    required = config.get("required")
    pool_size = config.get("pool_size")
    if not isinstance(required, int) or required < 1:
        raise ValueError("Quorum config requires 'required' (positive int)")
    if not isinstance(pool_size, int) or pool_size < required:
        raise ValueError("Quorum config requires 'pool_size' >= 'required'")
    if not config.get("pool_role"):
        raise ValueError("Quorum config requires 'pool_role'")


def validate_config(policy_type: str, config: dict) -> None:
    """Validate policy config based on type."""
    if policy_type == "chain":
        _validate_chain_config(config)
    elif policy_type == "quorum":
        _validate_quorum_config(config)
    else:
        raise ValueError(f"Invalid policy_type: {policy_type}")


async def create_policy(
    workspace_id: str,
    name: str,
    policy_type: str,
    config: dict,
    deadline_hours: int | None = None,
) -> dict:
    """Create an approval policy with validated config."""
    validate_config(policy_type, config)

    policy_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    async with _get_session() as session:
        policy = ApprovalPolicyORM(
            id=policy_id,
            workspace_id=workspace_id,
            name=name,
            policy_type=policy_type,
            config=json.dumps(config),
            deadline_hours=deadline_hours,
            is_active=1,
            created_at=now,
            updated_at=now,
        )
        session.add(policy)
        await session.commit()

    return _to_dict(policy)


async def update_policy(
    policy_id: str,
    workspace_id: str,
    name: str | None = None,
    config: dict | None = None,
    deadline_hours: int | None = None,
) -> dict | None:
    """Update policy. Only allowed if no active rounds reference it."""
    async with _get_session() as session:
        result = await session.execute(
            select(ApprovalPolicyORM).where(
                ApprovalPolicyORM.id == policy_id,
                ApprovalPolicyORM.workspace_id == workspace_id,
                ApprovalPolicyORM.is_active == 1,
            )
        )
        policy = result.scalar_one_or_none()
        if not policy:
            return None

        # Check for active rounds referencing this policy
        _round_model = importlib.import_module("src.models.review-round")
        active_rounds = await session.execute(
            select(_round_model.ReviewRoundORM.id).where(
                _round_model.ReviewRoundORM.policy_id == policy_id,
                _round_model.ReviewRoundORM.status.in_(("pending", "in_progress")),
            ).limit(1)
        )
        if active_rounds.scalar_one_or_none():
            raise ValueError("Cannot update policy with active review rounds")

        values = {"updated_at": datetime.now().isoformat()}
        if name is not None:
            values["name"] = name
        if config is not None:
            validate_config(policy.policy_type, config)
            values["config"] = json.dumps(config)
        if deadline_hours is not None:
            values["deadline_hours"] = deadline_hours

        await session.execute(
            update(ApprovalPolicyORM)
            .where(ApprovalPolicyORM.id == policy_id)
            .values(**values)
        )
        await session.commit()

        # Re-fetch
        result = await session.execute(
            select(ApprovalPolicyORM).where(ApprovalPolicyORM.id == policy_id)
        )
        return _to_dict(result.scalar_one())


async def delete_policy(policy_id: str, workspace_id: str) -> bool:
    """Soft-delete a policy (is_active=0)."""
    async with _get_session() as session:
        result = await session.execute(
            update(ApprovalPolicyORM)
            .where(
                ApprovalPolicyORM.id == policy_id,
                ApprovalPolicyORM.workspace_id == workspace_id,
            )
            .values(is_active=0, updated_at=datetime.now().isoformat())
        )
        await session.commit()
        return result.rowcount > 0


async def get_policy(policy_id: str, workspace_id: str) -> dict | None:
    """Get a single policy by ID."""
    async with _get_session() as session:
        result = await session.execute(
            select(ApprovalPolicyORM).where(
                ApprovalPolicyORM.id == policy_id,
                ApprovalPolicyORM.workspace_id == workspace_id,
                ApprovalPolicyORM.is_active == 1,
            )
        )
        row = result.scalar_one_or_none()
        return _to_dict(row) if row else None


async def list_policies(workspace_id: str) -> list[dict]:
    """List all active policies in workspace."""
    async with _get_session() as session:
        result = await session.execute(
            select(ApprovalPolicyORM)
            .where(
                ApprovalPolicyORM.workspace_id == workspace_id,
                ApprovalPolicyORM.is_active == 1,
            )
            .order_by(ApprovalPolicyORM.created_at.desc())
        )
        return [_to_dict(r) for r in result.scalars().all()]


def _to_dict(row: ApprovalPolicyORM) -> dict:
    return {
        "id": row.id,
        "workspace_id": row.workspace_id,
        "name": row.name,
        "policy_type": row.policy_type,
        "config": json.loads(row.config),
        "deadline_hours": row.deadline_hours,
        "is_active": bool(row.is_active),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }
