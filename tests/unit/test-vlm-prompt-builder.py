"""Unit tests for VLM prompt builder — hints injection into extraction prompts."""

import importlib
import pytest

_vlm = importlib.import_module("src.pipelines.local.vlm-prompt-builder")
build_vlm_extraction_prompt = _vlm.build_vlm_extraction_prompt
build_text_extraction_prompt = _vlm.build_text_extraction_prompt


class TestBuildVLMExtractionPrompt:
    """Test VLM extraction prompt building with hints."""

    @pytest.mark.unit
    def test_build_vlm_prompt_without_hints(self):
        """Building VLM prompt without hints excludes hint section."""
        from src.schemas import ExtractionSchema, SchemaField

        schema = ExtractionSchema(
            name="test_schema",
            fields=[
                SchemaField(label_name="invoice_number", data_type="plain text"),
                SchemaField(label_name="amount", data_type="currency"),
            ],
        )

        prompt = build_vlm_extraction_prompt(schema, use_csv=True, hints="")
        assert "Hints from previous corrections" not in prompt

    @pytest.mark.unit
    def test_build_vlm_prompt_with_hints(self):
        """Building VLM prompt with hints includes hint section."""
        from src.schemas import ExtractionSchema, SchemaField

        schema = ExtractionSchema(
            name="test_schema",
            fields=[
                SchemaField(label_name="invoice_number", data_type="plain text"),
            ],
        )

        hints = "For field 'invoice_number': Common correction: INV-001 -> INV-0001"
        prompt = build_vlm_extraction_prompt(schema, use_csv=True, hints=hints)

        assert "Hints from previous corrections" in prompt
        assert "INV-001 -> INV-0001" in prompt

    @pytest.mark.unit
    def test_build_vlm_prompt_csv_format(self):
        """Building VLM prompt uses CSV format when specified."""
        from src.schemas import ExtractionSchema, SchemaField

        schema = ExtractionSchema(
            name="test_schema",
            fields=[
                SchemaField(label_name="field1", data_type="plain text"),
                SchemaField(label_name="field2", data_type="plain text"),
            ],
        )

        prompt = build_vlm_extraction_prompt(schema, use_csv=True)
        # CSV format should have field names in structured format
        assert "field1" in prompt
        assert "field2" in prompt

    @pytest.mark.unit
    def test_build_vlm_prompt_non_csv_format(self):
        """Building VLM prompt uses extraction format when specified."""
        from src.schemas import ExtractionSchema, SchemaField

        schema = ExtractionSchema(
            name="test_schema",
            fields=[
                SchemaField(label_name="field1", data_type="plain text"),
            ],
        )

        prompt = build_vlm_extraction_prompt(schema, use_csv=False)
        assert "field1" in prompt

    @pytest.mark.unit
    def test_build_vlm_prompt_hints_format(self):
        """Building VLM prompt formats hints correctly."""
        from src.schemas import ExtractionSchema, SchemaField

        schema = ExtractionSchema(
            name="test_schema",
            fields=[SchemaField(label_name="test", data_type="plain text")],
        )

        hints = "For field 'name':\n  - Common correction: John -> Johnny\n  - Common correction: Jane -> Janet"
        prompt = build_vlm_extraction_prompt(schema, use_csv=True, hints=hints)

        assert "Hints from previous corrections:" in prompt
        assert "John -> Johnny" in prompt
        assert "Janet" in prompt

    @pytest.mark.unit
    def test_build_vlm_prompt_multiline_hints(self):
        """Building VLM prompt preserves multiline hints."""
        from src.schemas import ExtractionSchema, SchemaField

        schema = ExtractionSchema(
            name="test_schema",
            fields=[SchemaField(label_name="field", data_type="plain text")],
        )

        multiline_hints = """For field 'amount':
  - Common correction: $100 -> 100.00 (5x)
  - Common correction: $50 -> 50.00 (3x)

For field 'date':
  - Common correction: 01/15/2024 -> 2024-01-15 (8x)"""

        prompt = build_vlm_extraction_prompt(schema, use_csv=True, hints=multiline_hints)

        assert "amount" in prompt
        assert "100.00" in prompt
        assert "date" in prompt
        assert "2024-01-15" in prompt

    @pytest.mark.unit
    def test_build_vlm_prompt_empty_hints_ignored(self):
        """Building VLM prompt ignores empty hints string."""
        from src.schemas import ExtractionSchema, SchemaField

        schema = ExtractionSchema(
            name="test_schema",
            fields=[SchemaField(label_name="field", data_type="plain text")],
        )

        prompt_without = build_vlm_extraction_prompt(schema, use_csv=True, hints="")
        prompt_with_empty = build_vlm_extraction_prompt(schema, use_csv=True, hints="")

        assert prompt_without == prompt_with_empty

    @pytest.mark.unit
    def test_build_vlm_prompt_includes_schema(self):
        """Building VLM prompt includes field definitions."""
        from src.schemas import ExtractionSchema, SchemaField

        schema = ExtractionSchema(
            name="invoice_schema",
            fields=[
                SchemaField(label_name="invoice_number", data_type="plain text"),
                SchemaField(label_name="total_amount", data_type="currency"),
            ],
        )

        prompt = build_vlm_extraction_prompt(schema, use_csv=True)

        assert "invoice_number" in prompt
        assert "total_amount" in prompt


