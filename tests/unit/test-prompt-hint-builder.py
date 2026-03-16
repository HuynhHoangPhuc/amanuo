"""Unit tests for prompt hint builder — building hints from corrections."""

import importlib
import json
import uuid
import pytest

_hint_builder = importlib.import_module("src.services.prompt-hint-builder")
get_hints = _hint_builder.get_hints
_build_hints = _hint_builder._build_hints
_is_stale = _hint_builder._is_stale
invalidate = _hint_builder.invalidate


class TestBuildHints:
    """Test hint building from corrections."""

    @pytest.mark.unit
    async def test_build_hints_no_corrections_returns_empty(self, db_workspace):
        """Building hints with no corrections returns empty string."""
        schema_id = str(uuid.uuid4())
        hints = await _build_hints(schema_id)
        assert hints == ""

    @pytest.mark.unit
    async def test_build_hints_insufficient_corrections(self, db_workspace):
        """Building hints with insufficient corrections returns empty."""
        from src.database import get_connection, get_db_path
        from src.config import settings
        from datetime import datetime

        schema_id = str(uuid.uuid4())
        job_id = str(uuid.uuid4())
        original = [{"label_name": "field1", "value": "value1"}]
        corrected = [{"label_name": "field1", "value": "CORRECTED"}]
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

        _review = importlib.import_module("src.services.review-service")
        await _review.submit_review(
            job_id,
            db_workspace,
            "corrected",
            corrected_result=corrected,
        )

        # Only 1 correction, but minimum is 10
        hints = await _build_hints(schema_id)
        assert hints == ""

    @pytest.mark.unit
    async def test_build_hints_sufficient_corrections(self, db_workspace):
        """Building hints with sufficient corrections generates hint text."""
        from src.database import get_connection, get_db_path
        from src.config import settings
        from datetime import datetime

        schema_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        db = await get_connection(get_db_path(settings.database_url))
        try:
            # Create 10 jobs with same correction pattern
            for i in range(10):
                job_id = str(uuid.uuid4())
                original = [{"label_name": "amount", "value": "$100"}]
                await db.execute(
                    """INSERT INTO jobs
                    (id, status, mode, result, schema_id, workspace_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (job_id, "completed", "cloud", json.dumps(original), schema_id, db_workspace, now),
                )
            await db.commit()
        finally:
            await db.close()

        _review = importlib.import_module("src.services.review-service")

        # Submit 10 corrections with same pattern
        for i in range(10):
            job_id = str(uuid.uuid4())
            db = await get_connection(get_db_path(settings.database_url))
            try:
                original = [{"label_name": "amount", "value": "$100"}]
                await db.execute(
                    """INSERT INTO jobs
                    (id, status, mode, result, schema_id, workspace_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (job_id, "completed", "cloud", json.dumps(original), schema_id, db_workspace, now),
                )
                await db.commit()
            finally:
                await db.close()

            corrected = [{"label_name": "amount", "value": "100.00"}]
            await _review.submit_review(
                job_id,
                db_workspace,
                "corrected",
                corrected_result=corrected,
            )

        # Should generate hints now
        hints = await _build_hints(schema_id)
        assert hints != ""
        assert "amount" in hints
        assert "100.00" in hints or "$100" in hints

    @pytest.mark.unit
    async def test_build_hints_multiple_patterns(self, db_workspace):
        """Building hints shows top 3 patterns per field."""
        from src.database import get_connection, get_db_path
        from src.config import settings
        from datetime import datetime

        schema_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        _review = importlib.import_module("src.services.review-service")

        # Create 15 jobs with varying corrections for same field
        patterns = [
            ("old1", "new1"),  # 5x
            ("old2", "new2"),  # 5x
            ("old3", "new3"),  # 3x
            ("old4", "new4"),  # 2x
        ]

        job_counter = 0
        for old, new in patterns:
            count = [5, 5, 3, 2][patterns.index((old, new))]
            for _ in range(count):
                job_id = str(uuid.uuid4())
                job_counter += 1

                db = await get_connection(get_db_path(settings.database_url))
                try:
                    original = [{"label_name": "status", "value": old}]
                    await db.execute(
                        """INSERT INTO jobs
                        (id, status, mode, result, schema_id, workspace_id, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (job_id, "completed", "cloud", json.dumps(original), schema_id, db_workspace, now),
                    )
                    await db.commit()
                finally:
                    await db.close()

                corrected = [{"label_name": "status", "value": new}]
                await _review.submit_review(
                    job_id,
                    db_workspace,
                    "corrected",
                    corrected_result=corrected,
                )

        hints = await _build_hints(schema_id)
        # Should show top 3 patterns, not all 4
        lines = hints.split("\n")
        pattern_lines = [l for l in lines if "->" in l]
        assert len(pattern_lines) == 3

    @pytest.mark.unit
    async def test_build_hints_multiple_fields(self, db_workspace):
        """Building hints aggregates multiple fields."""
        from src.database import get_connection, get_db_path
        from src.config import settings
        from datetime import datetime

        schema_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        _review = importlib.import_module("src.services.review-service")

        # Create 10 jobs with corrections for 2 fields
        for i in range(10):
            job_id = str(uuid.uuid4())
            original = [
                {"label_name": "field1", "value": "old1"},
                {"label_name": "field2", "value": "old2"},
            ]

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

            corrected = [
                {"label_name": "field1", "value": "new1"},
                {"label_name": "field2", "value": "new2"},
            ]
            await _review.submit_review(
                job_id,
                db_workspace,
                "corrected",
                corrected_result=corrected,
            )

        hints = await _build_hints(schema_id)
        assert "field1" in hints
        assert "field2" in hints

    @pytest.mark.unit
    async def test_build_hints_caches_result(self, db_workspace):
        """Building hints caches the result."""
        schema_id = str(uuid.uuid4())

        # Clear cache
        _hint_builder._hint_cache.pop(schema_id, None)

        # First build
        hints1 = await _build_hints(schema_id)

        # Should be cached now
        assert schema_id in _hint_builder._hint_cache

        # Second call should return cached value
        hints2 = await _build_hints(schema_id)
        assert hints1 == hints2

    @pytest.mark.unit
    async def test_build_hints_resets_correction_counter(self, db_workspace):
        """Building hints resets correction counter."""
        schema_id = str(uuid.uuid4())

        _hint_builder._correction_counts[schema_id] = 5
        await _build_hints(schema_id)

        assert _hint_builder._correction_counts[schema_id] == 0


class TestGetHints:
    """Test hint retrieval with staleness checking."""

    @pytest.mark.unit
    async def test_get_hints_empty_returns_empty(self, db_workspace):
        """Getting hints for schema with no corrections returns empty."""
        schema_id = str(uuid.uuid4())
        _hint_builder._hint_cache.pop(schema_id, None)
        _hint_builder._correction_counts.pop(schema_id, None)

        hints = await get_hints(schema_id)
        assert hints == ""

    @pytest.mark.unit
    async def test_get_hints_returns_cached_if_not_stale(self, db_workspace):
        """Getting hints returns cached value if not stale."""
        schema_id = str(uuid.uuid4())
        cached_hints = "cached hint text"

        _hint_builder._hint_cache[schema_id] = cached_hints
        _hint_builder._correction_counts[schema_id] = 5  # Not stale (< 10)

        hints = await get_hints(schema_id)
        assert hints == cached_hints

    @pytest.mark.unit
    async def test_get_hints_rebuilds_if_stale(self, db_workspace):
        """Getting hints rebuilds if stale."""
        schema_id = str(uuid.uuid4())

        _hint_builder._hint_cache[schema_id] = "old hint"
        _hint_builder._correction_counts[schema_id] = 10  # Stale (>= 10)

        hints = await get_hints(schema_id)
        # Should rebuild (return empty since no actual corrections)
        assert hints == ""
        # Counter should reset
        assert _hint_builder._correction_counts[schema_id] == 0


class TestInvalidate:
    """Test cache invalidation."""

    @pytest.mark.unit
    async def test_invalidate_increments_counter(self, db_workspace):
        """Invalidating increments correction counter."""
        schema_id = str(uuid.uuid4())
        _hint_builder._correction_counts.pop(schema_id, None)

        assert _hint_builder._correction_counts.get(schema_id, 0) == 0

        await invalidate(schema_id)
        assert _hint_builder._correction_counts[schema_id] == 1

        await invalidate(schema_id)
        assert _hint_builder._correction_counts[schema_id] == 2

    @pytest.mark.unit
    async def test_invalidate_triggers_rebuild_at_threshold(self, db_workspace):
        """Invalidating at threshold triggers rebuild."""
        schema_id = str(uuid.uuid4())

        _hint_builder._correction_counts[schema_id] = 9
        assert _is_stale(schema_id) is False

        await invalidate(schema_id)
        assert _hint_builder._correction_counts[schema_id] == 10
        assert _is_stale(schema_id) is True


class TestStalenessCheck:
    """Test staleness checking."""

    @pytest.mark.unit
    def test_is_stale_false_below_threshold(self):
        """Stale check returns False below threshold."""
        schema_id = str(uuid.uuid4())
        _hint_builder._correction_counts[schema_id] = 5

        assert _is_stale(schema_id) is False

    @pytest.mark.unit
    def test_is_stale_true_at_threshold(self):
        """Stale check returns True at threshold."""
        schema_id = str(uuid.uuid4())
        _hint_builder._correction_counts[schema_id] = 10

        assert _is_stale(schema_id) is True

    @pytest.mark.unit
    def test_is_stale_true_above_threshold(self):
        """Stale check returns True above threshold."""
        schema_id = str(uuid.uuid4())
        _hint_builder._correction_counts[schema_id] = 15

        assert _is_stale(schema_id) is True

    @pytest.mark.unit
    def test_is_stale_unknown_schema_returns_false(self):
        """Stale check returns False for unknown schema."""
        schema_id = str(uuid.uuid4())
        _hint_builder._correction_counts.pop(schema_id, None)

        assert _is_stale(schema_id) is False
