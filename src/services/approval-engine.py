"""Core approval engine — state machine for chain and quorum workflows."""

import importlib
import json
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select, update

from src.database import get_session_factory
from src.models.job import JobORM

_round_model = importlib.import_module("src.models.review-round")
_assign_model = importlib.import_module("src.models.review-assignment")
_audit_model = importlib.import_module("src.models.review-audit-log")
_policy_model = importlib.import_module("src.models.approval-policy")
_conflict = importlib.import_module("src.services.approval-engine-conflict")
_queries = importlib.import_module("src.services.approval-engine-queries")

ReviewRoundORM = _round_model.ReviewRoundORM
ReviewAssignmentORM = _assign_model.ReviewAssignmentORM
ReviewAuditLogORM = _audit_model.ReviewAuditLogORM
ApprovalPolicyORM = _policy_model.ApprovalPolicyORM

# Re-export query functions so existing callers keep working
get_review_status = _queries.get_review_status
get_audit_log = _queries.get_audit_log


def _get_session():
    return get_session_factory()()


async def start_approval(job_id: str, policy_id: str, workspace_id: str) -> dict:
    """Start approval workflow: create first round based on policy type."""
    async with _get_session() as session:
        result = await session.execute(
            select(ApprovalPolicyORM).where(
                ApprovalPolicyORM.id == policy_id,
                ApprovalPolicyORM.workspace_id == workspace_id,
            )
        )
        policy = result.scalar_one_or_none()
        if not policy:
            raise ValueError(f"Approval policy {policy_id} not found")

        config = json.loads(policy.config)
        now = datetime.now().isoformat()
        deadline_at = None
        if policy.deadline_hours:
            deadline_at = (datetime.now() + timedelta(hours=policy.deadline_hours)).isoformat()

        round_id = str(uuid.uuid4())

        if policy.policy_type == "chain":
            step = config["steps"][0]
            rnd = ReviewRoundORM(
                id=round_id, job_id=job_id, policy_id=policy_id,
                round_number=1, round_type=step["role"],
                status="pending", required_approvals=1,
                deadline_at=deadline_at, created_at=now,
            )
        else:
            rnd = ReviewRoundORM(
                id=round_id, job_id=job_id, policy_id=policy_id,
                round_number=1, round_type="review",
                status="pending", required_approvals=config["required"],
                deadline_at=deadline_at, created_at=now,
            )

        session.add(rnd)
        await _log_audit(session, job_id, None, "approval.started",
                         {"policy_id": policy_id, "type": policy.policy_type})
        await session.commit()

    return {"round_id": round_id, "policy_type": policy.policy_type, "round_number": 1}


async def assign_reviewers(round_id: str, user_ids: list[str]) -> list[dict]:
    """Manually assign reviewers to a round."""
    if not user_ids:
        raise ValueError("Must provide at least one user_id")

    now = datetime.now().isoformat()
    assignments = []

    async with _get_session() as session:
        await session.execute(
            update(ReviewRoundORM).where(ReviewRoundORM.id == round_id)
            .values(status="in_progress")
        )
        for uid in user_ids:
            aid = str(uuid.uuid4())
            session.add(ReviewAssignmentORM(
                id=aid, round_id=round_id, user_id=uid,
                status="pending", created_at=now,
            ))
            assignments.append({"id": aid, "user_id": uid, "status": "pending"})

        rnd = (await session.execute(
            select(ReviewRoundORM).where(ReviewRoundORM.id == round_id)
        )).scalar_one()
        await _log_audit(session, rnd.job_id, None, "reviewers.assigned",
                         {"round_id": round_id, "user_ids": user_ids})
        await session.commit()

    return assignments


async def submit_review(
    assignment_id: str, user_id: str, status: str,
    corrected_result: list[dict] | None = None,
    review_time_ms: int | None = None,
) -> dict:
    """Process individual review submission and advance state machine."""
    if status not in ("approved", "corrected", "rejected"):
        raise ValueError("Status must be 'approved', 'corrected', or 'rejected'")

    now = datetime.now().isoformat()

    async with _get_session() as session:
        assignment = (await session.execute(
            select(ReviewAssignmentORM).where(ReviewAssignmentORM.id == assignment_id)
        )).scalar_one_or_none()
        if not assignment:
            raise ValueError("Assignment not found")
        if assignment.user_id != user_id:
            raise ValueError("User not assigned to this review")
        if assignment.status not in ("pending", "in_progress"):
            raise ValueError("Assignment already completed")

        corrected_json = json.dumps(corrected_result) if corrected_result else None
        await session.execute(
            update(ReviewAssignmentORM).where(ReviewAssignmentORM.id == assignment_id)
            .values(status=status, corrected_result=corrected_json,
                    review_time_ms=review_time_ms, completed_at=now)
        )

        rnd = (await session.execute(
            select(ReviewRoundORM).where(ReviewRoundORM.id == assignment.round_id)
        )).scalar_one()
        policy = (await session.execute(
            select(ApprovalPolicyORM).where(ApprovalPolicyORM.id == rnd.policy_id)
        )).scalar_one()

        config = json.loads(policy.config)
        await _log_audit(session, rnd.job_id, user_id, f"review.{status}",
                         {"assignment_id": assignment_id, "round": rnd.round_number})

        if policy.policy_type == "chain":
            result_info = await _advance_chain(session, rnd, config, status, now)
        else:
            result_info = await _evaluate_quorum(session, rnd, config, now)

        await session.commit()

    await _queries.publish_events(rnd.job_id, status, result_info)
    return {"assignment_id": assignment_id, "status": status, **result_info}


