"""Background extraction worker — processes jobs via pipeline engine — ARQ or asyncio fallback."""

import asyncio
import importlib
import json
import logging
from pathlib import Path

from sqlalchemy import select

from src.database import get_session_factory
from src.models.job import JobORM
from src.models.pipeline import PipelineORM
from src.schemas import ExtractionSchema, SchemaField

_job_service = importlib.import_module("src.services.job-service")
_router_service = importlib.import_module("src.services.router-service")
_confidence = importlib.import_module("src.services.confidence-scorer")
_pipeline_executor = importlib.import_module("src.engine.pipeline-executor")
_pipeline_config = importlib.import_module("src.engine.pipeline-config")
_step_interface = importlib.import_module("src.engine.step-interface")

logger = logging.getLogger(__name__)

# Fallback in-memory queue used when Redis is unavailable
_fallback_queue: asyncio.Queue[str] = asyncio.Queue()
_workers: list[asyncio.Task] = []


def _get_session():
    return get_session_factory()()


async def enqueue_job(job_id: str, priority: int = 0) -> None:
    """Enqueue job for processing. Uses ARQ if Redis available, else in-memory fallback."""
    _redis_pool = importlib.import_module("src.services.redis-pool")
    redis = await _redis_pool.get_redis()
    if redis:
        await redis.enqueue_job("process_extraction_job", job_id)
        logger.debug("Job %s enqueued via ARQ", job_id)
    else:
        logger.warning("Redis unavailable — using in-memory queue (jobs lost on restart)")
        await _fallback_queue.put(job_id)


async def process_job(job_id: str) -> None:
    """Process a single extraction job via pipeline engine or direct routing."""
    async with _get_session() as session:
        result = await session.execute(select(JobORM).where(JobORM.id == job_id))
        job_orm = result.scalar_one_or_none()

    if not job_orm:
        logger.error("Job %s not found", job_id)
        return

    row = {
        "id": job_orm.id, "status": job_orm.status, "mode": job_orm.mode,
        "cloud_provider": job_orm.cloud_provider, "schema_fields": job_orm.schema_fields,
        "schema_id": job_orm.schema_id, "input_file": job_orm.input_file,
        "workspace_id": job_orm.workspace_id, "batch_id": job_orm.batch_id,
        "pipeline_id": job_orm.pipeline_id,
    }

    try:
        await _job_service.update_job(job_id, status="processing")

        if not row["input_file"]:
            raise FileNotFoundError("No input file for job")

        image = Path(row["input_file"]).read_bytes()
        schema = _load_schema(row)
        workspace_id = row["workspace_id"] or "default"
        pipeline_id = row["pipeline_id"]

        if pipeline_id:
            result_ctx = await _execute_via_pipeline(
                pipeline_id, image, row, schema, workspace_id, job_id
            )
            if result_ctx:
                await _save_pipeline_result(job_id, result_ctx, schema, workspace_id)
                return

        # Fallback: direct routing
        provider = _router_service.route(row["mode"], row["cloud_provider"] or "gemini")
        result = await provider.extract(image, schema)
        conf = _confidence.score(result, schema)

        final_status = await _determine_final_status(row, conf)
        await _job_service.update_job(
            job_id,
            status=final_status,
            result=result.normalized,
            confidence=conf,
            cost_input_tokens=result.cost.input_tokens,
            cost_output_tokens=result.cost.output_tokens,
            cost_estimated_usd=result.cost.estimated_cost_usd,
        )
        await _publish_job_event(workspace_id, job_id, final_status, conf)

    except Exception as e:
        logger.exception("Job %s failed: %s", job_id, e)
        await _job_service.update_job(job_id, status="failed", error=str(e))
        workspace_id = row.get("workspace_id") or "default"
        await _publish_job_event(workspace_id, job_id, "failed", error=str(e))

    if row["batch_id"]:
        final_status = "failed"
        async with _get_session() as session:
            jr = await session.execute(select(JobORM).where(JobORM.id == job_id))
            j = jr.scalar_one_or_none()
            if j:
                final_status = j.status
        await _update_batch(row["batch_id"], final_status)


