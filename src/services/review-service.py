"""Review CRUD — submit, list, get reviews with correction diff logic."""

import importlib
import json
import uuid
from datetime import datetime

from sqlalchemy import select, func, update

from src.database import get_session_factory
from src.models.job import JobORM

_review_model = importlib.import_module("src.models.extraction-review")
ExtractionReviewORM = _review_model.ExtractionReviewORM


def _get_session():
    return get_session_factory()()


def _get_label(r: dict) -> str:
    """Get field label, handling both 'label_name' and 'label' keys."""
    return r.get("label_name", r.get("label", ""))


def compute_corrections(original: list[dict], corrected: list[dict]) -> list[dict]:
    """Compute field-level diff between original and corrected results."""
    original_map = {_get_label(r): r["value"] for r in original}
    corrections = []
    for field in corrected:
        label = _get_label(field)
        new_val = field["value"]
        old_val = original_map.get(label)
        if old_val != new_val:
            corrections.append({
                "field": label,
                "original": old_val,
                "corrected": new_val,
            })
    return corrections


async def submit_review(
    job_id: str,
    workspace_id: str,
    status: str,
    corrected_result: list[dict] | None = None,
    reviewer_id: str | None = None,
    review_time_ms: int | None = None,
) -> dict:
    """Submit review: approve or correct extraction result."""
    async with _get_session() as session:
        # Check for existing review (prevent duplicates)
        existing = await session.execute(
            select(ExtractionReviewORM).where(ExtractionReviewORM.job_id == job_id)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Job {job_id} already has a review")

        # Load job and validate ownership
        result = await session.execute(
            select(JobORM).where(JobORM.id == job_id, JobORM.workspace_id == workspace_id)
        )
        job = result.scalar_one_or_none()
        if not job:
            raise ValueError(f"Job {job_id} not found in workspace")

        original = json.loads(job.result) if job.result else []
        corrections_json = None
        corrected_json = None

        if status == "corrected" and corrected_result:
            corrections = compute_corrections(original, corrected_result)
            corrections_json = json.dumps(corrections)
            corrected_json = json.dumps(corrected_result)

        review_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        review = ExtractionReviewORM(
            id=review_id,
            job_id=job_id,
            workspace_id=workspace_id,
            status=status,
            original_result=json.dumps(original),
            corrected_result=corrected_json,
            corrections=corrections_json,
            reviewer_id=reviewer_id,
            review_time_ms=review_time_ms,
            created_at=now,
        )
        session.add(review)

        # Update job status to "reviewed"
        await session.execute(
            update(JobORM).where(JobORM.id == job_id).values(status="reviewed")
        )
        await session.commit()

    # Publish events (non-critical)
    await _publish_review_event(workspace_id, job_id, status)

    return {
        "id": review_id,
        "job_id": job_id,
        "status": status,
        "corrections": json.loads(corrections_json) if corrections_json else None,
        "created_at": now,
    }


async def list_reviews(
    workspace_id: str,
    status_filter: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """List reviews in workspace, filterable by status."""
    async with _get_session() as session:
        query = select(ExtractionReviewORM).where(
            ExtractionReviewORM.workspace_id == workspace_id
        )
        count_query = select(func.count()).select_from(ExtractionReviewORM).where(
            ExtractionReviewORM.workspace_id == workspace_id
        )

        if status_filter:
            query = query.where(ExtractionReviewORM.status == status_filter)
            count_query = count_query.where(ExtractionReviewORM.status == status_filter)

        total = (await session.execute(count_query)).scalar_one()
        rows = (
            await session.execute(
                query.order_by(ExtractionReviewORM.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        ).scalars().all()

        return {
            "reviews": [_orm_to_dict(r) for r in rows],
            "total": total,
        }


async def get_review(job_id: str, workspace_id: str) -> dict | None:
    """Get review detail for a job."""
    async with _get_session() as session:
        result = await session.execute(
            select(ExtractionReviewORM).where(
                ExtractionReviewORM.job_id == job_id,
                ExtractionReviewORM.workspace_id == workspace_id,
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        return _orm_to_dict(row)


async def _publish_review_event(workspace_id: str, job_id: str, status: str):
    """Publish webhook + WS event for review submission."""
    data = {"job_id": job_id, "review_status": status}
    try:
        _webhook = importlib.import_module("src.services.webhook-service")
        await _webhook.publish_event(workspace_id, "review.submitted", data)
    except Exception:
        pass
    try:
        _broadcaster = importlib.import_module("src.services.event-broadcaster")
        await _broadcaster.publish(workspace_id, "review.submitted", data)
    except Exception:
        pass


def _orm_to_dict(row: ExtractionReviewORM) -> dict:
    return {
        "id": row.id,
        "job_id": row.job_id,
        "workspace_id": row.workspace_id,
        "status": row.status,
        "original_result": json.loads(row.original_result) if row.original_result else [],
        "corrected_result": json.loads(row.corrected_result) if row.corrected_result else None,
        "corrections": json.loads(row.corrections) if row.corrections else None,
        "reviewer_id": row.reviewer_id,
        "review_time_ms": row.review_time_ms,
        "created_at": row.created_at,
    }
