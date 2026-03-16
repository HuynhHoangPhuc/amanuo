"""Batch processing — CRUD, counter updates, status derivation."""

import importlib
import uuid
from datetime import datetime

from src.config import settings
from src.database import get_connection, get_db_path

_batch_models = importlib.import_module("src.models.batch")
BatchResponse = _batch_models.BatchResponse
BatchItemResponse = _batch_models.BatchItemResponse
BatchListResponse = _batch_models.BatchListResponse


async def _get_db():
    return await get_connection(get_db_path(settings.database_url))


async def create_batch(workspace_id: str, total_items: int, pipeline_id: str | None = None) -> str:
    """Create a batch record. Returns batch_id."""
    batch_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    db = await _get_db()
    try:
        await db.execute(
            """INSERT INTO batches (id, workspace_id, status, total_items, pipeline_id, created_at)
               VALUES (?, ?, 'pending', ?, ?, ?)""",
            (batch_id, workspace_id, total_items, pipeline_id, now),
        )
        await db.commit()
    finally:
        await db.close()

    return batch_id


async def add_batch_item(batch_id: str, job_id: str, filename: str | None, index: int) -> str:
    """Link a job to a batch as an item."""
    item_id = str(uuid.uuid4())

    db = await _get_db()
    try:
        await db.execute(
            """INSERT INTO batch_items (id, batch_id, job_id, item_index, filename, status)
               VALUES (?, ?, ?, ?, ?, 'pending')""",
            (item_id, batch_id, job_id, index, filename),
        )
        await db.commit()
    finally:
        await db.close()

    return item_id


async def update_batch_counters(batch_id: str, completed_delta: int = 0, failed_delta: int = 0) -> None:
    """Atomically update batch counters and derive status."""
    db = await _get_db()
    try:
        if completed_delta:
            await db.execute(
                "UPDATE batches SET completed_items = completed_items + ? WHERE id = ?",
                (completed_delta, batch_id),
            )
        if failed_delta:
            await db.execute(
                "UPDATE batches SET failed_items = failed_items + ? WHERE id = ?",
                (failed_delta, batch_id),
            )

        # Derive status from counters
        cursor = await db.execute(
            "SELECT total_items, completed_items, failed_items FROM batches WHERE id = ?",
            (batch_id,),
        )
        row = await cursor.fetchone()
        if row:
            status = _derive_status(row["total_items"], row["completed_items"], row["failed_items"])
            completed_at = datetime.now().isoformat() if status in ("completed", "partial", "failed") else None
            if completed_at:
                await db.execute(
                    "UPDATE batches SET status = ?, completed_at = ? WHERE id = ?",
                    (status, completed_at, batch_id),
                )
            else:
                await db.execute("UPDATE batches SET status = ? WHERE id = ?", (status, batch_id))

        await db.commit()
    finally:
        await db.close()


async def get_batch(batch_id: str, workspace_id: str) -> BatchResponse | None:
    """Get batch with item details."""
    db = await _get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM batches WHERE id = ? AND workspace_id = ?",
            (batch_id, workspace_id),
        )
        row = await cursor.fetchone()
        if not row:
            return None

        # Load items
        cursor = await db.execute(
            "SELECT * FROM batch_items WHERE batch_id = ? ORDER BY item_index",
            (batch_id,),
        )
        items = await cursor.fetchall()

        return _row_to_response(row, items)
    finally:
        await db.close()


async def list_batches(workspace_id: str, limit: int = 20, offset: int = 0) -> BatchListResponse:
    """List batches for a workspace."""
    db = await _get_db()
    try:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM batches WHERE workspace_id = ?", (workspace_id,)
        )
        total = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT * FROM batches WHERE workspace_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (workspace_id, limit, offset),
        )
        rows = await cursor.fetchall()

        return BatchListResponse(
            batches=[_row_to_response(r) for r in rows],
            total=total,
        )
    finally:
        await db.close()


async def cancel_batch(batch_id: str, workspace_id: str) -> bool:
    """Cancel pending items in a batch."""
    db = await _get_db()
    try:
        # Verify ownership
        cursor = await db.execute(
            "SELECT id FROM batches WHERE id = ? AND workspace_id = ?",
            (batch_id, workspace_id),
        )
        if not await cursor.fetchone():
            return False

        # Cancel pending jobs in the batch
        await db.execute(
            """UPDATE jobs SET status = 'failed', error = 'Batch cancelled'
               WHERE batch_id = ? AND status = 'pending'""",
            (batch_id,),
        )
        await db.execute(
            "UPDATE batch_items SET status = 'cancelled' WHERE batch_id = ? AND status = 'pending'",
            (batch_id,),
        )
        await db.execute(
            "UPDATE batches SET status = 'failed', completed_at = ? WHERE id = ?",
            (datetime.now().isoformat(), batch_id),
        )
        await db.commit()
        return True
    finally:
        await db.close()


def _derive_status(total: int, completed: int, failed: int) -> str:
    """Derive batch status from counters."""
    done = completed + failed
    if done == 0:
        return "pending"
    if done < total:
        return "processing"
    if failed == total:
        return "failed"
    if failed > 0:
        return "partial"
    return "completed"


def _row_to_response(row, items=None) -> BatchResponse:
    """Convert DB row to BatchResponse."""
    total = row["total_items"]
    completed = row["completed_items"]
    progress = (completed / total * 100) if total > 0 else 0.0

    item_list = None
    if items is not None:
        item_list = [
            BatchItemResponse(
                id=i["id"], job_id=i["job_id"], filename=i["filename"],
                status=i["status"], item_index=i["item_index"],
            )
            for i in items
        ]

    return BatchResponse(
        id=row["id"], status=row["status"], total_items=total,
        completed_items=completed, failed_items=row["failed_items"],
        progress_pct=round(progress, 1), pipeline_id=row["pipeline_id"],
        created_at=row["created_at"], completed_at=row["completed_at"],
        items=item_list,
    )
