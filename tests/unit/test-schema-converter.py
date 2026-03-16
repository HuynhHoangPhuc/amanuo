"""Unit tests for schema converter (JSON Schema, Gemini, extraction prompt, normalizer)."""


from src.schemas import (
    ExtractionSchema,
    SchemaField,
    normalize_output,
    to_extraction_prompt,
    to_gemini_schema,
    to_json_schema,
)


def _make_schema(fields_data: list[dict]) -> ExtractionSchema:
    return ExtractionSchema(fields=[SchemaField(**f) for f in fields_data])


class TestToJsonSchema:
    def test_basic_string_field(self):
        schema = _make_schema([
            {"label_name": "color", "data_type": "plain text", "occurrence": "required once"},
        ])
        js = to_json_schema(schema)
        props = js["json_schema"]["schema"]["properties"]
        assert props["color"]["type"] == "string"
        assert "color" in js["json_schema"]["schema"]["required"]

    def test_number_field(self):
        schema = _make_schema([
            {"label_name": "amount", "data_type": "number", "occurrence": "required once"},
        ])
        js = to_json_schema(schema)
        assert js["json_schema"]["schema"]["properties"]["amount"]["type"] == "number"

    def test_checkbox_field(self):
        schema = _make_schema([
            {"label_name": "agreed", "data_type": "checkbox", "occurrence": "optional once"},
        ])
        js = to_json_schema(schema)
        assert js["json_schema"]["schema"]["properties"]["agreed"]["type"] == "boolean"
        assert "agreed" not in js["json_schema"]["schema"]["required"]

    def test_multiple_occurrence_wraps_array(self):
        schema = _make_schema([
            {"label_name": "items", "data_type": "plain text", "occurrence": "required multiple"},
        ])
        js = to_json_schema(schema)
        prop = js["json_schema"]["schema"]["properties"]["items"]
        assert prop["type"] == "array"
        assert prop["items"]["type"] == "string"

    def test_optional_field_not_in_required(self):
        schema = _make_schema([
            {"label_name": "opt", "data_type": "plain text", "occurrence": "optional once"},
        ])
        js = to_json_schema(schema)
        assert "opt" not in js["json_schema"]["schema"]["required"]

    def test_prompt_becomes_description(self):
        schema = _make_schema([
            {
                "label_name": "color",
                "data_type": "plain text",
                "occurrence": "required once",
                "prompt_for_label": "Vehicle color",
            },
        ])
        js = to_json_schema(schema)
        assert js["json_schema"]["schema"]["properties"]["color"]["description"] == "Vehicle color"


class TestToGeminiSchema:
    def test_basic_structure(self):
        schema = _make_schema([
            {"label_name": "name", "data_type": "plain text", "occurrence": "required once"},
        ])
        gs = to_gemini_schema(schema)
        assert gs["type"] == "OBJECT"
        assert "name" in gs["properties"]
        assert "name" in gs["required"]

    def test_optional_not_required(self):
        schema = _make_schema([
            {"label_name": "opt", "data_type": "plain text", "occurrence": "optional once"},
        ])
        gs = to_gemini_schema(schema)
        assert "opt" not in gs["required"]


class TestToExtractionPrompt:
    def test_contains_field_names(self):
        schema = _make_schema([
            {"label_name": "color", "data_type": "plain text", "occurrence": "required once"},
            {"label_name": "model", "data_type": "plain text", "occurrence": "optional once"},
        ])
        prompt = to_extraction_prompt(schema)
        assert "color" in prompt
        assert "model" in prompt
        assert "plain text" in prompt

    def test_contains_prompt_for_label(self):
        schema = _make_schema([
            {
                "label_name": "color",
                "data_type": "plain text",
                "occurrence": "required once",
                "prompt_for_label": "Exterior paint color",
            },
        ])
        prompt = to_extraction_prompt(schema)
        assert "Exterior paint color" in prompt


class TestNormalizeOutput:
    def test_basic_normalization(self):
        schema = _make_schema([
            {"label_name": "color", "data_type": "plain text", "occurrence": "required once"},
            {"label_name": "year", "data_type": "number", "occurrence": "required once"},
        ])
        raw = {"color": "White", "year": 2024}
        results = normalize_output(raw, schema)
        assert len(results) == 2
        assert results[0].value == "White"
        assert results[1].value == "2024"  # Coerced to string

    def test_missing_field_becomes_none(self):
        schema = _make_schema([
            {"label_name": "color", "data_type": "plain text", "occurrence": "required once"},
        ])
        raw = {}
        results = normalize_output(raw, schema)
        assert results[0].value is None

    def test_multiple_occurrence_coerced_to_list(self):
        schema = _make_schema([
            {"label_name": "items", "data_type": "plain text", "occurrence": "required multiple"},
        ])
        raw = {"items": "single_value"}
        results = normalize_output(raw, schema)
        assert results[0].value == ["single_value"]

    def test_single_occurrence_takes_first_from_list(self):
        schema = _make_schema([
            {"label_name": "name", "data_type": "plain text", "occurrence": "required once"},
        ])
        raw = {"name": ["Alice", "Bob"]}
        results = normalize_output(raw, schema)
        assert results[0].value == "Alice"

    def test_boolean_coerced_to_string(self):
        schema = _make_schema([
            {"label_name": "agreed", "data_type": "checkbox", "occurrence": "required once"},
        ])
        raw = {"agreed": True}
        results = normalize_output(raw, schema)
        assert results[0].value == "True"

    def test_list_values_coerced_to_strings(self):
        schema = _make_schema([
            {"label_name": "nums", "data_type": "number", "occurrence": "required multiple"},
        ])
        raw = {"nums": [1, 2, 3]}
        results = normalize_output(raw, schema)
        assert results[0].value == ["1", "2", "3"]