class TestBuildTextExtractionPrompt:
    """Test text extraction prompt building with hints."""

    @pytest.mark.unit
    def test_build_text_prompt_without_hints(self):
        """Building text prompt without hints excludes hint section."""
        from src.schemas import ExtractionSchema, SchemaField

        schema = ExtractionSchema(
            name="test_schema",
            fields=[SchemaField(label_name="field1", data_type="plain text")],
        )

        ocr_text = "Sample OCR text from document"
        prompt = build_text_extraction_prompt(ocr_text, schema, hints="")

        assert "Sample OCR text from document" in prompt
        assert "Hints from previous corrections" not in prompt

    @pytest.mark.unit
    def test_build_text_prompt_with_hints(self):
        """Building text prompt with hints includes hint section."""
        from src.schemas import ExtractionSchema, SchemaField

        schema = ExtractionSchema(
            name="test_schema",
            fields=[SchemaField(label_name="amount", data_type="currency")],
        )

        ocr_text = "Amount: $500"
        hints = "For field 'amount': Common correction: $500 -> 500.00"
        prompt = build_text_extraction_prompt(ocr_text, schema, hints=hints)

        assert "Hints from previous corrections" in prompt
        assert "500.00" in prompt

    @pytest.mark.unit
    def test_build_text_prompt_includes_ocr_text(self):
        """Building text prompt includes OCR text."""
        from src.schemas import ExtractionSchema, SchemaField

        schema = ExtractionSchema(
            name="test_schema",
            fields=[SchemaField(label_name="name", data_type="plain text")],
        )

        ocr_text = """Invoice #12345
        Customer: John Doe
        Amount: $1000.00"""

        prompt = build_text_extraction_prompt(ocr_text, schema)

        assert "Invoice #12345" in prompt
        assert "John Doe" in prompt
        assert "1000.00" in prompt

    @pytest.mark.unit
    def test_build_text_prompt_ocr_section_labeled(self):
        """Building text prompt labels OCR section clearly."""
        from src.schemas import ExtractionSchema, SchemaField

        schema = ExtractionSchema(
            name="test_schema",
            fields=[SchemaField(label_name="field", data_type="plain text")],
        )

        ocr_text = "Sample text"
        prompt = build_text_extraction_prompt(ocr_text, schema)

        assert "OCR" in prompt.upper()

    @pytest.mark.unit
    def test_build_text_prompt_includes_extraction_instructions(self):
        """Building text prompt includes extraction instructions."""
        from src.schemas import ExtractionSchema, SchemaField

        schema = ExtractionSchema(
            name="test_schema",
            fields=[SchemaField(label_name="field", data_type="plain text")],
        )

        prompt = build_text_extraction_prompt("text", schema)

        assert "extract" in prompt.lower()

    @pytest.mark.unit
    def test_build_text_prompt_csv_format(self):
        """Building text prompt uses CSV format for fields."""
        from src.schemas import ExtractionSchema, SchemaField

        schema = ExtractionSchema(
            name="test_schema",
            fields=[
                SchemaField(label_name="field1", data_type="plain text"),
                SchemaField(label_name="field2", data_type="plain text"),
            ],
        )

        prompt = build_text_extraction_prompt("ocr text", schema)

        assert "field1" in prompt
        assert "field2" in prompt

    @pytest.mark.unit
    def test_build_text_prompt_hints_append_position(self):
        """Building text prompt appends hints at end."""
        from src.schemas import ExtractionSchema, SchemaField

        schema = ExtractionSchema(
            name="test_schema",
            fields=[SchemaField(label_name="amount", data_type="currency")],
        )

        ocr_text = "Amount: $100"
        hints = "For field 'amount': $100 -> 100.00"
        prompt = build_text_extraction_prompt(ocr_text, schema, hints=hints)

        # Hints should be after OCR text and field definitions
        hint_pos = prompt.find("Hints from previous corrections")
        ocr_pos = prompt.find(ocr_text)
        assert hint_pos > ocr_pos

    @pytest.mark.unit
    def test_build_text_prompt_long_ocr_text(self):
        """Building text prompt handles long OCR text."""
        from src.schemas import ExtractionSchema, SchemaField

        schema = ExtractionSchema(
            name="test_schema",
            fields=[SchemaField(label_name="content", data_type="plain text")],
        )

        # Generate long OCR text
        ocr_text = "Sample line\n" * 100

        prompt = build_text_extraction_prompt(ocr_text, schema)

        assert "Sample line" in prompt
        assert len(prompt) > len(ocr_text)

    @pytest.mark.unit
    def test_build_text_prompt_multiline_ocr(self):
        """Building text prompt preserves multiline OCR text."""
        from src.schemas import ExtractionSchema, SchemaField

        schema = ExtractionSchema(
            name="test_schema",
            fields=[SchemaField(label_name="field", data_type="plain text")],
        )

        ocr_text = """Line 1
Line 2
Line 3"""

        prompt = build_text_extraction_prompt(ocr_text, schema)

        assert "Line 1" in prompt
        assert "Line 2" in prompt
        assert "Line 3" in prompt


