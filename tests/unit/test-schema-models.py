"""Unit tests for schema Pydantic models."""

import pytest

from src.schemas import ExtractionResult, ExtractionSchema, SchemaField


class TestSchemaField:
    def test_valid_field(self):
        f = SchemaField(label_name="color", data_type="plain text", occurrence="required once")
        assert f.label_name == "color"
        assert f.prompt_for_label is None

    def test_with_prompt(self):
        f = SchemaField(
            label_name="color",
            data_type="plain text",
            occurrence="required once",
            prompt_for_label="The vehicle color",
        )
        assert f.prompt_for_label == "The vehicle color"

    def test_all_data_types(self):
        for dt in ["plain text", "number", "address", "datetime", "currency", "checkbox"]:
            f = SchemaField(label_name="test", data_type=dt, occurrence="required once")
            assert f.data_type == dt

    def test_all_occurrences(self):
        for occ in ["optional once", "optional multiple", "required once", "required multiple"]:
            f = SchemaField(label_name="test", data_type="plain text", occurrence=occ)
            assert f.occurrence == occ

    def test_invalid_data_type(self):
        with pytest.raises(Exception):
            SchemaField(label_name="test", data_type="invalid", occurrence="required once")

    def test_empty_label_name_rejected(self):
        with pytest.raises(Exception):
            SchemaField(label_name="", data_type="plain text", occurrence="required once")


class TestExtractionSchema:
    def test_valid_schema(self):
        s = ExtractionSchema(fields=[
            SchemaField(label_name="color", data_type="plain text", occurrence="required once"),
        ])
        assert len(s.fields) == 1

    def test_empty_fields_rejected(self):
        with pytest.raises(Exception):
            ExtractionSchema(fields=[])

    def test_max_fields(self):
        fields = [
            SchemaField(label_name=f"field_{i}", data_type="plain text", occurrence="required once")
            for i in range(50)
        ]
        s = ExtractionSchema(fields=fields)
        assert len(s.fields) == 50

    def test_over_max_fields_rejected(self):
        fields = [
            SchemaField(label_name=f"field_{i}", data_type="plain text", occurrence="required once")
            for i in range(51)
        ]
        with pytest.raises(Exception):
            ExtractionSchema(fields=fields)


class TestExtractionResult:
    def test_string_value(self):
        r = ExtractionResult(label_name="color", data_type="plain text", value="White")
        assert r.value == "White"

    def test_list_value(self):
        r = ExtractionResult(label_name="items", data_type="plain text", value=["a", "b"])
        assert r.value == ["a", "b"]

    def test_null_value(self):
        r = ExtractionResult(label_name="missing", data_type="plain text")
        assert r.value is None

    def test_with_confidence(self):
        r = ExtractionResult(label_name="x", data_type="plain text", value="y", confidence=0.95)
        assert r.confidence == 0.95

    def test_serialization_roundtrip(self):
        r = ExtractionResult(label_name="color", data_type="plain text", value="Blue")
        data = r.model_dump()
        r2 = ExtractionResult(**data)
        assert r2.value == "Blue"
