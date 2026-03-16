"""Review API endpoints — submit, list, get reviews."""

import importlib

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

_review_service = importlib.import_module("src.services.review-service")
_auth = importlib.import_module("src.middleware.auth-middleware")

router = APIRouter(prefix="/reviews", tags=["reviews"])


class ReviewRequest(BaseModel):
    status: str  # "approved" | "corrected"
    corrected_result: list[dict] | None = None
    reviewer_id: str | None = None
    review_time_ms: int | None = None


@router.post("/{job_id}")
async def submit_review(
    job_id: str,
    body: ReviewRequest,
    workspace_id: str = Depends(_auth.get_workspace_id),
):
    """Submit a review for a completed extraction job."""
    if body.status not in ("approved", "corrected"):
        raise HTTPException(400, "Status must be 'approved' or 'corrected'")
    try:
        return await _review_service.submit_review(
            job_id=job_id,
            workspace_id=workspace_id,
            status=body.status,
            corrected_result=body.corrected_result,
            reviewer_id=body.reviewer_id,
            review_time_ms=body.review_time_ms,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("")
async def list_reviews(
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
    workspace_id: str = Depends(_auth.get_workspace_id),
):
    """List reviews filterable by status."""
    if limit > 100:
        limit = 100
    return await _review_service.list_reviews(
        workspace_id=workspace_id,
        status_filter=status,
        limit=limit,
        offset=offset,
    )


@router.get("/{job_id}")
async def get_review(
    job_id: str,
    workspace_id: str = Depends(_auth.get_workspace_id),
):
    """Get review detail for a job."""
    review = await _review_service.get_review(job_id, workspace_id)
    if not review:
        raise HTTPException(404, f"Review for job {job_id} not found")
    return review
