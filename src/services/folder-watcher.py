"""Directory watcher for automated batch ingestion."""

import asyncio
import importlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".pdf"}


async def start_folder_watcher(settings) -> asyncio.Task:
    """Start watching a directory for new files."""
    task = asyncio.create_task(_watch_loop(settings))
    logger.info("Folder watcher started: %s", settings.watch_dir)
    return task


def stop_folder_watcher(task: asyncio.Task) -> None:
    """Stop the folder watcher."""
    task.cancel()
    logger.info("Folder watcher stopped")


async def _watch_loop(settings) -> None:
    """Main watch loop — polls for new files using watchfiles."""
    try:
        import watchfiles

        watch_dir = Path(settings.watch_dir)
        watch_dir.mkdir(parents=True, exist_ok=True)
        processed_dir = watch_dir / "processed"
        processed_dir.mkdir(exist_ok=True)

        async for changes in watchfiles.awatch(str(watch_dir)):
            new_files = []
            for change_type, path in changes:
                p = Path(path)
                if p.suffix.lower() in _SUPPORTED_EXTENSIONS and p.parent == watch_dir:
                    new_files.append(p)

            if new_files:
                # Batch window — collect files for a few seconds
                await asyncio.sleep(settings.watch_batch_window_seconds)
                await _process_batch(new_files, settings, processed_dir)

    except asyncio.CancelledError:
        return
    except ImportError:
        logger.error("watchfiles not installed — folder watcher disabled")
    except Exception:
        logger.exception("Folder watcher error")


async def _process_batch(files: list[Path], settings, processed_dir: Path) -> None:
    """Create a batch from detected files."""
    _batch_service = importlib.import_module("src.services.batch-service")
    _job_service = importlib.import_module("src.services.job-service")
    _worker = importlib.import_module("src.services.extraction-worker")

    batch_id = await _batch_service.create_batch(
        workspace_id="default",
        total_items=len(files),
        pipeline_id=settings.watch_pipeline_id or None,
    )

    for idx, file_path in enumerate(files):
        if not file_path.exists():
            continue

        content = file_path.read_bytes()
        schema_id = settings.watch_schema_id or None

        job_id = await _job_service.create_job(
            mode="auto",
            cloud_provider="gemini",
            schema_fields_json=None,
            schema_id=schema_id,
            input_file=str(file_path),
            workspace_id="default",
            batch_id=batch_id,
            pipeline_id=settings.watch_pipeline_id or None,
        )

        await _batch_service.add_batch_item(batch_id, job_id, file_path.name, idx)
        await _worker.enqueue_job(job_id)

        # Move to processed
        try:
            file_path.rename(processed_dir / file_path.name)
        except OSError:
            pass

    logger.info("Batch %s created with %d files from folder watcher", batch_id, len(files))
