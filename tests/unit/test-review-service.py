"""Unit tests for review service — submission, listing, retrieval, correction diffs."""

import importlib
import json
import uuid
import pytest

_review = importlib.import_module("src.services.review-service")
submit_review = _review.submit_review
list_reviews = _review.list_reviews
get_review = _review.get_review
compute_corrections = _review.compute_corrections


class TestComputeCorrections:
    """Test correction diff computation."""

    @pytest.mark.unit
    def test_compute_corrections_single_field_change(self):
        """Compute corrections returns diff for single field change."""
        original = [
            {"label_name": "invoice_number", "value": "INV-001"},
            {"label_name": "amount", "value": "100.00"},
        ]
        corrected = [
            {"label_name": "invoice_number", "value": "INV-002"},
            {"label_name": "amount", "value": "100.00"},
        ]

        diffs = compute_corrections(original, corrected)
        assert len(diffs) == 1
        assert diffs[0]["field"] == "invoice_number"
        assert diffs[0]["original"] == "INV-001"
        assert diffs[0]["corrected"] == "INV-002"

    @pytest.mark.unit
    def test_compute_corrections_multiple_field_changes(self):
        """Compute corrections returns diffs for multiple field changes."""
        original = [
            {"label_name": "name", "value": "John Doe"},
            {"label_name": "email", "value": "john@example.com"},
            {"label_name": "phone", "value": "555-1234"},
        ]
        corrected = [
            {"label_name": "name", "value": "Jane Doe"},
            {"label_name": "email", "value": "jane@example.com"},
            {"label_name": "phone", "value": "555-1234"},
        ]

        diffs = compute_corrections(original, corrected)
        assert len(diffs) == 2
        fields = {d["field"] for d in diffs}
        assert fields == {"name", "email"}

    @pytest.mark.unit
    def test_compute_corrections_no_changes(self):
        """Compute corrections returns empty list when no changes."""
        original = [
            {"label_name": "field1", "value": "value1"},
            {"label_name": "field2", "value": "value2"},
        ]
        corrected = [
            {"label_name": "field1", "value": "value1"},
            {"label_name": "field2", "value": "value2"},
        ]

        diffs = compute_corrections(original, corrected)
        assert len(diffs) == 0

    @pytest.mark.unit
    def test_compute_corrections_empty_original(self):
        """Compute corrections handles empty original results."""
        original = []
        corrected = [{"label_name": "field1", "value": "value1"}]

        diffs = compute_corrections(original, corrected)
        assert len(diffs) == 1
        assert diffs[0]["field"] == "field1"
        assert diffs[0]["original"] is None

    @pytest.mark.unit
    def test_compute_corrections_new_fields_included(self):
        """Compute corrections includes new fields not in original."""
        original = [{"label_name": "field1", "value": "value1"}]
        corrected = [
            {"label_name": "field1", "value": "value1"},
            {"label_name": "field2", "value": "value2"},  # New field
        ]

        diffs = compute_corrections(original, corrected)
        # New field2 is included with original=None
        assert len(diffs) == 1
        assert diffs[0]["field"] == "field2"
        assert diffs[0]["original"] is None
        assert diffs[0]["corrected"] == "value2"

    @pytest.mark.unit
    def test_compute_corrections_null_values(self):
        """Compute corrections handles null/None values."""
        original = [{"label_name": "optional_field", "value": None}]
        corrected = [{"label_name": "optional_field", "value": "now_has_value"}]

        diffs = compute_corrections(original, corrected)
        assert len(diffs) == 1
        assert diffs[0]["original"] is None
        assert diffs[0]["corrected"] == "now_has_value"


