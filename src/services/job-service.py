"""Job lifecycle management — CRUD operations using SQLAlchemy ORM."""

import importlib
import json
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_session_factory
from src.models.job import JobORM

_api = importlib.import_module("src.models.api-models")
JobResponse = _api.JobResponse
CostResponse = _api.CostResponse
JobListResponse = _api.JobListResponse

from src.schemas import ExtractionResult


def _get_session():
    """Open a new session from the factory (for non-Depends callers)."""
    return get_session_factory()()


async def create_job(
    mode: str,
    cloud_provider: str | None,
    schema_fields_json: str | None,
    schema_id: str | None,
    input_file: str,
    workspace_id: str = "default",
    batch_id: str | None = None,
    pipeline_id: str | None = None,
) -> str:
    """Create a new job record. Returns job ID."""
    job_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    async with _get_session() as session:
        job = JobORM(
            id=job_id,
            status="pending",
            mode=mode,
            cloud_provider=cloud_provider,
            schema_fields=schema_fields_json,
            schema_id=schema_id,
            input_file=input_file,
            created_at=now,
            workspace_id=workspace_id,
            batch_id=batch_id,
            pipeline_id=pipeline_id,
        )
        session.add(job)
        await session.commit()

    return job_id


async def get_job(job_id: str, workspace_id: str = "default") -> JobResponse | None:
    """Get job by ID, scoped to workspace."""
    async with _get_session() as session:
        result = await session.execute(
            select(JobORM).where(JobORM.id == job_id, JobORM.workspace_id == workspace_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        return _orm_to_response(row)


async def get_job_raw(job_id: str) -> dict | None:
    """Get raw job data by ID (no workspace filter, for internal use)."""
    async with _get_session() as session:
        result = await session.execute(select(JobORM).where(JobORM.id == job_id))
        row = result.scalar_one_or_none()
        if not row:
            return None
        return {
            "id": row.id, "status": row.status, "mode": row.mode,
            "cloud_provider": row.cloud_provider, "schema_fields": row.schema_fields,
            "schema_id": row.schema_id, "input_file": row.input_file, "result": row.result,
            "confidence": row.confidence, "cost_input_tokens": row.cost_input_tokens,
            "cost_output_tokens": row.cost_output_tokens,
            "cost_estimated_usd": row.cost_estimated_usd, "error": row.error,
            "created_at": row.created_at, "completed_at": row.completed_at,
            "workspace_id": row.workspace_id, "batch_id": row.batch_id,
            "pipeline_id": row.pipeline_id,
        }


async def list_jobs(workspace_id: str = "default", limit: int = 20, offset: int = 0) -> JobListResponse:
    """List jobs with pagination, scoped to workspace."""
    async with _get_session() as session:
        total_result = await session.execute(
            select(func.count()).select_from(JobORM).where(JobORM.workspace_id == workspace_id)
        )
        total = total_result.scalar_one()

        rows_result = await session.execute(
            select(JobORM)
            .where(JobORM.workspace_id == workspace_id)
            .order_by(JobORM.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = rows_result.scalars().all()

        return JobListResponse(
            jobs=[_orm_to_response(r) for r in rows],
            total=total,
        )


async def update_job(
    job_id: str,
    status: str | None = None,
    result: list[ExtractionResult] | None = None,
    confidence: float | None = None,
    cost_input_tokens: int | None = None,
    cost_output_tokens: int | None = None,
    cost_estimated_usd: float | None = None,
    error: str | None = None,
) -> None:
    """Update job fields."""
    values: dict = {}

    if status:
        values["status"] = status
    if result is not None:
        values["result"] = json.dumps([r.model_dump() for r in result])
    if confidence is not None:
        values["confidence"] = confidence
    if cost_input_tokens is not None:
        values["cost_input_tokens"] = cost_input_tokens
    if cost_output_tokens is not None:
        values["cost_output_tokens"] = cost_output_tokens
    if cost_estimated_usd is not None:
        values["cost_estimated_usd"] = cost_estimated_usd
    if error is not None:
        values["error"] = error
    if status in ("completed", "failed"):
        values["completed_at"] = datetime.now().isoformat()

    if not values:
        return

    async with _get_session() as session:
        await session.execute(update(JobORM).where(JobORM.id == job_id).values(**values))
        await session.commit()


async def update_job_input_file(job_id: str, input_file: str) -> None:
    """Update the input_file path for a job."""
    async with _get_session() as session:
        await session.execute(
            update(JobORM).where(JobORM.id == job_id).values(input_file=input_file)
        )
        await session.commit()


async def save_upload(file_bytes: bytes, filename: str, job_id: str) -> str:
    """Save uploaded file to disk. Returns file path."""
    ext = Path(filename).suffix or ".png"
    file_path = Path(settings.upload_dir) / f"{job_id}{ext}"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(file_bytes)
    return str(file_path)


def _orm_to_response(row: JobORM) -> JobResponse:
    """Convert an ORM instance to JobResponse."""
    result = None
    if row.result:
        result = [ExtractionResult(**r) for r in json.loads(row.result)]

    cost = None
    if row.cost_input_tokens is not None:
        cost = CostResponse(
            input_tokens=row.cost_input_tokens or 0,
            output_tokens=row.cost_output_tokens or 0,
            estimated_cost_usd=row.cost_estimated_usd or 0.0,
        )

    return JobResponse(
        id=row.id,
        status=row.status,
        mode=row.mode,
        cloud_provider=row.cloud_provider,
        created_at=row.created_at,
        completed_at=row.completed_at,
        result=result,
        confidence=row.confidence,
        cost=cost,
        error=row.error,
    )
