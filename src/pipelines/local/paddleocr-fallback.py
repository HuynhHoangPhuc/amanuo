"""PaddleOCR two-stage fallback: OCR text extraction -> local LLM field extraction."""

import importlib
import json
import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def _get_paddleocr():
    """Lazy-import PaddleOCR to avoid import errors when not installed."""
    try:
        from paddleocr import PaddleOCR
        return PaddleOCR
    except ImportError:
        return None


async def extract_text_with_paddleocr(image: bytes, lang: str = "en") -> str:
    """Stage 1: Extract raw text from image using PaddleOCR.

    Args:
        image: Raw image bytes
        lang: Language code (en, japan, vi)

    Returns:
        Extracted text concatenated from all detected regions.
    """
    PaddleOCR = _get_paddleocr()
    if PaddleOCR is None:
        raise ImportError("PaddleOCR not installed. Install with: pip install paddleocr paddlepaddle")

    # PaddleOCR needs a file path, write temp file
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(image)
        temp_path = f.name

    try:
        # Map language codes
        lang_map = {"en": "en", "jp": "japan", "ja": "japan", "vn": "vi", "vi": "vi"}
        paddle_lang = lang_map.get(lang, "en")

        ocr = PaddleOCR(use_angle_cls=True, lang=paddle_lang, show_log=False)
        result = ocr.ocr(temp_path, cls=True)

        if not result or not result[0]:
            return ""

        # Concatenate all detected text regions
        lines = []
        for line in result[0]:
            if line and len(line) >= 2:
                text = line[1][0]  # (text, confidence)
                lines.append(text)

        return "\n".join(lines)
    finally:
        Path(temp_path).unlink(missing_ok=True)


async def paddleocr_extract(
    image: bytes,
    schema,
    vlm_backend,
    lang: str = "en",
) -> dict:
    """Two-stage extraction: PaddleOCR -> local LLM.

    Args:
        image: Raw image bytes
        schema: ExtractionSchema
        vlm_backend: Any backend with generate_text() method
        lang: Language code

    Returns:
        Parsed JSON dict of extracted fields.
    """
    _prompt_builder = importlib.import_module("src.pipelines.local.vlm-prompt-builder")

    # Stage 1: OCR
    ocr_text = await extract_text_with_paddleocr(image, lang)
    if not ocr_text.strip():
        logger.warning("PaddleOCR returned empty text")
        return {}

    # Stage 2: Extract fields using local LLM
    prompt = _prompt_builder.build_text_extraction_prompt(ocr_text, schema)

    response = await vlm_backend.generate_text(prompt, json_schema=None)

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        # Try to find JSON in the response
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(response[start:end])
        logger.error("Failed to parse LLM response as JSON: %s", response[:200])
        return {}
