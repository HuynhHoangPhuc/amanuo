"""Background extraction worker — processes jobs asynchronously."""

import asyncio
import importlib
import json
import logging
from pathlib import Path

from src.schemas import ExtractionSchema, SchemaField

_job_service = importlib.import_module("src.services.job-service")
_router_service = importlib.import_module("src.services.router-service")
_confidence = importlib.import_module("src.services.confidence-scorer")

logger = logging.getLogger(__name__)

# Simple in-memory job queue
_job_queue: asyncio.Queue[str] = asyncio.Queue()
_workers: list[asyncio.Task] = []


async def enqueue_job(job_id: str) -> None:
    """Add a job to the processing queue."""
    await _job_queue.put(job_id)


async def process_job(job_id: str) -> None:
    """Process a single extraction job."""
    job = await _job_service.get_job(job_id)
    if not job:
        logger.error("Job %s not found", job_id)
        return

    try:
        await _job_service.update_job(job_id, status="processing")

        # Load image
        if not job.mode:
            raise ValueError("Job has no mode set")

        # Get raw job data to access input_file and schema_fields
        from src.config import settings
        from src.database import get_connection, get_db_path
        db = await get_connection(get_db_path(settings.database_url))
        try:
            cursor = await db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = await cursor.fetchone()
        finally:
            await db.close()

        if not row or not row["input_file"]:
            raise FileNotFoundError("No input file for job")

        image = Path(row["input_file"]).read_bytes()

        # Load schema
        schema = _load_schema(row)

        # Route to provider
        provider = _router_service.route(
            row["mode"], row["cloud_provider"] or "gemini"
        )

        # Execute extraction
        result = await provider.extract(image, schema)

        # Calculate confidence
        conf = _confidence.score(result, schema)

        # Update job with results
        await _job_service.update_job(
            job_id,
            status="completed",
            result=result.normalized,
            confidence=conf,
            cost_input_tokens=result.cost.input_tokens,
            cost_output_tokens=result.cost.output_tokens,
            cost_estimated_usd=result.cost.estimated_cost_usd,
        )

    except Exception as e:
        logger.exception("Job %s failed: %s", job_id, e)
        await _job_service.update_job(job_id, status="failed", error=str(e))


def _load_schema(row) -> ExtractionSchema:
    """Load schema from job record (inline fields or saved schema ID)."""
    if row["schema_fields"]:
        fields_data = json.loads(row["schema_fields"])
        return ExtractionSchema(fields=[SchemaField(**f) for f in fields_data])

    if row["schema_id"]:
        # Would need async DB call — for MVP, schema_fields is always populated
        raise ValueError("schema_id lookup not implemented in worker; use inline schema_fields")

    raise ValueError("Job has no schema defined")


async def _worker_loop() -> None:
    """Background worker that processes jobs from the queue."""
    while True:
        job_id = await _job_queue.get()
        try:
            await process_job(job_id)
        except Exception as e:
            logger.exception("Worker error processing job %s: %s", job_id, e)
        finally:
            _job_queue.task_done()


def start_workers(count: int = 3) -> None:
    """Start background worker tasks."""
    for i in range(count):
        task = asyncio.create_task(_worker_loop())
        _workers.append(task)
    logger.info("Started %d extraction workers", count)


def stop_workers() -> None:
    """Cancel all worker tasks."""
    for task in _workers:
        task.cancel()
    _workers.clear()
