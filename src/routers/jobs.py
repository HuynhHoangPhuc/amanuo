"""Job status and listing endpoints."""

import importlib

from fastapi import APIRouter, Depends, HTTPException

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


@router.get("", response_model=_api.JobListResponse)
async def list_jobs(
    limit: int = 20,
    offset: int = 0,
    workspace_id: str = Depends(_auth.get_workspace_id),
):
    """List recent jobs with pagination."""
    if limit > 100:
        limit = 100
    return await _job_service.list_jobs(workspace_id=workspace_id, limit=limit, offset=offset)
