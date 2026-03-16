"""POST /extract endpoint — upload image + schema, returns job ID."""

import importlib
import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from src.config import settings
from src.schemas import ExtractionSchema, SchemaField, SchemaValidationError, validate_or_raise

_job_service = importlib.import_module("src.services.job-service")
_worker = importlib.import_module("src.services.extraction-worker")

router = APIRouter()

_ALLOWED_TYPES = {"image/png", "image/jpeg", "image/tiff", "application/pdf"}


@router.post("/extract", status_code=202)
async def extract(
    file: UploadFile = File(...),
    mode: str = Form("auto"),
    schema_fields: str | None = Form(None),
    schema_id: str | None = Form(None),
    cloud_provider: str = Form("gemini"),
    lang: str = Form("en"),
) -> dict:
    """Submit an extraction job.

    Accepts multipart form with image file and extraction parameters.
    Returns 202 with job_id for async processing.
    """
    # Validate file type
    if file.content_type and file.content_type not in _ALLOWED_TYPES:
        raise HTTPException(400, f"Unsupported file type: {file.content_type}")

    # Validate file size
    content = await file.read()
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(400, f"File exceeds {settings.max_file_size_mb}MB limit")

    # Validate mode
    if mode not in ("local_only", "cloud", "auto"):
        raise HTTPException(400, f"Invalid mode: {mode}")

    # Validate schema
    if not schema_fields and not schema_id:
        raise HTTPException(400, "Either schema_fields or schema_id is required")

    parsed_fields = None
    if schema_fields:
        try:
            fields_data = json.loads(schema_fields)
            parsed = [SchemaField(**f) for f in fields_data]
            schema = ExtractionSchema(fields=parsed)
            validate_or_raise(schema)
            parsed_fields = schema_fields
        except json.JSONDecodeError:
            raise HTTPException(400, "schema_fields must be valid JSON")
        except SchemaValidationError as e:
            raise HTTPException(400, f"Schema validation failed: {e.errors}")
        except Exception as e:
            raise HTTPException(400, f"Invalid schema_fields: {e}")

    # Create job
    job_id = await _job_service.create_job(
        mode=mode,
        cloud_provider=cloud_provider if mode != "local_only" else None,
        schema_fields_json=parsed_fields,
        schema_id=schema_id,
        input_file="",  # Will be updated after save
    )

    # Save uploaded file
    file_path = await _job_service.save_upload(content, file.filename or "upload.png", job_id)

    # Update job with file path
    from src.database import get_connection, get_db_path
    db = await get_connection(get_db_path(settings.database_url))
    try:
        await db.execute("UPDATE jobs SET input_file = ? WHERE id = ?", (file_path, job_id))
        await db.commit()
    finally:
        await db.close()

    # Enqueue for processing
    await _worker.enqueue_job(job_id)

    return {"job_id": job_id, "status": "pending"}