class TestReviewSubmission:
    """Test review submission (approve & correct)."""

    @pytest.mark.unit
    async def test_submit_review_approved(self, db_workspace):
        """Submitting approved review creates review record."""
        from src.database import get_connection, get_db_path
        from src.config import settings
        from datetime import datetime

        # Create a job with extraction result
        job_id = str(uuid.uuid4())
        schema_id = str(uuid.uuid4())
        result = [
            {"label_name": "invoice_number", "value": "INV-001"},
            {"label_name": "amount", "value": "100.00"},
        ]
        now = datetime.now().isoformat()

        db = await get_connection(get_db_path(settings.database_url))
        try:
            await db.execute(
                """INSERT INTO jobs
                (id, status, mode, result, schema_id, workspace_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (job_id, "completed", "cloud", json.dumps(result), schema_id, db_workspace, now),
            )
            await db.commit()
        finally:
            await db.close()

        # Submit approved review
        response = await submit_review(
            job_id=job_id,
            workspace_id=db_workspace,
            status="approved",
            reviewer_id="reviewer-1",
            review_time_ms=5000,
        )

        assert response["status"] == "approved"
        assert response["corrections"] is None
        assert response["created_at"] is not None

        # Verify job status changed
        job_review = await get_review(job_id, db_workspace)
        assert job_review is not None
        assert job_review["status"] == "approved"

    @pytest.mark.unit
    async def test_submit_review_corrected_with_diffs(self, db_workspace):
        """Submitting corrected review calculates and stores diffs."""
        from src.database import get_connection, get_db_path
        from src.config import settings
        from datetime import datetime

        job_id = str(uuid.uuid4())
        schema_id = str(uuid.uuid4())
        original = [
            {"label_name": "invoice_number", "value": "INV-001"},
            {"label_name": "amount", "value": "100.00"},
        ]
        corrected = [
            {"label_name": "invoice_number", "value": "INV-002"},
            {"label_name": "amount", "value": "150.00"},
        ]
        now = datetime.now().isoformat()

        db = await get_connection(get_db_path(settings.database_url))
        try:
            await db.execute(
                """INSERT INTO jobs
                (id, status, mode, result, schema_id, workspace_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (job_id, "completed", "cloud", json.dumps(original), schema_id, db_workspace, now),
            )
            await db.commit()
        finally:
            await db.close()

        response = await submit_review(
            job_id=job_id,
            workspace_id=db_workspace,
            status="corrected",
            corrected_result=corrected,
            reviewer_id="reviewer-1",
            review_time_ms=8000,
        )

        assert response["status"] == "corrected"
        assert response["corrections"] is not None
        assert len(response["corrections"]) == 2

        # Verify corrections captured correctly
        corrections = {c["field"]: c for c in response["corrections"]}
        assert corrections["invoice_number"]["original"] == "INV-001"
        assert corrections["invoice_number"]["corrected"] == "INV-002"
        assert corrections["amount"]["original"] == "100.00"
        assert corrections["amount"]["corrected"] == "150.00"

    @pytest.mark.unit
    async def test_submit_review_corrected_partial(self, db_workspace):
        """Submitting corrected review with some unchanged fields."""
        from src.database import get_connection, get_db_path
        from src.config import settings
        from datetime import datetime

        job_id = str(uuid.uuid4())
        schema_id = str(uuid.uuid4())
        original = [
            {"label_name": "field1", "value": "value1"},
            {"label_name": "field2", "value": "value2"},
            {"label_name": "field3", "value": "value3"},
        ]
        corrected = [
            {"label_name": "field1", "value": "value1"},  # Unchanged
            {"label_name": "field2", "value": "CORRECTED"},  # Changed
            {"label_name": "field3", "value": "value3"},  # Unchanged
        ]
        now = datetime.now().isoformat()

        db = await get_connection(get_db_path(settings.database_url))
        try:
            await db.execute(
                """INSERT INTO jobs
                (id, status, mode, result, schema_id, workspace_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (job_id, "completed", "cloud", json.dumps(original), schema_id, db_workspace, now),
            )
            await db.commit()
        finally:
            await db.close()

        response = await submit_review(
            job_id=job_id,
            workspace_id=db_workspace,
            status="corrected",
            corrected_result=corrected,
        )

        # Only 1 field changed
        assert len(response["corrections"]) == 1
        assert response["corrections"][0]["field"] == "field2"

    @pytest.mark.unit
    async def test_submit_review_nonexistent_job_raises_error(self, db_workspace):
        """Submitting review for nonexistent job raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await submit_review(
                job_id="nonexistent-job",
                workspace_id=db_workspace,
                status="approved",
            )

    @pytest.mark.unit
    async def test_submit_review_wrong_workspace_raises_error(self, db_workspace):
        """Submitting review with wrong workspace raises ValueError."""
        from src.database import get_connection, get_db_path
        from src.config import settings
        from datetime import datetime

        job_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        db = await get_connection(get_db_path(settings.database_url))
        try:
            await db.execute(
                """INSERT INTO jobs (id, status, mode, created_at, workspace_id)
                VALUES (?, ?, ?, ?, ?)""",
                (job_id, "completed", "cloud", now, db_workspace),
            )
            await db.commit()
        finally:
            await db.close()

        with pytest.raises(ValueError, match="not found"):
            await submit_review(
                job_id=job_id,
                workspace_id="wrong-workspace",
                status="approved",
            )

    @pytest.mark.unit
    async def test_submit_review_updates_job_status(self, db_workspace):
        """Submitting review updates job status to 'reviewed'."""
        from src.database import get_connection, get_db_path
        from src.config import settings
        from datetime import datetime

        job_id = str(uuid.uuid4())
        result = [{"label_name": "field", "value": "value"}]
        now = datetime.now().isoformat()

        db = await get_connection(get_db_path(settings.database_url))
        try:
            await db.execute(
                """INSERT INTO jobs
                (id, status, mode, result, workspace_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (job_id, "completed", "cloud", json.dumps(result), db_workspace, now),
            )
            await db.commit()
        finally:
            await db.close()

        await submit_review(
            job_id=job_id,
            workspace_id=db_workspace,
            status="approved",
        )

        # Verify job status changed
        db = await get_connection(get_db_path(settings.database_url))
        try:
            cursor = await db.execute("SELECT status FROM jobs WHERE id = ?", (job_id,))
            row = await cursor.fetchone()
            assert row[0] == "reviewed"
        finally:
            await db.close()


class TestReviewListing:
    """Test review listing and filtering."""

    @pytest.mark.unit
    async def test_list_reviews_empty(self, db_workspace):
        """Listing reviews on empty workspace returns empty list."""
        result = await list_reviews(db_workspace)
        assert result["reviews"] == []
        assert result["total"] == 0

    @pytest.mark.unit
    async def test_list_reviews_returns_all(self, db_workspace):
        """Listing reviews returns all reviews."""
        from src.database import get_connection, get_db_path
        from src.config import settings
        from datetime import datetime

        # Create multiple jobs and reviews
        job_ids = [str(uuid.uuid4()) for _ in range(3)]
        result = [{"label_name": "field", "value": "value"}]
        now = datetime.now().isoformat()

        db = await get_connection(get_db_path(settings.database_url))
        try:
            for job_id in job_ids:
                await db.execute(
                    """INSERT INTO jobs
                    (id, status, mode, result, workspace_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (job_id, "completed", "cloud", json.dumps(result), db_workspace, now),
                )
            await db.commit()
        finally:
            await db.close()

        # Submit reviews
        for job_id in job_ids:
            await submit_review(
                job_id=job_id,
                workspace_id=db_workspace,
                status="approved",
            )

        # List reviews
        response = await list_reviews(db_workspace)
        assert response["total"] == 3
        assert len(response["reviews"]) == 3

    @pytest.mark.unit
    async def test_list_reviews_filter_by_status_approved(self, db_workspace):
        """Listing reviews filters by 'approved' status."""
        from src.database import get_connection, get_db_path
        from src.config import settings
        from datetime import datetime

        job_ids = [str(uuid.uuid4()) for _ in range(2)]
        result = [{"label_name": "field", "value": "value"}]
        now = datetime.now().isoformat()

        db = await get_connection(get_db_path(settings.database_url))
        try:
            for job_id in job_ids:
                await db.execute(
                    """INSERT INTO jobs
                    (id, status, mode, result, workspace_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (job_id, "completed", "cloud", json.dumps(result), db_workspace, now),
                )
            await db.commit()
        finally:
            await db.close()

        await submit_review(
            job_id=job_ids[0],
            workspace_id=db_workspace,
            status="approved",
        )
        await submit_review(
            job_id=job_ids[1],
            workspace_id=db_workspace,
            status="corrected",
            corrected_result=[{"label_name": "field", "value": "CORRECTED"}],
        )

        response = await list_reviews(db_workspace, status_filter="approved")
        assert response["total"] == 1
        assert response["reviews"][0]["status"] == "approved"

    @pytest.mark.unit
    async def test_list_reviews_filter_by_status_corrected(self, db_workspace):
        """Listing reviews filters by 'corrected' status."""
        from src.database import get_connection, get_db_path
        from src.config import settings
        from datetime import datetime

        job_ids = [str(uuid.uuid4()) for _ in range(2)]
        result = [{"label_name": "field", "value": "value"}]
        now = datetime.now().isoformat()

        db = await get_connection(get_db_path(settings.database_url))
        try:
            for job_id in job_ids:
                await db.execute(
                    """INSERT INTO jobs
                    (id, status, mode, result, workspace_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (job_id, "completed", "cloud", json.dumps(result), db_workspace, now),
                )
            await db.commit()
        finally:
            await db.close()

        await submit_review(
            job_id=job_ids[0],
            workspace_id=db_workspace,
            status="approved",
        )
        await submit_review(
            job_id=job_ids[1],
            workspace_id=db_workspace,
            status="corrected",
            corrected_result=[{"label_name": "field", "value": "CORRECTED"}],
        )

        response = await list_reviews(db_workspace, status_filter="corrected")
        assert response["total"] == 1
        assert response["reviews"][0]["status"] == "corrected"

    @pytest.mark.unit
    async def test_list_reviews_pagination(self, db_workspace):
        """Listing reviews respects limit and offset."""
        from src.database import get_connection, get_db_path
        from src.config import settings
        from datetime import datetime

        # Create 5 jobs and reviews
        job_ids = [str(uuid.uuid4()) for _ in range(5)]
        result = [{"label_name": "field", "value": "value"}]
        now = datetime.now().isoformat()

        db = await get_connection(get_db_path(settings.database_url))
        try:
            for job_id in job_ids:
                await db.execute(
                    """INSERT INTO jobs
                    (id, status, mode, result, workspace_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (job_id, "completed", "cloud", json.dumps(result), db_workspace, now),
                )
            await db.commit()
        finally:
            await db.close()

        for job_id in job_ids:
            await submit_review(
                job_id=job_id,
                workspace_id=db_workspace,
                status="approved",
            )

        # Get first page
        page1 = await list_reviews(db_workspace, limit=2, offset=0)
        assert len(page1["reviews"]) == 2
        assert page1["total"] == 5

        # Get second page
        page2 = await list_reviews(db_workspace, limit=2, offset=2)
        assert len(page2["reviews"]) == 2

        # IDs should be different
        page1_ids = {r["id"] for r in page1["reviews"]}
        page2_ids = {r["id"] for r in page2["reviews"]}
        assert page1_ids != page2_ids

    @pytest.mark.unit
    async def test_list_reviews_ordered_by_date(self, db_workspace):
        """Listing reviews returns newest first."""
        from src.database import get_connection, get_db_path
        from src.config import settings
        from datetime import datetime, timedelta

        job_ids = [str(uuid.uuid4()) for _ in range(3)]
        result = [{"label_name": "field", "value": "value"}]
        base_time = datetime.now()

        db = await get_connection(get_db_path(settings.database_url))
        try:
            for i, job_id in enumerate(job_ids):
                time = (base_time - timedelta(hours=i)).isoformat()
                await db.execute(
                    """INSERT INTO jobs
                    (id, status, mode, result, workspace_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (job_id, "completed", "cloud", json.dumps(result), db_workspace, time),
                )
            await db.commit()
        finally:
            await db.close()

        # Submit in reverse chronological order
        for job_id in reversed(job_ids):
            await submit_review(
                job_id=job_id,
                workspace_id=db_workspace,
                status="approved",
            )

        response = await list_reviews(db_workspace)
        # Most recent should be first
        assert response["reviews"][0]["job_id"] == job_ids[0]


class TestReviewRetrieval:
    """Test individual review retrieval."""

    @pytest.mark.unit
    async def test_get_review_returns_review_detail(self, db_workspace):
        """Getting review returns complete review data."""
        from src.database import get_connection, get_db_path
        from src.config import settings
        from datetime import datetime

        job_id = str(uuid.uuid4())
        original = [
            {"label_name": "field1", "value": "value1"},
            {"label_name": "field2", "value": "value2"},
        ]
        now = datetime.now().isoformat()

        db = await get_connection(get_db_path(settings.database_url))
        try:
            await db.execute(
                """INSERT INTO jobs
                (id, status, mode, result, workspace_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (job_id, "completed", "cloud", json.dumps(original), db_workspace, now),
            )
            await db.commit()
        finally:
            await db.close()

        await submit_review(
            job_id=job_id,
            workspace_id=db_workspace,
            status="approved",
            reviewer_id="reviewer-123",
            review_time_ms=3000,
        )

        review = await get_review(job_id, db_workspace)
        assert review is not None
        assert review["job_id"] == job_id
        assert review["status"] == "approved"
        assert review["reviewer_id"] == "reviewer-123"
        assert review["review_time_ms"] == 3000
        assert review["original_result"] == original

    @pytest.mark.unit
    async def test_get_review_with_corrections(self, db_workspace):
        """Getting review returns corrections."""
        from src.database import get_connection, get_db_path
        from src.config import settings
        from datetime import datetime

        job_id = str(uuid.uuid4())
        original = [
            {"label_name": "field1", "value": "old"},
            {"label_name": "field2", "value": "unchanged"},
        ]
        corrected = [
            {"label_name": "field1", "value": "new"},
            {"label_name": "field2", "value": "unchanged"},
        ]
        now = datetime.now().isoformat()

        db = await get_connection(get_db_path(settings.database_url))
        try:
            await db.execute(
                """INSERT INTO jobs
                (id, status, mode, result, workspace_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (job_id, "completed", "cloud", json.dumps(original), db_workspace, now),
            )
            await db.commit()
        finally:
            await db.close()

        await submit_review(
            job_id=job_id,
            workspace_id=db_workspace,
            status="corrected",
            corrected_result=corrected,
        )

        review = await get_review(job_id, db_workspace)
        assert review["corrections"] is not None
        assert len(review["corrections"]) == 1
        assert review["corrected_result"] == corrected

    @pytest.mark.unit
    async def test_get_review_nonexistent_returns_none(self, db_workspace):
        """Getting nonexistent review returns None."""
        review = await get_review("nonexistent-job", db_workspace)
        assert review is None

    @pytest.mark.unit
    async def test_get_review_wrong_workspace_returns_none(self, db_workspace):
        """Getting review from wrong workspace returns None."""
        from src.database import get_connection, get_db_path
        from src.config import settings
        from datetime import datetime

        job_id = str(uuid.uuid4())
        result = [{"label_name": "field", "value": "value"}]
        now = datetime.now().isoformat()

        db = await get_connection(get_db_path(settings.database_url))
        try:
            await db.execute(
                """INSERT INTO jobs
                (id, status, mode, result, workspace_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (job_id, "completed", "cloud", json.dumps(result), db_workspace, now),
            )
            await db.commit()
        finally:
            await db.close()

        await submit_review(
            job_id=job_id,
            workspace_id=db_workspace,
            status="approved",
        )

        review = await get_review(job_id, "wrong-workspace")
        assert review is None
