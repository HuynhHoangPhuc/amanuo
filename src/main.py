"""FastAPI application entry point."""

import importlib
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.database import create_engine_from_url, get_db_path, get_engine, init_db, init_db_postgres, is_sqlite
from src.routers import health
from src.routers.extract import router as extract_router
from src.routers.jobs import router as jobs_router
from src.routers.schemas import router as schemas_router

_worker = importlib.import_module("src.services.extraction-worker")
_store = importlib.import_module("src.schemas.schema-store")
_auth_router = importlib.import_module("src.routers.auth")
_workspaces_router = importlib.import_module("src.routers.workspaces")
_pipelines_router = importlib.import_module("src.routers.pipelines")
_webhooks_router = importlib.import_module("src.routers.webhooks")
_webhook_delivery = importlib.import_module("src.services.webhook-delivery")
_pipeline_config = importlib.import_module("src.engine.pipeline-config")

_batch_router = None
_folder_watcher = None
try:
    _batch_router = importlib.import_module("src.routers.batch")
    _folder_watcher = importlib.import_module("src.services.folder-watcher")
except ModuleNotFoundError:
    pass

_templates_router = importlib.import_module("src.routers.templates")
_template_svc = importlib.import_module("src.services.template-service")

_watcher_task = None
_delivery_worker_task = None
_retry_checker_task = None

_redis_pool = importlib.import_module("src.services.redis-pool")
_event_broadcaster = importlib.import_module("src.services.event-broadcaster")
_ws_events_router = importlib.import_module("src.routers.websocket-events")
_reviews_router = importlib.import_module("src.routers.reviews")
_accuracy_router = importlib.import_module("src.routers.accuracy")
_analytics_router = importlib.import_module("src.routers.analytics")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise database, Redis, seed templates, start workers on startup."""
    global _watcher_task, _delivery_worker_task, _retry_checker_task

    # 1. Initialise SQLAlchemy engine (must happen before any service calls)
    create_engine_from_url(settings.database_url)

    # 2. Run migrations and seed default data (dialect-aware)
    if is_sqlite(settings.database_url):
        db_path = get_db_path(settings.database_url)
        await init_db(db_path)
    else:
        await init_db_postgres()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)

    # 3. Connect to Redis for ARQ job queue (graceful degradation if unavailable)
    try:
        await _redis_pool.init_redis(settings.redis_url)
        logger.info("Redis connected — using ARQ job queue")
    except Exception as e:
        logger.warning("Redis unavailable (%s) — using in-memory queue (jobs not persistent)", e)

    # 3b. Connect broadcaster for WebSocket events (graceful degradation if unavailable)
    try:
        await _event_broadcaster.init_broadcaster(settings.broadcaster_url)
    except Exception as e:
        logger.warning("Broadcaster unavailable (%s) — WebSocket in no-broadcast mode", e)

    # 4. Seed schema templates + default pipeline via ORM services
    await _store.seed_templates(None)
    await _seed_default_pipeline()

    # 5. Seed curated schema marketplace templates (idempotent)
    from src.database import get_session_factory
    async with get_session_factory()() as session:
        await _template_svc.seed_curated_templates(session)

    # 6. Start fallback in-memory workers (drain queue when Redis unavailable)
    _worker.start_workers(count=settings.max_workers)
    _delivery_worker_task = _webhook_delivery.start_delivery_worker()
    _retry_checker_task = _webhook_delivery.start_retry_checker()

    if _folder_watcher and settings.watch_dir:
        _watcher_task = await _folder_watcher.start_folder_watcher(settings)

    yield

    # Cleanup
    _worker.stop_workers()
    if _delivery_worker_task:
        _webhook_delivery.stop_delivery_worker(_delivery_worker_task)
    if _retry_checker_task:
        _webhook_delivery.stop_retry_checker(_retry_checker_task)
    if _watcher_task and _folder_watcher:
        _folder_watcher.stop_folder_watcher(_watcher_task)

    await _event_broadcaster.shutdown_broadcaster()
    await _redis_pool.close_redis()

    engine = get_engine()
    if engine:
        await engine.dispose()


async def _seed_default_pipeline() -> None:
    """Seed the default pipeline if it doesn't exist."""
    from sqlalchemy import select
    from src.database import get_session_factory
    from src.models.pipeline import PipelineORM

    async with get_session_factory()() as session:
        result = await session.execute(
            select(PipelineORM).where(
                PipelineORM.workspace_id == "default",
                PipelineORM.name == "default",
            )
        )
        if result.scalar_one_or_none():
            return

        pipeline_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        pipeline = PipelineORM(
            id=pipeline_id,
            workspace_id="default",
            name="default",
            description="Default extraction pipeline",
            config=_pipeline_config.DEFAULT_PIPELINE_YAML,
            is_active=1,
            created_at=now,
            updated_at=now,
        )
        session.add(pipeline)
        await session.commit()


app = FastAPI(
    title=settings.app_name,
    description="Adaptive hybrid OCR system",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(health.router)
app.include_router(extract_router)
app.include_router(jobs_router)
app.include_router(schemas_router)
app.include_router(_auth_router.router)
app.include_router(_workspaces_router.router)
app.include_router(_pipelines_router.router)
app.include_router(_webhooks_router.router)
if _batch_router:
    app.include_router(_batch_router.router)
app.include_router(_templates_router.router)
app.include_router(_ws_events_router.router)
app.include_router(_reviews_router.router)
app.include_router(_accuracy_router.router)
app.include_router(_analytics_router.router)

try:
    import gradio as gr

    _gradio_app = importlib.import_module("src.ui.gradio-app")
    demo = _gradio_app.create_ui()
    app = gr.mount_gradio_app(app, demo, path="/ui")
except ImportError:
    pass