async def _advance_chain(session, rnd, config, status, now) -> dict:
    """Chain flow: advance to next step or finalize."""
    if status == "rejected":
        await _finalize_job(session, rnd.job_id, "rejected", now)
        await _complete_round(session, rnd.id, now)
        return {"job_status": "rejected", "action": "chain_rejected"}

    await _complete_round(session, rnd.id, now)

    steps = config["steps"]
    next_step_idx = rnd.round_number
    if next_step_idx >= len(steps):
        await _finalize_job(session, rnd.job_id, "approved", now)
        return {"job_status": "approved", "action": "chain_completed"}

    next_step = steps[next_step_idx]
    next_round_id = str(uuid.uuid4())
    session.add(ReviewRoundORM(
        id=next_round_id, job_id=rnd.job_id, policy_id=rnd.policy_id,
        round_number=rnd.round_number + 1, round_type=next_step["role"],
        status="pending", required_approvals=1, created_at=now,
    ))
    return {"action": "next_round", "next_round_id": next_round_id,
            "round_number": rnd.round_number + 1}


async def _evaluate_quorum(session, rnd, config, now) -> dict:
    """Quorum flow: check if M approvals reached, detect conflicts."""
    all_assignments = (await session.execute(
        select(ReviewAssignmentORM).where(ReviewAssignmentORM.round_id == rnd.id)
    )).scalars().all()

    completed = [a for a in all_assignments if a.status in ("approved", "corrected", "rejected")]
    if len(completed) < len(all_assignments):
        return {"action": "waiting", "completed": len(completed), "total": len(all_assignments)}

    approved = [a for a in completed if a.status in ("approved", "corrected")]

    if len(approved) < rnd.required_approvals:
        await _finalize_job(session, rnd.job_id, "rejected", now)
        await _complete_round(session, rnd.id, now)
        return {"job_status": "rejected", "action": "quorum_rejected"}

    conflicts = _conflict.detect_conflicts(approved)
    if conflicts:
        await _complete_round(session, rnd.id, now, status="escalated")
        esc = await _create_escalation_round(
            session, rnd.job_id, rnd.policy_id, rnd.round_number + 1, conflicts, now)
        return {"action": "escalated",
                "conflicts": _conflict.build_conflict_summary(conflicts), **esc}

    await _finalize_job(session, rnd.job_id, "approved", now)
    await _complete_round(session, rnd.id, now)
    return {"job_status": "approved", "action": "quorum_approved"}


async def _create_escalation_round(session, job_id, policy_id, round_number, conflicts, now) -> dict:
    round_id = str(uuid.uuid4())
    session.add(ReviewRoundORM(
        id=round_id, job_id=job_id, policy_id=policy_id,
        round_number=round_number, round_type="escalation",
        status="pending", required_approvals=1, created_at=now,
    ))
    await _log_audit(session, job_id, None, "review.escalated",
                     {"conflicts": _conflict.build_conflict_summary(conflicts)})
    return {"escalation_round_id": round_id}


async def _finalize_job(session, job_id, status, now) -> None:
    final_status = "reviewed" if status == "approved" else "rejected"
    await session.execute(
        update(JobORM).where(JobORM.id == job_id)
        .values(status=final_status, completed_at=now)
    )
    await _log_audit(session, job_id, None, f"job.{final_status}", {})


async def _complete_round(session, round_id, now, status="completed") -> None:
    await session.execute(
        update(ReviewRoundORM).where(ReviewRoundORM.id == round_id)
        .values(status=status, completed_at=now)
    )


async def _log_audit(session, job_id, user_id, action, details) -> None:
    session.add(ReviewAuditLogORM(
        id=str(uuid.uuid4()), job_id=job_id, user_id=user_id,
        action=action, details=json.dumps(details),
        created_at=datetime.now().isoformat(),
    ))
