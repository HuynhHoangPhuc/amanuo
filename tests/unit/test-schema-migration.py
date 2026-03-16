"""Unit tests for schema migration and field diff analysis."""

import importlib
import pytest

_migration = importlib.import_module("src.schemas.schema-migration")

FieldDiff = _migration.FieldDiff
diff_fields = _migration.diff_fields
validate_migration = _migration.validate_migration


class TestFieldDiffAnalysis:
    """Test field diff analysis."""

    @pytest.mark.unit
    def test_diff_no_changes(self):
        """Diff with identical fields shows no changes."""
        old = [{"label_name": "a", "data_type": "text", "occurrence": "required once"}]
        new = [{"label_name": "a", "data_type": "text", "occurrence": "required once"}]

        diff = diff_fields(old, new)
        assert len(diff.added) == 0
        assert len(diff.removed) == 0
        assert len(diff.type_changed) == 0
        assert len(diff.unchanged) == 1
        assert diff.unchanged[0] == "a"

    @pytest.mark.unit
    def test_diff_field_added(self):
        """Diff shows added fields."""
        old = [{"label_name": "a", "data_type": "text", "occurrence": "required once"}]
        new = [
            {"label_name": "a", "data_type": "text", "occurrence": "required once"},
            {"label_name": "b", "data_type": "text", "occurrence": "optional once"},
        ]

        diff = diff_fields(old, new)
        assert "b" in diff.added
        assert len(diff.removed) == 0

    @pytest.mark.unit
    def test_diff_field_removed(self):
        """Diff shows removed fields."""
        old = [
            {"label_name": "a", "data_type": "text", "occurrence": "required once"},
            {"label_name": "b", "data_type": "text", "occurrence": "required once"},
        ]
        new = [{"label_name": "a", "data_type": "text", "occurrence": "required once"}]

        diff = diff_fields(old, new)
        assert "b" in diff.removed
        assert len(diff.added) == 0

    @pytest.mark.unit
    def test_diff_type_changed(self):
        """Diff shows type changes."""
        old = [{"label_name": "a", "data_type": "text", "occurrence": "required once"}]
        new = [{"label_name": "a", "data_type": "number", "occurrence": "required once"}]

        diff = diff_fields(old, new)
        assert "a" in diff.type_changed
        assert len(diff.unchanged) == 0

    @pytest.mark.unit
    def test_diff_occurrence_changed(self):
        """Diff shows occurrence changes."""
        old = [{"label_name": "a", "data_type": "text", "occurrence": "required once"}]
        new = [{"label_name": "a", "data_type": "text", "occurrence": "optional once"}]

        diff = diff_fields(old, new)
        assert "a" in diff.type_changed

    @pytest.mark.unit
    def test_diff_prompt_changed(self):
        """Diff shows prompt-only changes."""
        old = [
            {
                "label_name": "a",
                "data_type": "text",
                "occurrence": "required once",
                "prompt_for_label": "Old",
            }
        ]
        new = [
            {
                "label_name": "a",
                "data_type": "text",
                "occurrence": "required once",
                "prompt_for_label": "New",
            }
        ]

        diff = diff_fields(old, new)
        assert "a" in diff.prompt_changed
        assert "a" not in diff.type_changed

    @pytest.mark.unit
    def test_diff_multiple_changes(self):
        """Diff shows multiple types of changes."""
        old = [
            {"label_name": "a", "data_type": "text", "occurrence": "required once"},
            {"label_name": "b", "data_type": "text", "occurrence": "required once"},
            {"label_name": "c", "data_type": "text", "occurrence": "required once"},
        ]
        new = [
            {"label_name": "a", "data_type": "number", "occurrence": "required once"},  # type changed
            {"label_name": "b", "data_type": "text", "occurrence": "required once"},      # unchanged
            {"label_name": "d", "data_type": "text", "occurrence": "optional once"},      # added
        ]

        diff = diff_fields(old, new)
        assert "a" in diff.type_changed
        assert "b" in diff.unchanged
        assert "c" in diff.removed
        assert "d" in diff.added

    @pytest.mark.unit
    def test_diff_sorted_output(self):
        """Diff output lists are sorted."""
        old = [
            {"label_name": "z", "data_type": "text", "occurrence": "required once"},
            {"label_name": "a", "data_type": "text", "occurrence": "required once"},
        ]
        new = [
            {"label_name": "m", "data_type": "text", "occurrence": "required once"},
        ]

        diff = diff_fields(old, new)
        assert diff.removed == ["a", "z"]  # sorted


