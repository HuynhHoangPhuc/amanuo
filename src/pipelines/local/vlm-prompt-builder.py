"""Build extraction prompts for local VLM backends."""

from src.schemas import ExtractionSchema, to_csv_prompt


def build_vlm_extraction_prompt(schema: ExtractionSchema, use_csv: bool = True) -> str:
    """Build prompt for VLM image extraction."""
    if use_csv:
        return to_csv_prompt(schema)

    # JSON-based prompt (more tokens but clearer for some models)
    from src.schemas import to_extraction_prompt
    return to_extraction_prompt(schema)


def build_text_extraction_prompt(ocr_text: str, schema: ExtractionSchema) -> str:
    """Build prompt for text-only extraction (PaddleOCR Stage 2)."""
    csv = to_csv_prompt(schema)
    return (
        f"Given the following OCR-extracted text from a document, "
        f"extract the requested fields.\n\n"
        f"OCR Text:\n{ocr_text}\n\n"
        f"{csv}"
    )
