"""Build extraction prompts for local VLM backends."""

from src.schemas import ExtractionSchema, to_csv_prompt


def build_vlm_extraction_prompt(
    schema: ExtractionSchema, use_csv: bool = True, hints: str = ""
) -> str:
    """Build prompt for VLM image extraction, optionally with correction hints."""
    if use_csv:
        prompt = to_csv_prompt(schema)
    else:
        from src.schemas import to_extraction_prompt
        prompt = to_extraction_prompt(schema)

    if hints:
        prompt += f"\n\nHints from previous corrections:\n{hints}"
    return prompt


def build_text_extraction_prompt(
    ocr_text: str, schema: ExtractionSchema, hints: str = ""
) -> str:
    """Build prompt for text-only extraction (PaddleOCR Stage 2)."""
    csv = to_csv_prompt(schema)
    prompt = (
        f"Given the following OCR-extracted text from a document, "
        f"extract the requested fields.\n\n"
        f"OCR Text:\n{ocr_text}\n\n"
        f"{csv}"
    )
    if hints:
        prompt += f"\n\nHints from previous corrections:\n{hints}"
    return prompt
