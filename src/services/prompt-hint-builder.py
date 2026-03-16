"""Build prompt hints from human corrections to improve future extractions."""

import importlib
import json
import logging
from collections import defaultdict

from sqlalchemy import select

from src.database import get_session_factory

_review_model = importlib.import_module("src.models.extraction-review")
ExtractionReviewORM = _review_model.ExtractionReviewORM

logger = logging.getLogger(__name__)

# In-memory cache: schema_id → hint text
_hint_cache: dict[str, str] = {}
_correction_counts: dict[str, int] = {}
_REFRESH_THRESHOLD = 10  # Rebuild hints after N new corrections
_MIN_CORRECTIONS = 10  # Minimum corrections per field before generating hints


def _get_session():
    return get_session_factory()()


async def get_hints(schema_id: str) -> str:
    """Get cached prompt hints for a schema. Rebuild if stale."""
    if schema_id in _hint_cache and not _is_stale(schema_id):
        return _hint_cache[schema_id]
    return await _build_hints(schema_id)


async def _build_hints(schema_id: str) -> str:
    """Query corrections, aggregate patterns, generate hint text."""
    async with _get_session() as session:
        # Get all corrections for jobs with this schema
        from src.models.job import JobORM
        result = await session.execute(
            select(ExtractionReviewORM.corrections)
            .join(JobORM, JobORM.id == ExtractionReviewORM.job_id)
            .where(
                JobORM.schema_id == schema_id,
                ExtractionReviewORM.status == "corrected",
                ExtractionReviewORM.corrections.isnot(None),
            )
        )
        rows = result.scalars().all()

    if not rows:
        _hint_cache[schema_id] = ""
        _correction_counts[schema_id] = 0
        return ""

    # Aggregate corrections by field
    field_patterns: dict[str, list[dict]] = defaultdict(list)
    for corrections_json in rows:
        for correction in json.loads(corrections_json):
            field_patterns[correction["field"]].append(correction)

    # Build hint text for fields with enough corrections
    hints = []
    for field, corrections in field_patterns.items():
        if len(corrections) < _MIN_CORRECTIONS:
            continue

        # Find most common correction patterns
        pattern_counts: dict[str, int] = defaultdict(int)
        for c in corrections:
            pattern = f"{c['original']} -> {c['corrected']}"
            pattern_counts[pattern] += 1

        top_patterns = sorted(pattern_counts.items(), key=lambda x: -x[1])[:3]
        hint_lines = [f"For field '{field}':"]
        for pattern, count in top_patterns:
            hint_lines.append(f"  - Common correction ({count}x): {pattern}")
        hints.append("\n".join(hint_lines))

    hint_text = "\n\n".join(hints)
    _hint_cache[schema_id] = hint_text
    _correction_counts[schema_id] = 0
    return hint_text


def _is_stale(schema_id: str) -> bool:
    """Check if hints need refresh (N new corrections since last build)."""
    return _correction_counts.get(schema_id, 0) >= _REFRESH_THRESHOLD


async def invalidate(schema_id: str):
    """Called when new review submitted — increment correction counter."""
    _correction_counts[schema_id] = _correction_counts.get(schema_id, 0) + 1
