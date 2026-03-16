"""FastAPI application entry point."""

import importlib
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.database import get_connection, get_db_path, init_db
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

# Batch processing (imported later when Phase 4 is ready)
_batch_router = None
_folder_watcher = None
try:
    _batch_router = importlib.import_module("src.routers.batch")
    _folder_watcher = importlib.import_module("src.services.folder-watcher")
except ModuleNotFoundError:
    pass  # Phase 4 not yet implemented

_watcher_task = None
_delivery_worker_task = None
_retry_checker_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database, seed templates, start workers on startup."""
    global _watcher_task, _delivery_worker_task, _retry_checker_task

    db_path = get_db_path(settings.database_url)
    await init_db(db_path)
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)

    # Seed schema templates + default pipeline
    db = await get_connection(db_path)
    try:
        await _store.seed_templates(db)
        await _seed_default_pipeline(db)
    finally:
        await db.close()

    # Start background extraction workers
    _worker.start_workers(count=settings.max_workers)

    # Start webhook delivery worker + retry checker
    _delivery_worker_task = _webhook_delivery.start_delivery_worker()
    _retry_checker_task = _webhook_delivery.start_retry_checker()

    # Start folder watcher if configured
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


async def _seed_default_pipeline(db) -> None:
    """Seed the default pipeline if it doesn't exist."""
    cursor = await db.execute(
        "SELECT id FROM pipelines WHERE workspace_id = 'default' AND name = 'default'"
    )
    if await cursor.fetchone():
        return

    import uuid
    from datetime import datetime

    pipeline_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    await db.execute(
        """INSERT INTO pipelines (id, workspace_id, name, description, config, created_at, updated_at)
           VALUES (?, 'default', 'default', 'Default extraction pipeline', ?, ?, ?)""",
        (pipeline_id, _pipeline_config.DEFAULT_PIPELINE_YAML, now, now),
    )
    await db.commit()


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

# Existing routers
app.include_router(health.router)
app.include_router(extract_router)
app.include_router(jobs_router)
app.include_router(schemas_router)

# New routers (Phase 2+)
app.include_router(_auth_router.router)
app.include_router(_workspaces_router.router)
app.include_router(_pipelines_router.router)
app.include_router(_webhooks_router.router)
if _batch_router:
    app.include_router(_batch_router.router)

# Mount Gradio UI
try:
    import gradio as gr

    _gradio_app = importlib.import_module("src.ui.gradio-app")
    demo = _gradio_app.create_ui()
    app = gr.mount_gradio_app(app, demo, path="/ui")
except ImportError:
    pass  # Gradio not installed — API-only mode
