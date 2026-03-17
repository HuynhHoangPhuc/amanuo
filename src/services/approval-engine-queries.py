"""Read-only query functions for approval engine (status, audit log, events)."""

import importlib
import json

from sqlalchemy import select

from src.database import get_session_factory

_round_model = importlib.import_module("src.models.review-round")
_assign_model = importlib.import_module("src.models.review-assignment")
_audit_model = importlib.import_module("src.models.review-audit-log")
_policy_model = importlib.import_module("src.models.approval-policy")

ReviewRoundORM = _round_model.ReviewRoundORM
ReviewAssignmentORM = _assign_model.ReviewAssignmentORM
ReviewAuditLogORM = _audit_model.ReviewAuditLogORM
ApprovalPolicyORM = _policy_model.ApprovalPolicyORM


def _get_session():
    return get_session_factory()()


async def get_review_status(job_id: str) -> dict | None:
    """Get current approval status for a job."""
    async with _get_session() as session:
        rounds = (await session.execute(
            select(ReviewRoundORM).where(ReviewRoundORM.job_id == job_id)
            .order_by(ReviewRoundORM.round_number)
        )).scalars().all()

        if not rounds:
            return None

        current = rounds[-1]
        assignments = (await session.execute(
            select(ReviewAssignmentORM).where(ReviewAssignmentORM.round_id == current.id)
        )).scalars().all()

        # Get policy name
        policy = (await session.execute(
            select(ApprovalPolicyORM).where(ApprovalPolicyORM.id == current.policy_id)
        )).scalar_one()

        return {
            "job_id": job_id,
            "policy_name": policy.name,
            "policy_type": policy.policy_type,
            "current_round": current.round_number,
            "total_rounds": len(json.loads(policy.config).get("steps", [])) if policy.policy_type == "chain" else None,
            "round_status": current.status,
            "assignments": [
                {"id": a.id, "user_id": a.user_id, "status": a.status,
                 "completed_at": a.completed_at}
                for a in assignments
            ],
            "deadline_at": current.deadline_at,
        }


async def get_audit_log(job_id: str) -> list[dict]:
    """Get audit log entries for a job."""
    async with _get_session() as session:
        result = await session.execute(
            select(ReviewAuditLogORM).where(ReviewAuditLogORM.job_id == job_id)
            .order_by(ReviewAuditLogORM.created_at)
        )
        return [
            {"id": r.id, "job_id": r.job_id, "user_id": r.user_id,
             "action": r.action, "details": json.loads(r.details) if r.details else None,
             "created_at": r.created_at}
            for r in result.scalars().all()
        ]


async def publish_events(job_id, review_status, result_info) -> None:
    """Publish webhook + WS events (non-critical)."""
    action = result_info.get("action", "")
    event_type = f"review.{action}" if action else f"review.{review_status}"
    data = {"job_id": job_id, **result_info}
    try:
        _broadcaster = importlib.import_module("src.services.event-broadcaster")
        await _broadcaster.publish("default", event_type, data)
    except Exception:
        pass