async def _execute_via_pipeline(pipeline_id, image, row, schema, workspace_id, job_id):
    """Execute job through pipeline engine. Returns StepContext or None."""
    async with _get_session() as session:
        result = await session.execute(
            select(PipelineORM).where(PipelineORM.id == pipeline_id)
        )
        p_row = result.scalar_one_or_none()

    if not p_row:
        logger.warning("Pipeline %s not found, falling back to direct routing", pipeline_id)
        return None

    config = _pipeline_config.parse_pipeline_yaml(p_row.config)
    context = _step_interface.StepContext(
        image=image,
        schema_fields=row["schema_fields"],
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
            confidence = (
                _confidence.score_from_results(result_list, schema)
                if hasattr(_confidence, "score_from_results")
                else 0.0
            )

    row_data = {"schema_id": context.schema_id if hasattr(context, "schema_id") else None}
    final_status = await _determine_final_status(row_data, confidence or 0.0)
    await _job_service.update_job(
        job_id,
        status=final_status,
        result=result_list,
        confidence=confidence,
        cost_input_tokens=context.cost_input_tokens,
        cost_output_tokens=context.cost_output_tokens,
        cost_estimated_usd=context.cost_estimated_usd,
    )
    await _publish_job_event(workspace_id, job_id, final_status, confidence)


async def _publish_job_event(workspace_id, job_id, status, confidence=None, error=None):
    """Publish webhook + WebSocket event for job completion/failure."""
    event_type = f"job.{status}"
    data = {"job_id": job_id, "status": status}
    if confidence is not None:
        data["confidence"] = confidence
    if error:
        data["error"] = error
    try:
        _webhook_service = importlib.import_module("src.services.webhook-service")
        await _webhook_service.publish_event(workspace_id, event_type, data)
    except Exception:
        pass  # Non-critical
    try:
        _broadcaster = importlib.import_module("src.services.event-broadcaster")
        await _broadcaster.publish(workspace_id, event_type, data)
    except Exception:
        pass  # Non-critical


async def _update_batch(batch_id, job_status):
    """Update batch counters after job completion."""
    try:
        _batch_service = importlib.import_module("src.services.batch-service")
        if job_status == "completed":
            await _batch_service.update_batch_counters(batch_id, completed_delta=1)
        elif job_status == "failed":
            await _batch_service.update_batch_counters(batch_id, failed_delta=1)
    except Exception:
        pass


async def _determine_final_status(row: dict, confidence: float) -> str:
    """Decide if job needs human review based on schema setting or confidence."""
    from src.config import settings
    schema_id = row.get("schema_id")
    if schema_id:
        try:
            _schema_orm = importlib.import_module("src.models.schema-orm")
            async with _get_session() as session:
                result = await session.execute(
                    select(_schema_orm.SchemaORM).where(_schema_orm.SchemaORM.id == schema_id)
                )
                schema_row = result.scalar_one_or_none()
                if schema_row and getattr(schema_row, "require_review", False):
                    return "pending_review"
        except Exception:
            pass
    if confidence is not None and confidence < settings.review_confidence_threshold:
        return "pending_review"
    return "completed"


def _load_schema(row) -> ExtractionSchema:
    """Load schema from job record (inline fields or saved schema ID)."""
    if row["schema_fields"]:
        fields_data = json.loads(row["schema_fields"])
        return ExtractionSchema(fields=[SchemaField(**f) for f in fields_data])
    if row["schema_id"]:
        raise ValueError("schema_id lookup not implemented in worker; use inline schema_fields")
    raise ValueError("Job has no schema defined")


def get_queue_stats() -> dict:
    """Return fallback queue depth for health/metrics."""
    return {
        "fallback_queue_size": _fallback_queue.qsize(),
        "active_fallback_workers": len(_workers),
    }


async def _worker_loop() -> None:
    """Background worker that drains the fallback in-memory queue."""
    while True:
        job_id = await _fallback_queue.get()
        try:
            await process_job(job_id)
        except Exception as e:
            logger.exception("Worker error processing job %s: %s", job_id, e)
        finally:
            _fallback_queue.task_done()


def start_workers(count: int = 3) -> None:
    """Start fallback in-memory worker tasks (used when Redis unavailable)."""
    for _ in range(count):
        task = asyncio.create_task(_worker_loop())
        _workers.append(task)
    logger.info("Started %d fallback extraction workers", count)


def stop_workers() -> None:
    """Cancel all fallback worker tasks."""
    for task in _workers:
        task.cancel()
    _workers.clear()
