"""ARQ worker settings — defines task functions and worker configuration."""

import importlib
import logging

from arq.connections import RedisSettings

logger = logging.getLogger(__name__)


async def process_extraction_job(ctx: dict, job_id: str) -> dict:
    """ARQ task: process a single extraction job by ID."""
    worker_module = importlib.import_module("src.services.extraction-worker")
    await worker_module.process_job(job_id)
    return {"job_id": job_id, "status": "processed"}


async def deliver_webhook_task(ctx: dict, delivery_id: str) -> dict:
    """ARQ task: deliver a single webhook by delivery ID."""
    delivery_module = importlib.import_module("src.services.webhook-delivery")
    await delivery_module.deliver(delivery_id)
    return {"delivery_id": delivery_id, "status": "delivered"}


async def startup(ctx: dict) -> None:
    """Initialize DB engine in worker context."""
    from src.config import settings
    from src.database import create_engine_from_url

    create_engine_from_url(settings.database_url)
    logger.info("ARQ worker started, DB engine initialized")


async def shutdown(ctx: dict) -> None:
    """Clean up worker context."""
    from src.database import get_engine

    engine = get_engine()
    if engine:
        await engine.dispose()
    logger.info("ARQ worker shutdown complete")


def get_redis_settings() -> RedisSettings:
    """Return Redis settings from app config."""
    from src.config import settings

    return RedisSettings.from_dsn(settings.redis_url)


class WorkerSettings:
    """ARQ worker configuration."""

    functions = [process_extraction_job, deliver_webhook_task]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = get_redis_settings()
    max_jobs = 3
    job_timeout = 300  # 5 minutes
    max_tries = 3
    keep_result = 300  # keep result 5 minutes
