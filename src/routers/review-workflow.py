"""Approval workflow endpoints — review queue, submit, assign, escalate, audit."""

import importlib

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

_auth = importlib.import_module("src.middleware.auth-middleware")
_engine = importlib.import_module("src.services.approval-engine")

router = APIRouter(tags=["review-workflow"])


class ReviewSubmitRequest(BaseModel):
    status: str  # "approved" | "corrected" | "rejected"
    corrected_result: list[dict] | None = None
    review_time_ms: int | None = None


class AssignReviewersRequest(BaseModel):
    user_ids: list[str]


@router.get("/review-queue")
async def get_review_queue(
    user: dict = Depends(_auth.require_role("reviewer", "approver")),
):
    """Get pending review assignments for current user."""
    from sqlalchemy import select
    from src.database import get_session_factory

    _assign_model = importlib.import_module("src.models.review-assignment")
    _round_model = importlib.import_module("src.models.review-round")
    from src.models.job import JobORM

    async with get_session_factory()() as session:
        # Get pending/in_progress assignments for this user
        result = await session.execute(
            select(_assign_model.ReviewAssignmentORM)
            .where(
                _assign_model.ReviewAssignmentORM.user_id == user["user_id"],
                _assign_model.ReviewAssignmentORM.status.in_(("pending", "in_progress")),
            )
            .order_by(_assign_model.ReviewAssignmentORM.created_at)
        )
        assignments = result.scalars().all()

        queue = []
        for a in assignments:
            # Get round info
            rnd = (await session.execute(
                select(_round_model.ReviewRoundORM)
                .where(_round_model.ReviewRoundORM.id == a.round_id)
            )).scalar_one_or_none()
            if not rnd:
                continue

            # Get job info
            job = (await session.execute(
                select(JobORM).where(JobORM.id == rnd.job_id)
            )).scalar_one_or_none()

            queue.append({
                "assignment_id": a.id,
                "job_id": rnd.job_id,
                "round_number": rnd.round_number,
                "round_type": rnd.round_type,
                "deadline_at": rnd.deadline_at,
                "status": a.status,
                "schema_id": job.schema_id if job else None,
                "created_at": a.created_at,
            })

    return {"queue": queue, "total": len(queue)}


@router.get("/jobs/{job_id}/review-status")
async def get_review_status(
    job_id: str,
    user: dict = Depends(_auth.get_current_user),
):
    """Get current approval status for a job."""
    status = await _engine.get_review_status(job_id)
    if not status:
        raise HTTPException(404, "No approval workflow for this job")
    return status


@router.post("/jobs/{job_id}/assign")
async def assign_reviewers(
    job_id: str,
    body: AssignReviewersRequest,
    user: dict = Depends(_auth.require_role("admin")),
):
    """Assign reviewers to the current round of a job (admin only)."""
    status = await _engine.get_review_status(job_id)
    if not status:
        raise HTTPException(404, "No approval workflow for this job")

    # Get current round ID from the last round
    from sqlalchemy import select
    from src.database import get_session_factory
    _round_model = importlib.import_module("src.models.review-round")

    async with get_session_factory()() as session:
        result = await session.execute(
            select(_round_model.ReviewRoundORM)
            .where(_round_model.ReviewRoundORM.job_id == job_id)
            .order_by(_round_model.ReviewRoundORM.round_number.desc())
            .limit(1)
        )
        current_round = result.scalar_one_or_none()
        if not current_round or current_round.status not in ("pending", "in_progress"):
            raise HTTPException(400, "No active round to assign reviewers")

    return await _engine.assign_reviewers(current_round.id, body.user_ids)


@router.post("/jobs/{job_id}/review")
async def submit_review(
    job_id: str,
    body: ReviewSubmitRequest,
    user: dict = Depends(_auth.require_role("reviewer", "approver")),
):
    """Submit review for user's assignment on this job."""
    # Find user's active assignment for this job
    from sqlalchemy import select
    from src.database import get_session_factory
    _assign_model = importlib.import_module("src.models.review-assignment")
    _round_model = importlib.import_module("src.models.review-round")

    async with get_session_factory()() as session:
        # Get active rounds for this job
        rounds = (await session.execute(
            select(_round_model.ReviewRoundORM.id)
            .where(_round_model.ReviewRoundORM.job_id == job_id,
                   _round_model.ReviewRoundORM.status.in_(("pending", "in_progress")))
        )).scalars().all()

        if not rounds:
            raise HTTPException(400, "No active round for this job")

        # Find user's pending assignment
        assignment = (await session.execute(
            select(_assign_model.ReviewAssignmentORM)
            .where(
                _assign_model.ReviewAssignmentORM.round_id.in_(rounds),
                _assign_model.ReviewAssignmentORM.user_id == user["user_id"],
                _assign_model.ReviewAssignmentORM.status.in_(("pending", "in_progress")),
            )
        )).scalar_one_or_none()

        if not assignment:
            raise HTTPException(403, "No active assignment for this user on this job")

    try:
        return await _engine.submit_review(
            assignment_id=assignment.id,
            user_id=user["user_id"],
            status=body.status,
            corrected_result=body.corrected_result,
            review_time_ms=body.review_time_ms,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/jobs/{job_id}/audit-log")
async def get_audit_log(
    job_id: str,
    user: dict = Depends(_auth.require_role("admin")),
):
    """Get review action history for a job (admin only)."""
    return await _engine.get_audit_log(job_id)
