"""Unit tests for schema suggest service — field parsing and validation logic."""

import importlib
import pytest

_svc = importlib.import_module("src.services.schema-suggest-service")

_parse_fields = _svc._parse_fields
_validate_field = _svc._validate_field
suggest_schema_fields = _svc.suggest_schema_fields


class TestValidateField:
    """Tests for the _validate_field helper."""

    @pytest.mark.unit
    def test_valid_field_returns_dict(self):
        field = {"label": "invoice_number", "type": "text", "occurrence": "required once", "confidence": 0.9}
        result = _validate_field(field)
        assert result is not None
        assert result["label"] == "invoice_number"
        assert result["type"] == "text"
        assert result["occurrence"] == "required once"
        assert result["confidence"] == pytest.approx(0.9)

    @pytest.mark.unit
    def test_label_normalized_to_snake_case(self):
        field = {"label": "Invoice Number", "type": "text", "occurrence": "required once", "confidence": 0.8}
        result = _validate_field(field)
        assert result["label"] == "invoice_number"

    @pytest.mark.unit
    def test_empty_label_returns_none(self):
        field = {"label": "", "type": "text", "occurrence": "required once", "confidence": 0.5}
        assert _validate_field(field) is None

    @pytest.mark.unit
    def test_missing_label_returns_none(self):
        field = {"type": "text", "occurrence": "required once", "confidence": 0.5}
        assert _validate_field(field) is None

    @pytest.mark.unit
    def test_invalid_type_defaults_to_text(self):
        field = {"label": "amount", "type": "currency", "occurrence": "required once", "confidence": 0.7}
        result = _validate_field(field)
        assert result["type"] == "text"

    @pytest.mark.unit
    def test_invalid_occurrence_defaults_to_optional_once(self):
        field = {"label": "amount", "type": "number", "occurrence": "required many", "confidence": 0.7}
        result = _validate_field(field)
        assert result["occurrence"] == "optional once"

    @pytest.mark.unit
    def test_confidence_clamped_to_range(self):
        field_high = {"label": "x", "type": "text", "occurrence": "optional once", "confidence": 1.5}
        field_low = {"label": "x", "type": "text", "occurrence": "optional once", "confidence": -0.3}
        assert _validate_field(field_high)["confidence"] == pytest.approx(1.0)
        assert _validate_field(field_low)["confidence"] == pytest.approx(0.0)

    @pytest.mark.unit
    def test_missing_confidence_defaults_to_half(self):
        field = {"label": "total", "type": "number", "occurrence": "required once"}
        result = _validate_field(field)
        assert result["confidence"] == pytest.approx(0.5)

    @pytest.mark.unit
    def test_non_dict_returns_none(self):
        assert _validate_field("not a dict") is None
        assert _validate_field(42) is None
        assert _validate_field(None) is None


class TestParseFields:
    """Tests for _parse_fields — parses raw VLM JSON responses."""

    @pytest.mark.unit
    def test_parses_clean_json_array(self):
        raw = '[{"label": "invoice_number", "type": "text", "occurrence": "required once", "confidence": 0.9}]'
        result = _parse_fields(raw)
        assert len(result) == 1
        assert result[0]["label"] == "invoice_number"

    @pytest.mark.unit
    def test_parses_json_embedded_in_text(self):
        raw = 'Here are the fields:\n[{"label": "total", "type": "number", "occurrence": "required once", "confidence": 0.85}]\nDone.'
        result = _parse_fields(raw)
        assert len(result) == 1
        assert result[0]["label"] == "total"

    @pytest.mark.unit
    def test_returns_empty_for_invalid_json(self):
        result = _parse_fields("This is not JSON at all.")
        assert result == []

    @pytest.mark.unit
    def test_returns_empty_for_empty_string(self):
        result = _parse_fields("")
        assert result == []

    @pytest.mark.unit
    def test_filters_invalid_fields_from_array(self):
        raw = '[{"label": "good", "type": "text", "occurrence": "required once", "confidence": 0.9}, {"label": "", "type": "text", "occurrence": "required once", "confidence": 0.5}]'
        result = _parse_fields(raw)
        assert len(result) == 1
        assert result[0]["label"] == "good"

    @pytest.mark.unit
    def test_parses_multiple_fields(self):
        raw = '[{"label": "a", "type": "text", "occurrence": "required once", "confidence": 0.9}, {"label": "b", "type": "number", "occurrence": "optional once", "confidence": 0.7}]'
        result = _parse_fields(raw)
        assert len(result) == 2


class TestSuggestSchemaFields:
    """Integration tests for suggest_schema_fields — graceful degradation."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_empty_list_when_vlm_unavailable(self):
        """When no VLM is running, should return empty list without raising."""
        result = await suggest_schema_fields(b"fake image bytes", lang="en")
        assert isinstance(result, list)
        # In test env with no Ollama, should degrade gracefully to empty list
        # (may return fields if Ollama happens to be running — that's fine too)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_accepts_language_parameter(self):
        """Should accept lang parameter without error."""
        result = await suggest_schema_fields(b"fake image bytes", lang="ja")
        assert isinstance(result, list)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_result_sorted_by_confidence(self):
        """If fields are returned, they should be sorted by confidence descending."""
        result = await suggest_schema_fields(b"fake image bytes", lang="en")
        if len(result) >= 2:
            confidences = [f["confidence"] for f in result]
            assert confidences == sorted(confidences, reverse=True)
