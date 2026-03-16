"""Job lifecycle management — CRUD operations + file storage."""

import importlib
import json
import uuid
from datetime import datetime
from pathlib import Path

import aiosqlite

from src.config import settings
from src.database import get_connection, get_db_path

_api = importlib.import_module("src.models.api-models")
JobResponse = _api.JobResponse
CostResponse = _api.CostResponse
JobListResponse = _api.JobListResponse

from src.schemas import ExtractionResult


async def _get_db() -> aiosqlite.Connection:
    return await get_connection(get_db_path(settings.database_url))


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

    db = await _get_db()
    try:
        await db.execute(
            """INSERT INTO jobs (id, status, mode, cloud_provider, schema_fields,
               schema_id, input_file, created_at, workspace_id, batch_id, pipeline_id)
               VALUES (?, 'pending', ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (job_id, mode, cloud_provider, schema_fields_json, schema_id, input_file,
             now, workspace_id, batch_id, pipeline_id),
        )
        await db.commit()
    finally:
        await db.close()

    return job_id


async def get_job(job_id: str, workspace_id: str = "default") -> JobResponse | None:
    """Get job by ID, scoped to workspace."""
    db = await _get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM jobs WHERE id = ? AND workspace_id = ?",
            (job_id, workspace_id),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return _row_to_response(row)
    finally:
        await db.close()


async def get_job_raw(job_id: str) -> dict | None:
    """Get raw job row by ID (no workspace filter, for internal use)."""
    db = await _get_db()
    try:
        cursor = await db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return dict(row)
    finally:
        await db.close()


async def list_jobs(workspace_id: str = "default", limit: int = 20, offset: int = 0) -> JobListResponse:
    """List jobs with pagination, scoped to workspace."""
    db = await _get_db()
    try:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM jobs WHERE workspace_id = ?", (workspace_id,)
        )
        total = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT * FROM jobs WHERE workspace_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (workspace_id, limit, offset),
        )
        rows = await cursor.fetchall()

        return JobListResponse(
            jobs=[_row_to_response(row) for row in rows],
            total=total,
        )
    finally:
        await db.close()


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
    db = await _get_db()
    try:
        updates = []
        params = []

        if status:
            updates.append("status = ?")
            params.append(status)
        if result is not None:
            updates.append("result = ?")
            params.append(json.dumps([r.model_dump() for r in result]))
        if confidence is not None:
            updates.append("confidence = ?")
            params.append(confidence)
        if cost_input_tokens is not None:
            updates.append("cost_input_tokens = ?")
            params.append(cost_input_tokens)
        if cost_output_tokens is not None:
            updates.append("cost_output_tokens = ?")
            params.append(cost_output_tokens)
        if cost_estimated_usd is not None:
            updates.append("cost_estimated_usd = ?")
            params.append(cost_estimated_usd)
        if error is not None:
            updates.append("error = ?")
            params.append(error)
        if status in ("completed", "failed"):
            updates.append("completed_at = ?")
            params.append(datetime.now().isoformat())

        if updates:
            params.append(job_id)
            await db.execute(
                f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?", params
            )
            await db.commit()
    finally:
        await db.close()


async def save_upload(file_bytes: bytes, filename: str, job_id: str) -> str:
    """Save uploaded file to disk. Returns file path."""
    ext = Path(filename).suffix or ".png"
    file_path = Path(settings.upload_dir) / f"{job_id}{ext}"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(file_bytes)
    return str(file_path)


def _row_to_response(row) -> JobResponse:
    """Convert a database row to JobResponse."""
    result = None
    if row["result"]:
        result = [ExtractionResult(**r) for r in json.loads(row["result"])]

    cost = None
    if row["cost_input_tokens"] is not None:
        cost = CostResponse(
            input_tokens=row["cost_input_tokens"] or 0,
            output_tokens=row["cost_output_tokens"] or 0,
            estimated_cost_usd=row["cost_estimated_usd"] or 0.0,
        )

    return JobResponse(
        id=row["id"],
        status=row["status"],
        mode=row["mode"],
        cloud_provider=row["cloud_provider"],
        created_at=row["created_at"],
        completed_at=row["completed_at"],
        result=result,
        confidence=row["confidence"],
        cost=cost,
        error=row["error"],
    )
