"""Compute and store accuracy metrics per schema from review data."""

import importlib
import json
import uuid
from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import select, func

from src.database import get_session_factory
from src.models.job import JobORM

_review_model = importlib.import_module("src.models.extraction-review")
ExtractionReviewORM = _review_model.ExtractionReviewORM
_accuracy_model = importlib.import_module("src.models.accuracy-metric")
AccuracyMetricORM = _accuracy_model.AccuracyMetricORM

_metrics_cache: dict[str, tuple[datetime, dict]] = {}  # schema_id → (cached_at, data)
_CACHE_TTL_SECONDS = 300  # 5 minutes


def _get_session():
    return get_session_factory()()


async def compute_accuracy(
    workspace_id: str,
    schema_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Compute accuracy metrics for a schema in a date range."""
    async with _get_session() as session:
        query = (
            select(ExtractionReviewORM)
            .join(JobORM, JobORM.id == ExtractionReviewORM.job_id)
            .where(
                ExtractionReviewORM.workspace_id == workspace_id,
                JobORM.schema_id == schema_id,
            )
        )
        if start_date:
            query = query.where(ExtractionReviewORM.created_at >= start_date)
        if end_date:
            query = query.where(ExtractionReviewORM.created_at <= end_date)

        rows = (await session.execute(query)).scalars().all()

    total = len(rows)
    if total == 0:
        return {"total_reviews": 0, "approved_count": 0, "corrected_count": 0,
                "accuracy_pct": 0.0, "field_accuracy": {}}

    approved = sum(1 for r in rows if r.status == "approved")
    corrected = total - approved
    accuracy_pct = round((approved / total) * 100, 2)

    # Per-field accuracy
    field_stats: dict[str, dict] = defaultdict(lambda: {"correct": 0, "total": 0})
    for row in rows:
        original = json.loads(row.original_result) if row.original_result else []
        corrections = json.loads(row.corrections) if row.corrections else []
        corrected_fields = {c["field"] for c in corrections}

        for field in original:
            label = field.get("label_name", field.get("label", ""))
            field_stats[label]["total"] += 1
            if label not in corrected_fields:
                field_stats[label]["correct"] += 1

    field_accuracy = {}
    for label, stats in field_stats.items():
        pct = round((stats["correct"] / stats["total"]) * 100, 2) if stats["total"] > 0 else 0.0
        field_accuracy[label] = {
            "correct": stats["correct"],
            "total": stats["total"],
            "accuracy_pct": pct,
        }

    return {
        "total_reviews": total,
        "approved_count": approved,
        "corrected_count": corrected,
        "accuracy_pct": accuracy_pct,
        "field_accuracy": field_accuracy,
    }


async def compute_and_store(
    workspace_id: str,
    schema_id: str,
    period_start: str | None = None,
    period_end: str | None = None,
) -> dict:
    """Compute and persist accuracy snapshot."""
    now = datetime.now()
    if not period_end:
        period_end = now.isoformat()
    if not period_start:
        period_start = (now - timedelta(days=1)).isoformat()

    metrics = await compute_accuracy(workspace_id, schema_id, period_start, period_end)

    async with _get_session() as session:
        metric = AccuracyMetricORM(
            id=str(uuid.uuid4()),
            schema_id=schema_id,
            workspace_id=workspace_id,
            period_start=period_start,
            period_end=period_end,
            total_reviews=metrics["total_reviews"],
            approved_count=metrics["approved_count"],
            corrected_count=metrics["corrected_count"],
            accuracy_pct=metrics["accuracy_pct"],
            field_accuracy=json.dumps(metrics["field_accuracy"]),
            created_at=now.isoformat(),
        )
        session.add(metric)
        await session.commit()

    return metrics


async def get_metrics(
    workspace_id: str,
    schema_id: str,
    limit: int = 30,
) -> list[dict]:
    """Get recent accuracy metric snapshots for dashboard."""
    # Check cache
    cache_key = f"{workspace_id}:{schema_id}"
    if cache_key in _metrics_cache:
        cached_at, data = _metrics_cache[cache_key]
        if (datetime.now() - cached_at).total_seconds() < _CACHE_TTL_SECONDS:
            return data

    async with _get_session() as session:
        result = await session.execute(
            select(AccuracyMetricORM)
            .where(
                AccuracyMetricORM.workspace_id == workspace_id,
                AccuracyMetricORM.schema_id == schema_id,
            )
            .order_by(AccuracyMetricORM.period_end.desc())
            .limit(limit)
        )
        rows = result.scalars().all()

    data = [
        {
            "id": r.id,
            "period_start": r.period_start,
            "period_end": r.period_end,
            "total_reviews": r.total_reviews,
            "approved_count": r.approved_count,
            "corrected_count": r.corrected_count,
            "accuracy_pct": r.accuracy_pct,
            "field_accuracy": json.loads(r.field_accuracy),
        }
        for r in rows
    ]

    _metrics_cache[cache_key] = (datetime.now(), data)
    return data
