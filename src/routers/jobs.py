"""Job status, listing, and document serving endpoints."""

import importlib
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

_job_service = importlib.import_module("src.services.job-service")
_api = importlib.import_module("src.models.api-models")
_auth = importlib.import_module("src.middleware.auth-middleware")

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=_api.JobResponse)
async def get_job(job_id: str, workspace_id: str = Depends(_auth.get_workspace_id)):
    """Get job status and results by ID."""
    job = await _job_service.get_job(job_id, workspace_id)
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")
    return job


@router.get("/{job_id}/document")
async def get_document(job_id: str, workspace_id: str = Depends(_auth.get_workspace_id)):
    """Serve the original uploaded document file for review."""
    from src.config import settings
    raw = await _job_service.get_job_raw(job_id)
    if not raw or raw.get("workspace_id") != workspace_id:
        raise HTTPException(404, f"Job {job_id} not found")
    input_file = raw.get("input_file")
    if not input_file:
        raise HTTPException(404, "Document file not found")
    # Prevent path traversal — file must be under upload_dir
    resolved = Path(input_file).resolve()
    upload_root = Path(settings.upload_dir).resolve()
    if not str(resolved).startswith(str(upload_root)):
        raise HTTPException(403, "Access denied")
    if not resolved.exists():
        raise HTTPException(404, "Document file not found")
    return FileResponse(str(resolved))


@router.get("", response_model=_api.JobListResponse)
async def list_jobs(
    limit: int = 20,
    offset: int = 0,
    status: str | None = None,
    workspace_id: str = Depends(_auth.get_workspace_id),
):
    """List recent jobs with pagination, optionally filtered by status."""
    if limit > 100:
        limit = 100
    return await _job_service.list_jobs(
        workspace_id=workspace_id, limit=limit, offset=offset, status_filter=status,
    )
