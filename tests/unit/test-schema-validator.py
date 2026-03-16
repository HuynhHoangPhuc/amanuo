"""Unit tests for schema validation logic."""

import pytest

from src.schemas import (
    ExtractionSchema,
    SchemaField,
    SchemaValidationError,
    validate_or_raise,
    validate_schema,
)


def _make_schema(fields_data: list[dict]) -> ExtractionSchema:
    return ExtractionSchema(fields=[SchemaField(**f) for f in fields_data])


class TestValidateSchema:
    def test_valid_schema(self):
        schema = _make_schema([
            {"label_name": "color", "data_type": "plain text", "occurrence": "required once"},
            {"label_name": "model", "data_type": "plain text", "occurrence": "optional once"},
        ])
        errors = validate_schema(schema)
        assert errors == []

    def test_duplicate_labels(self):
        schema = _make_schema([
            {"label_name": "color", "data_type": "plain text", "occurrence": "required once"},
            {"label_name": "color", "data_type": "number", "occurrence": "required once"},
        ])
        errors = validate_schema(schema)
        assert any("Duplicate" in e for e in errors)

    def test_invalid_label_characters(self):
        schema = _make_schema([
            {"label_name": "color@!", "data_type": "plain text", "occurrence": "required once"},
        ])
        errors = validate_schema(schema)
        assert any("Invalid characters" in e for e in errors)

    def test_valid_label_with_dots(self):
        schema = _make_schema([
            {"label_name": "address.street", "data_type": "plain text", "occurrence": "required once"},
        ])
        errors = validate_schema(schema)
        assert errors == []

    def test_nesting_depth_exceeded(self):
        schema = _make_schema([
            {"label_name": "a.b.c.d", "data_type": "plain text", "occurrence": "required once"},
        ])
        errors = validate_schema(schema)
        assert any("nesting depth" in e for e in errors)

    def test_nesting_depth_at_limit(self):
        schema = _make_schema([
            {"label_name": "a.b.c", "data_type": "plain text", "occurrence": "required once"},
        ])
        errors = validate_schema(schema)
        assert errors == []

    def test_long_prompt_rejected(self):
        schema = _make_schema([
            {
                "label_name": "x",
                "data_type": "plain text",
                "occurrence": "required once",
                "prompt_for_label": "a" * 501,
            },
        ])
        errors = validate_schema(schema)
        assert any("exceeds" in e for e in errors)

    def test_label_with_spaces_and_hyphens(self):
        schema = _make_schema([
            {"label_name": "full name", "data_type": "plain text", "occurrence": "required once"},
            {"label_name": "engine-number", "data_type": "plain text", "occurrence": "required once"},
        ])
        errors = validate_schema(schema)
        assert errors == []


class TestValidateOrRaise:
    def test_valid_schema_no_exception(self):
        schema = _make_schema([
            {"label_name": "test", "data_type": "plain text", "occurrence": "required once"},
        ])
        validate_or_raise(schema)  # Should not raise

    def test_invalid_schema_raises(self):
        schema = _make_schema([
            {"label_name": "a.b.c.d", "data_type": "plain text", "occurrence": "required once"},
        ])
        with pytest.raises(SchemaValidationError) as exc:
            validate_or_raise(schema)
        assert len(exc.value.errors) > 0
