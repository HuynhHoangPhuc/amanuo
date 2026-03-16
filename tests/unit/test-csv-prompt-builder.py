"""Unit tests for CSV prompt builder."""

from src.schemas import ExtractionSchema, SchemaField, to_csv_prompt


def _make_schema(fields_data: list[dict]) -> ExtractionSchema:
    return ExtractionSchema(fields=[SchemaField(**f) for f in fields_data])


class TestToCsvPrompt:
    def test_basic_csv_output(self):
        schema = _make_schema([
            {"label_name": "color", "data_type": "plain text", "occurrence": "required once", "prompt_for_label": "Vehicle color"},
        ])
        csv = to_csv_prompt(schema)
        assert "color;plain text;required once;Vehicle color" in csv

    def test_no_prompt_empty_field(self):
        schema = _make_schema([
            {"label_name": "name", "data_type": "plain text", "occurrence": "required once"},
        ])
        csv = to_csv_prompt(schema)
        assert "name;plain text;required once;" in csv

    def test_multiple_fields(self):
        schema = _make_schema([
            {"label_name": "a", "data_type": "plain text", "occurrence": "required once"},
            {"label_name": "b", "data_type": "number", "occurrence": "optional once"},
        ])
        csv = to_csv_prompt(schema)
        assert "a;plain text;required once;" in csv
        assert "b;number;optional once;" in csv

    def test_contains_extraction_instructions(self):
        schema = _make_schema([
            {"label_name": "x", "data_type": "plain text", "occurrence": "required once"},
        ])
        csv = to_csv_prompt(schema)
        assert "Extract" in csv
        assert "JSON" in csv

    def test_csv_shorter_than_json_prompt(self):
        """CSV format should use fewer characters than JSON extraction prompt."""
        from src.schemas import to_extraction_prompt
        schema = _make_schema([
            {"label_name": f"field_{i}", "data_type": "plain text", "occurrence": "required once", "prompt_for_label": f"Description {i}"}
            for i in range(10)
        ])
        csv = to_csv_prompt(schema)
        json_prompt = to_extraction_prompt(schema)
        # CSV should be shorter (fewer tokens)
        assert len(csv) < len(json_prompt)
