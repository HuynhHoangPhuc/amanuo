"""Background extraction worker — processes jobs via pipeline engine."""

import asyncio
import importlib
import json
import logging
from pathlib import Path

from src.schemas import ExtractionSchema, SchemaField

_job_service = importlib.import_module("src.services.job-service")
_router_service = importlib.import_module("src.services.router-service")
_confidence = importlib.import_module("src.services.confidence-scorer")
_pipeline_executor = importlib.import_module("src.engine.pipeline-executor")
_pipeline_config = importlib.import_module("src.engine.pipeline-config")
_step_interface = importlib.import_module("src.engine.step-interface")

logger = logging.getLogger(__name__)

# Simple in-memory job queue
_job_queue: asyncio.Queue[str] = asyncio.Queue()
_workers: list[asyncio.Task] = []


async def enqueue_job(job_id: str) -> None:
    """Add a job to the processing queue."""
    await _job_queue.put(job_id)


async def process_job(job_id: str) -> None:
    """Process a single extraction job via pipeline engine or direct routing."""
    from src.config import settings
    from src.database import get_connection, get_db_path

    # Get raw job data
    db = await get_connection(get_db_path(settings.database_url))
    try:
        cursor = await db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = await cursor.fetchone()
    finally:
        await db.close()

    if not row:
        logger.error("Job %s not found", job_id)
        return

    try:
        await _job_service.update_job(job_id, status="processing")

        if not row["input_file"]:
            raise FileNotFoundError("No input file for job")

        image = Path(row["input_file"]).read_bytes()
        schema = _load_schema(row)
        workspace_id = row["workspace_id"] or "default"
        pipeline_id = row["pipeline_id"]

        # Try pipeline execution if pipeline_id is set
        if pipeline_id:
            result_ctx = await _execute_via_pipeline(
                pipeline_id, image, row, schema, workspace_id, job_id
            )
            if result_ctx:
                await _save_pipeline_result(job_id, result_ctx, schema, workspace_id)
                return

        # Fallback: direct routing (original MVP flow)
        provider = _router_service.route(row["mode"], row["cloud_provider"] or "gemini")
        result = await provider.extract(image, schema)
        conf = _confidence.score(result, schema)

        await _job_service.update_job(
            job_id,
            status="completed",
            result=result.normalized,
            confidence=conf,
            cost_input_tokens=result.cost.input_tokens,
            cost_output_tokens=result.cost.output_tokens,
            cost_estimated_usd=result.cost.estimated_cost_usd,
        )
        await _publish_job_event(workspace_id, job_id, "completed", conf)

    except Exception as e:
        logger.exception("Job %s failed: %s", job_id, e)
        await _job_service.update_job(job_id, status="failed", error=str(e))
        workspace_id = row["workspace_id"] or "default"
        await _publish_job_event(workspace_id, job_id, "failed", error=str(e))

    # Update batch counters if job is part of a batch
    if row["batch_id"]:
        await _update_batch(row["batch_id"], row["status"] if row else "failed")


async def _execute_via_pipeline(pipeline_id, image, row, schema, workspace_id, job_id):
    """Execute job through pipeline engine. Returns StepContext or None."""
    from src.config import settings
    from src.database import get_connection, get_db_path

    db = await get_connection(get_db_path(settings.database_url))
    try:
        cursor = await db.execute("SELECT config FROM pipelines WHERE id = ?", (pipeline_id,))
        p_row = await cursor.fetchone()
    finally:
        await db.close()

    if not p_row:
        logger.warning("Pipeline %s not found, falling back to direct routing", pipeline_id)
        return None

    config = _pipeline_config.parse_pipeline_yaml(p_row["config"])
    schema_fields_json = row["schema_fields"]

    context = _step_interface.StepContext(
        image=image,
        schema_fields=schema_fields_json,
        schema_id=row["schema_id"],
        workspace_id=workspace_id,
        job_id=job_id,
        mode=row["mode"],
        cloud_provider=row["cloud_provider"] or "gemini",
    )

    return await _pipeline_executor.execute_pipeline(config, context)


async def _save_pipeline_result(job_id, context, schema, workspace_id):
    """Save pipeline execution result to the job."""
    from src.schemas import ExtractionResult

    result_list = None
    confidence = context.confidence

    if context.result:
        result_list = [ExtractionResult(**r) if isinstance(r, dict) else r for r in context.result]
        if confidence is None:
            confidence = _confidence.score_from_results(result_list, schema) if hasattr(_confidence, 'score_from_results') else 0.0

    await _job_service.update_job(
        job_id,
        status="completed",
        result=result_list,
        confidence=confidence,
        cost_input_tokens=context.cost_input_tokens,
        cost_output_tokens=context.cost_output_tokens,
        cost_estimated_usd=context.cost_estimated_usd,
    )
    await _publish_job_event(workspace_id, job_id, "completed", confidence)


async def _publish_job_event(workspace_id, job_id, status, confidence=None, error=None):
    """Publish webhook event for job completion/failure."""
    try:
        _webhook_service = importlib.import_module("src.services.webhook-service")
        event_type = f"job.{status}"
        data = {"job_id": job_id, "status": status}
        if confidence is not None:
            data["confidence"] = confidence
        if error:
            data["error"] = error
        await _webhook_service.publish_event(workspace_id, event_type, data)
    except Exception:
        pass  # Non-critical — don't fail the job


async def _update_batch(batch_id, job_status):
    """Update batch counters after job completion."""
    try:
        _batch_service = importlib.import_module("src.services.batch-service")
        if job_status == "completed":
            await _batch_service.update_batch_counters(batch_id, completed_delta=1)
        elif job_status == "failed":
            await _batch_service.update_batch_counters(batch_id, failed_delta=1)
    except (ModuleNotFoundError, Exception):
        pass  # Phase 4 not yet implemented or non-critical


def _load_schema(row) -> ExtractionSchema:
    """Load schema from job record (inline fields or saved schema ID)."""
    if row["schema_fields"]:
        fields_data = json.loads(row["schema_fields"])
        return ExtractionSchema(fields=[SchemaField(**f) for f in fields_data])

    if row["schema_id"]:
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
