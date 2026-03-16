"""Batch processing — CRUD, counter updates, status derivation — SQLAlchemy ORM."""

import importlib
import uuid
from datetime import datetime

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session_factory
from src.models.batch import BatchORM, BatchItemORM
from src.models.job import JobORM

_batch_models = importlib.import_module("src.models.batch")
BatchResponse = _batch_models.BatchResponse
BatchItemResponse = _batch_models.BatchItemResponse
BatchListResponse = _batch_models.BatchListResponse


def _get_session():
    return get_session_factory()()


async def create_batch(workspace_id: str, total_items: int, pipeline_id: str | None = None) -> str:
    """Create a batch record. Returns batch_id."""
    batch_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    async with _get_session() as session:
        batch = BatchORM(
            id=batch_id,
            workspace_id=workspace_id,
            status="pending",
            total_items=total_items,
            pipeline_id=pipeline_id,
            created_at=now,
        )
        session.add(batch)
        await session.commit()

    return batch_id


async def add_batch_item(batch_id: str, job_id: str, filename: str | None, index: int) -> str:
    """Link a job to a batch as an item."""
    item_id = str(uuid.uuid4())

    async with _get_session() as session:
        item = BatchItemORM(
            id=item_id,
            batch_id=batch_id,
            job_id=job_id,
            item_index=index,
            filename=filename,
            status="pending",
        )
        session.add(item)
        await session.commit()

    return item_id


async def update_batch_counters(batch_id: str, completed_delta: int = 0, failed_delta: int = 0) -> None:
    """Atomically update batch counters and derive status."""
    async with _get_session() as session:
        # Fetch current counters
        result = await session.execute(
            select(BatchORM).where(BatchORM.id == batch_id)
        )
        batch = result.scalar_one_or_none()
        if not batch:
            return

        new_completed = batch.completed_items + completed_delta
        new_failed = batch.failed_items + failed_delta
        status = _derive_status(batch.total_items, new_completed, new_failed)
        completed_at = (
            datetime.now().isoformat()
            if status in ("completed", "partial", "failed")
            else None
        )

        values = {
            "completed_items": new_completed,
            "failed_items": new_failed,
            "status": status,
        }
        if completed_at:
            values["completed_at"] = completed_at

        await session.execute(update(BatchORM).where(BatchORM.id == batch_id).values(**values))
        await session.commit()

    # Publish real-time progress event (non-critical)
    try:
        _broadcaster = importlib.import_module("src.services.event-broadcaster")
        await _broadcaster.publish(batch.workspace_id, "batch.progress", {
            "batch_id": batch_id,
            "completed": new_completed,
            "failed": new_failed,
            "total": batch.total_items,
            "status": status,
        })
    except Exception:
        pass


async def get_batch(batch_id: str, workspace_id: str) -> BatchResponse | None:
    """Get batch with item details."""
    async with _get_session() as session:
        result = await session.execute(
            select(BatchORM).where(
                BatchORM.id == batch_id, BatchORM.workspace_id == workspace_id
            )
        )
        batch = result.scalar_one_or_none()
        if not batch:
            return None

        items_result = await session.execute(
            select(BatchItemORM)
            .where(BatchItemORM.batch_id == batch_id)
            .order_by(BatchItemORM.item_index)
        )
        items = items_result.scalars().all()

        return _orm_to_response(batch, items)


async def list_batches(workspace_id: str, limit: int = 20, offset: int = 0) -> BatchListResponse:
    """List batches for a workspace."""
    async with _get_session() as session:
        total_result = await session.execute(
            select(func.count()).select_from(BatchORM).where(BatchORM.workspace_id == workspace_id)
        )
        total = total_result.scalar_one()

        rows_result = await session.execute(
            select(BatchORM)
            .where(BatchORM.workspace_id == workspace_id)
            .order_by(BatchORM.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = rows_result.scalars().all()

        return BatchListResponse(
            batches=[_orm_to_response(r) for r in rows],
            total=total,
        )


async def cancel_batch(batch_id: str, workspace_id: str) -> bool:
    """Cancel pending items in a batch."""
    async with _get_session() as session:
        # Verify ownership
        result = await session.execute(
            select(BatchORM).where(
                BatchORM.id == batch_id, BatchORM.workspace_id == workspace_id
            )
        )
        if not result.scalar_one_or_none():
            return False

        # Cancel pending jobs in the batch
        await session.execute(
            update(JobORM)
            .where(JobORM.batch_id == batch_id, JobORM.status == "pending")
            .values(status="failed", error="Batch cancelled")
        )
        await session.execute(
            update(BatchItemORM)
            .where(BatchItemORM.batch_id == batch_id, BatchItemORM.status == "pending")
            .values(status="cancelled")
        )
        await session.execute(
            update(BatchORM)
            .where(BatchORM.id == batch_id)
            .values(status="failed", completed_at=datetime.now().isoformat())
        )
        await session.commit()
        return True


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


def _orm_to_response(batch: BatchORM, items=None) -> BatchResponse:
    """Convert ORM instance to BatchResponse."""
    total = batch.total_items
    completed = batch.completed_items
    progress = (completed / total * 100) if total > 0 else 0.0

    item_list = None
    if items is not None:
        item_list = [
            BatchItemResponse(
                id=i.id, job_id=i.job_id, filename=i.filename,
                status=i.status, item_index=i.item_index,
            )
            for i in items
        ]

    return BatchResponse(
        id=batch.id,
        status=batch.status,
        total_items=total,
        completed_items=completed,
        failed_items=batch.failed_items,
        progress_pct=round(progress, 1),
        pipeline_id=batch.pipeline_id,
        created_at=batch.created_at,
        completed_at=batch.completed_at,
        items=item_list,
    )
