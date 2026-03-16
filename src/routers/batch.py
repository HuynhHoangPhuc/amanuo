"""Batch processing endpoints — multi-file upload and tracking."""

import importlib
import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from src.config import settings

_auth = importlib.import_module("src.middleware.auth-middleware")
_batch_service = importlib.import_module("src.services.batch-service")
_job_service = importlib.import_module("src.services.job-service")
_worker = importlib.import_module("src.services.extraction-worker")
_batch_models = importlib.import_module("src.models.batch")

router = APIRouter(tags=["batch"])

_ALLOWED_TYPES = {"image/png", "image/jpeg", "image/tiff", "application/pdf"}


@router.post("/extract/batch", status_code=202)
async def create_batch(
    files: list[UploadFile] = File(...),
    schema_fields: str | None = Form(None),
    schema_id: str | None = Form(None),
    pipeline_id: str | None = Form(None),
    mode: str = Form("auto"),
    cloud_provider: str = Form("gemini"),
    workspace_id: str = Depends(_auth.get_workspace_id),
):
    """Submit a batch of files for extraction. Returns batch_id."""
    if not files:
        raise HTTPException(400, "At least one file is required")

    if not schema_fields and not schema_id:
        raise HTTPException(400, "Either schema_fields or schema_id is required")

    # Create batch record
    batch_id = await _batch_service.create_batch(
        workspace_id=workspace_id,
        total_items=len(files),
        pipeline_id=pipeline_id,
    )

    # Process each file
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    for idx, file in enumerate(files):
        if file.content_type and file.content_type not in _ALLOWED_TYPES:
            continue  # Skip unsupported files

        content = await file.read()
        if len(content) > max_bytes:
            continue  # Skip oversized files

        # Create job for this file
        job_id = await _job_service.create_job(
            mode=mode,
            cloud_provider=cloud_provider if mode != "local_only" else None,
            schema_fields_json=schema_fields,
            schema_id=schema_id,
            input_file="",
            workspace_id=workspace_id,
            batch_id=batch_id,
            pipeline_id=pipeline_id,
        )

        # Save file
        file_path = await _job_service.save_upload(content, file.filename or f"batch_{idx}.png", job_id)

        # Update job with file path
        from src.database import get_connection, get_db_path
        db = await get_connection(get_db_path(settings.database_url))
        try:
            await db.execute("UPDATE jobs SET input_file = ? WHERE id = ?", (file_path, job_id))
            await db.commit()
        finally:
            await db.close()

        # Link to batch
        await _batch_service.add_batch_item(batch_id, job_id, file.filename, idx)

        # Enqueue for processing
        await _worker.enqueue_job(job_id)

    return {"batch_id": batch_id, "total_items": len(files)}


@router.get("/batches", response_model=_batch_models.BatchListResponse)
async def list_batches(
    limit: int = 20,
    offset: int = 0,
    workspace_id: str = Depends(_auth.get_workspace_id),
):
    """List batches with progress summaries."""
    if limit > 100:
        limit = 100
    return await _batch_service.list_batches(workspace_id, limit, offset)


@router.get("/batches/{batch_id}", response_model=_batch_models.BatchResponse)
async def get_batch(
    batch_id: str,
    workspace_id: str = Depends(_auth.get_workspace_id),
):
    """Get batch detail with per-item status."""
    batch = await _batch_service.get_batch(batch_id, workspace_id)
    if not batch:
        raise HTTPException(404, f"Batch {batch_id} not found")
    return batch


@router.post("/batches/{batch_id}/cancel")
async def cancel_batch(
    batch_id: str,
    workspace_id: str = Depends(_auth.get_workspace_id),
):
    """Cancel pending items in a batch."""
    cancelled = await _batch_service.cancel_batch(batch_id, workspace_id)
    if not cancelled:
        raise HTTPException(404, f"Batch {batch_id} not found")
    return {"cancelled": True}
