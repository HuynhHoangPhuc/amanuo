"""Health check endpoint."""

from fastapi import APIRouter

from src.config import settings
from src.database import get_connection, get_db_path

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """Return app health status including DB connectivity."""
    db_ok = False
    db_path = get_db_path(settings.database_url)
    try:
        db = await get_connection(db_path)
        await db.execute("SELECT 1")
        await db.close()
        db_ok = True
    except Exception:
        pass

    return {
        "status": "ok" if db_ok else "degraded",
        "app": settings.app_name,
        "debug": settings.debug,
        "database": "connected" if db_ok else "unavailable",
        "default_mode": settings.default_mode,
    }