class TestHintsInjection:
    """Test hints injection mechanics."""

    @pytest.mark.unit
    def test_vlm_hint_injection_position(self):
        """VLM hints are injected at end of prompt."""
        from src.schemas import ExtractionSchema, SchemaField

        schema = ExtractionSchema(
            name="test_schema",
            fields=[SchemaField(label_name="field", data_type="plain text")],
        )

        base_prompt = build_vlm_extraction_prompt(schema, use_csv=True, hints="")
        hintsed_prompt = build_vlm_extraction_prompt(schema, use_csv=True, hints="Test hint")

        # hintsed_prompt should be longer
        assert len(hintsed_prompt) > len(base_prompt)

        # Base content should still be there
        base_lines = base_prompt.split("\n")
        hintsed_lines = hintsed_prompt.split("\n")

        # Hintsed should have additional lines
        assert len(hintsed_lines) > len(base_lines)

    @pytest.mark.unit
    def test_text_hint_injection_position(self):
        """Text hints are injected at end of prompt."""
        from src.schemas import ExtractionSchema, SchemaField

        schema = ExtractionSchema(
            name="test_schema",
            fields=[SchemaField(label_name="field", data_type="plain text")],
        )

        base_prompt = build_text_extraction_prompt("text", schema, hints="")
        hintsed_prompt = build_text_extraction_prompt("text", schema, hints="Test hint")

        assert len(hintsed_prompt) > len(base_prompt)

    @pytest.mark.unit
    def test_hint_section_header_consistent(self):
        """Hint section header is consistent."""
        from src.schemas import ExtractionSchema, SchemaField

        schema = ExtractionSchema(
            name="test_schema",
            fields=[SchemaField(label_name="field", data_type="plain text")],
        )

        vlm_prompt = build_vlm_extraction_prompt(schema, use_csv=True, hints="hint")
        text_prompt = build_text_extraction_prompt("text", schema, hints="hint")

        assert "Hints from previous corrections:" in vlm_prompt
        assert "Hints from previous corrections:" in text_prompt

    @pytest.mark.unit
    def test_special_characters_in_hints(self):
        """Prompts handle special characters in hints."""
        from src.schemas import ExtractionSchema, SchemaField

        schema = ExtractionSchema(
            name="test_schema",
            fields=[SchemaField(label_name="field", data_type="plain text")],
        )

        hints = """For field 'amount':
  - $100 -> 100.00
  - €50 -> 50.00
  - £25 -> 25.00"""

        prompt = build_vlm_extraction_prompt(schema, use_csv=True, hints=hints)

        assert "$100" in prompt
        assert "€50" in prompt
        assert "£25" in prompt
