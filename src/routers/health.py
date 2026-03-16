"""Health check endpoint — reports DB and Redis connectivity."""

import importlib

from fastapi import APIRouter

from src.config import settings
from src.database import get_engine

router = APIRouter()

_redis_pool = importlib.import_module("src.services.redis-pool")
_extraction_worker = importlib.import_module("src.services.extraction-worker")


@router.get("/health")
async def health_check() -> dict:
    """Return app health status including DB and Redis connectivity."""
    db_ok = False
    try:
        from sqlalchemy import text

        engine = get_engine()
        if engine:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        pass

    redis_ok = (await _redis_pool.get_redis()) is not None
    queue_stats = _extraction_worker.get_queue_stats()

    overall_ok = db_ok  # Redis is optional — degraded but not down
    return {
        "status": "ok" if overall_ok else "degraded",
        "app": settings.app_name,
        "debug": settings.debug,
        "database": "connected" if db_ok else "unavailable",
        "redis": "connected" if redis_ok else "unavailable",
        "queue_mode": "arq" if redis_ok else "in-memory",
        "default_mode": settings.default_mode,
        **queue_stats,
    }
