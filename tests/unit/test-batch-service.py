"""Unit tests for batch service."""

import importlib
import pytest

_batch = importlib.import_module("src.services.batch-service")

create_batch = _batch.create_batch
add_batch_item = _batch.add_batch_item
update_batch_counters = _batch.update_batch_counters
get_batch = _batch.get_batch
list_batches = _batch.list_batches
cancel_batch = _batch.cancel_batch
_derive_status = _batch._derive_status


class TestBatchServiceCRUD:
    """Test batch CRUD operations."""

    @pytest.mark.unit
    async def test_create_batch(self, db_workspace):
        """Creating a batch returns batch_id."""
        batch_id = await create_batch(db_workspace, total_items=5)
        assert batch_id is not None
        assert len(batch_id) > 0

    @pytest.mark.unit
    async def test_add_batch_item(self, db_workspace):
        """Adding item to batch returns item_id."""
        import uuid
        from src.database import get_connection, get_db_path
        from src.config import settings
        from datetime import datetime

        batch_id = await create_batch(db_workspace, total_items=3)

        # Create a dummy job
        job_id = str(uuid.uuid4())
        db = await get_connection(get_db_path(settings.database_url))
        try:
            now = datetime.now().isoformat()
            await db.execute(
                "INSERT INTO jobs (id, status, mode, created_at) VALUES (?, ?, ?, ?)",
                (job_id, "pending", "cloud", now),
            )
            await db.commit()
        finally:
            await db.close()

        item_id = await add_batch_item(batch_id, job_id, "file.pdf", 0)
        assert item_id is not None
        assert len(item_id) > 0

    @pytest.mark.unit
    async def test_get_batch_after_creation(self, db_workspace):
        """Get batch returns created batch with correct metadata."""
        batch_id = await create_batch(db_workspace, total_items=2)
        batch = await get_batch(batch_id, db_workspace)

        assert batch is not None
        assert batch.id == batch_id
        assert batch.status == "pending"
        assert batch.total_items == 2
        assert batch.completed_items == 0

    @pytest.mark.unit
    async def test_get_batch_wrong_workspace_returns_none(self, db_workspace):
        """Get batch with wrong workspace_id returns None."""
        batch_id = await create_batch(db_workspace, total_items=2)
        batch = await get_batch(batch_id, "wrong-ws")
        assert batch is None

    @pytest.mark.unit
    async def test_list_batches(self, db_workspace):
        """List batches returns pagination."""
        await create_batch(db_workspace, total_items=1)
        await create_batch(db_workspace, total_items=2)

        result = await list_batches(db_workspace, limit=10, offset=0)
        assert result.total >= 2
        assert len(result.batches) >= 2

    @pytest.mark.unit
    async def test_list_batches_pagination(self, db_workspace):
        """List batches respects limit and offset."""
        await create_batch(db_workspace, total_items=1)
        await create_batch(db_workspace, total_items=2)
        await create_batch(db_workspace, total_items=3)

        result = await list_batches(db_workspace, limit=2, offset=0)
        assert len(result.batches) <= 2

        result = await list_batches(db_workspace, limit=2, offset=2)
        assert result.total >= 3


class TestBatchCounters:
    """Test batch counter updates and status derivation."""

    @pytest.mark.unit
    async def test_update_batch_counters_completed(self, db_workspace):
        """Updating completed counter increments it."""
        batch_id = await create_batch(db_workspace, total_items=3)
        await update_batch_counters(batch_id, completed_delta=1)

        batch = await get_batch(batch_id, db_workspace)
        assert batch.completed_items == 1

    @pytest.mark.unit
    async def test_update_batch_counters_failed(self, db_workspace):
        """Updating failed counter increments it."""
        batch_id = await create_batch(db_workspace, total_items=3)
        await update_batch_counters(batch_id, failed_delta=1)

        batch = await get_batch(batch_id, db_workspace)
        assert batch.failed_items == 1

    @pytest.mark.unit
    async def test_update_both_counters(self, db_workspace):
        """Updating both counters works atomically."""
        batch_id = await create_batch(db_workspace, total_items=5)
        await update_batch_counters(batch_id, completed_delta=2, failed_delta=1)

        batch = await get_batch(batch_id, db_workspace)
        assert batch.completed_items == 2
        assert batch.failed_items == 1

    @pytest.mark.unit
    def test_derive_status_pending(self):
        """All pending (no completed/failed) returns pending."""
        assert _derive_status(total=5, completed=0, failed=0) == "pending"

    @pytest.mark.unit
    def test_derive_status_processing(self):
        """Some done but not all returns processing."""
        assert _derive_status(total=5, completed=2, failed=0) == "processing"

    @pytest.mark.unit
    def test_derive_status_completed(self):
        """All done with no failures returns completed."""
        assert _derive_status(total=5, completed=5, failed=0) == "completed"

    @pytest.mark.unit
    def test_derive_status_all_failed(self):
        """All done but all failed returns failed."""
        assert _derive_status(total=5, completed=0, failed=5) == "failed"

    @pytest.mark.unit
    def test_derive_status_partial(self):
        """Some completed, some failed returns partial."""
        assert _derive_status(total=5, completed=3, failed=2) == "partial"

    @pytest.mark.unit
    async def test_batch_status_derived_on_counter_update(self, db_workspace):
        """Status is derived when counters are updated."""
        batch_id = await create_batch(db_workspace, total_items=2)
        await update_batch_counters(batch_id, completed_delta=2)

        batch = await get_batch(batch_id, db_workspace)
        assert batch.status == "completed"


