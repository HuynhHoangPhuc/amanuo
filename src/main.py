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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database, seed templates, start workers on startup."""
    db_path = get_db_path(settings.database_url)
    await init_db(db_path)
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)

    # Seed schema templates
    db = await get_connection(db_path)
    try:
        await _store.seed_templates(db)
    finally:
        await db.close()

    # Start background extraction workers
    _worker.start_workers(count=settings.max_workers)

    yield

    # Cleanup
    _worker.stop_workers()


app = FastAPI(
    title=settings.app_name,
    description="Adaptive hybrid OCR system",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(extract_router)
app.include_router(jobs_router)
app.include_router(schemas_router)

# Mount Gradio UI
try:
    import gradio as gr

    _gradio_app = importlib.import_module("src.ui.gradio-app")
    demo = _gradio_app.create_ui()
    app = gr.mount_gradio_app(app, demo, path="/ui")
except ImportError:
    pass  # Gradio not installed — API-only mode