class TestMigrationValidation:
    """Test migration validation and warnings."""

    @pytest.mark.unit
    def test_validate_no_changes_no_warnings(self):
        """No changes returns no warnings."""
        old = [{"label_name": "a", "data_type": "text", "occurrence": "required once"}]
        new = [{"label_name": "a", "data_type": "text", "occurrence": "required once"}]

        warnings = validate_migration(old, new)
        assert len(warnings) == 0

    @pytest.mark.unit
    def test_validate_adding_field_no_warnings(self):
        """Adding field generates no warnings."""
        old = [{"label_name": "a", "data_type": "text", "occurrence": "required once"}]
        new = [
            {"label_name": "a", "data_type": "text", "occurrence": "required once"},
            {"label_name": "b", "data_type": "text", "occurrence": "optional once"},
        ]

        warnings = validate_migration(old, new)
        assert len(warnings) == 0

    @pytest.mark.unit
    def test_validate_removing_field_warning(self):
        """Removing field generates warning."""
        old = [
            {"label_name": "a", "data_type": "text", "occurrence": "required once"},
            {"label_name": "b", "data_type": "text", "occurrence": "required once"},
        ]
        new = [{"label_name": "a", "data_type": "text", "occurrence": "required once"}]

        warnings = validate_migration(old, new)
        assert any("removed" in w.lower() for w in warnings)
        assert any("b" in w for w in warnings)

    @pytest.mark.unit
    def test_validate_type_change_warning(self):
        """Changing field type generates warning."""
        old = [{"label_name": "a", "data_type": "text", "occurrence": "required once"}]
        new = [{"label_name": "a", "data_type": "number", "occurrence": "required once"}]

        warnings = validate_migration(old, new)
        assert any("data_type" in w.lower() for w in warnings)
        assert any("breaking" in w.lower() for w in warnings)

    @pytest.mark.unit
    def test_validate_occurrence_change_warning(self):
        """Changing field occurrence generates warning."""
        old = [{"label_name": "a", "data_type": "text", "occurrence": "required once"}]
        new = [{"label_name": "a", "data_type": "text", "occurrence": "optional once"}]

        warnings = validate_migration(old, new)
        assert any("occurrence" in w.lower() for w in warnings)
        assert any("breaking" in w.lower() for w in warnings)

    @pytest.mark.unit
    def test_validate_required_to_optional_specific_warning(self):
        """Required→optional change triggers specific warning."""
        old = [{"label_name": "a", "data_type": "text", "occurrence": "required once"}]
        new = [{"label_name": "a", "data_type": "text", "occurrence": "optional once"}]

        warnings = validate_migration(old, new)
        assert any("required to optional" in w.lower() for w in warnings)

    @pytest.mark.unit
    def test_validate_multiple_breaking_changes(self):
        """Multiple breaking changes generate multiple warnings."""
        old = [
            {"label_name": "a", "data_type": "text", "occurrence": "required once"},
            {"label_name": "b", "data_type": "text", "occurrence": "required once"},
            {"label_name": "c", "data_type": "text", "occurrence": "required once"},
        ]
        new = [
            {"label_name": "a", "data_type": "number", "occurrence": "required once"},  # type change
            # b removed
            {"label_name": "c", "data_type": "text", "occurrence": "optional once"},    # occurrence change
        ]

        warnings = validate_migration(old, new)
        assert len(warnings) >= 3  # At least: type change, removed, occurrence change