class TestBatchItems:
    """Test batch items."""

    @pytest.mark.unit
    async def test_get_batch_includes_items(self, db_workspace):
        """Get batch includes items when present."""
        import uuid
        from src.database import get_connection, get_db_path
        from src.config import settings

        batch_id = await create_batch(db_workspace, total_items=2)

        # Create dummy jobs in database
        job_id_1 = str(uuid.uuid4())
        job_id_2 = str(uuid.uuid4())
        db = await get_connection(get_db_path(settings.database_url))
        try:
            from datetime import datetime
            now = datetime.now().isoformat()
            await db.execute(
                "INSERT INTO jobs (id, status, mode, created_at) VALUES (?, ?, ?, ?)",
                (job_id_1, "pending", "cloud", now),
            )
            await db.execute(
                "INSERT INTO jobs (id, status, mode, created_at) VALUES (?, ?, ?, ?)",
                (job_id_2, "pending", "cloud", now),
            )
            await db.commit()
        finally:
            await db.close()

        item_id_1 = await add_batch_item(batch_id, job_id_1, "file1.pdf", 0)
        item_id_2 = await add_batch_item(batch_id, job_id_2, "file2.pdf", 1)

        batch = await get_batch(batch_id, db_workspace)
        assert batch.items is not None
        assert len(batch.items) == 2
        assert batch.items[0].item_index == 0
        assert batch.items[1].item_index == 1

    @pytest.mark.unit
    async def test_batch_items_ordered_by_index(self, db_workspace):
        """Batch items are ordered by item_index."""
        import uuid
        from src.database import get_connection, get_db_path
        from src.config import settings
        from datetime import datetime

        batch_id = await create_batch(db_workspace, total_items=3)

        # Create dummy jobs
        job_ids = [str(uuid.uuid4()) for _ in range(3)]
        db = await get_connection(get_db_path(settings.database_url))
        try:
            now = datetime.now().isoformat()
            for job_id in job_ids:
                await db.execute(
                    "INSERT INTO jobs (id, status, mode, created_at) VALUES (?, ?, ?, ?)",
                    (job_id, "pending", "cloud", now),
                )
            await db.commit()
        finally:
            await db.close()

        await add_batch_item(batch_id, job_ids[0], "a.pdf", 2)
        await add_batch_item(batch_id, job_ids[1], "b.pdf", 0)
        await add_batch_item(batch_id, job_ids[2], "c.pdf", 1)

        batch = await get_batch(batch_id, db_workspace)
        assert batch.items[0].item_index == 0
        assert batch.items[1].item_index == 1
        assert batch.items[2].item_index == 2


class TestBatchCancellation:
    """Test batch cancellation."""

    @pytest.mark.unit
    async def test_cancel_batch(self, db_workspace):
        """Cancelling batch returns True on success."""
        batch_id = await create_batch(db_workspace, total_items=1)
        result = await cancel_batch(batch_id, db_workspace)
        assert result is True

    @pytest.mark.unit
    async def test_cancel_nonexistent_batch_returns_false(self, db_workspace):
        """Cancelling nonexistent batch returns False."""
        result = await cancel_batch("nonexistent", db_workspace)
        assert result is False

    @pytest.mark.unit
    async def test_cancel_batch_wrong_workspace_returns_false(self, db_workspace):
        """Cancelling batch with wrong workspace returns False."""
        batch_id = await create_batch(db_workspace, total_items=1)
        result = await cancel_batch(batch_id, "wrong-ws")
        assert result is False
