"""Schema field suggestion service — uses VLM to analyze documents and suggest extraction fields."""

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

META_PROMPT = """You are an AI assistant helping extract structured data from documents.
Analyze this document image and suggest extraction fields for structured data extraction.

For each field you identify, provide:
- label: snake_case field name (e.g., "invoice_number", "total_amount")
- type: one of "text", "number", "date", "boolean"
- occurrence: one of "required once", "optional once", "optional multiple"
- confidence: 0.0-1.0 (how confident the field clearly exists in this document)

Return ONLY a JSON array. Example:
[{"label": "invoice_number", "type": "text", "occurrence": "required once", "confidence": 0.95}]

Only suggest fields clearly visible in the document. Do not invent fields."""

VALID_TYPES = {"text", "number", "date", "boolean"}
VALID_OCCURRENCES = {"required once", "optional once", "optional multiple"}


async def suggest_schema_fields(image_bytes: bytes, lang: str = "en") -> list[dict]:
    """Analyze document image and return suggested schema fields.

    Returns list of dicts with: label, type, occurrence, confidence.
    Sorted by confidence descending. Returns empty list if VLM unavailable.
    """
    try:
        raw_response = await _call_vlm(image_bytes, lang)
        fields = _parse_fields(raw_response)
        return sorted(fields, key=lambda f: f.get("confidence", 0), reverse=True)
    except RuntimeError as e:
        logger.info(f"VLM unavailable for schema suggestion: {e}")
        return []
    except Exception as e:
        logger.error(f"Schema suggestion failed: {e}")
        return []


async def _call_vlm(image_bytes: bytes, lang: str) -> str:
    """Call local VLM (Ollama) with meta-prompt to get field suggestions."""
    import importlib

    _ollama_mod = importlib.import_module("src.pipelines.local.ollama-backend")
    OllamaBackend = _ollama_mod.OllamaBackend

    backend = OllamaBackend()

    # Check availability before attempting inference
    available = await backend.is_available()
    if not available:
        raise RuntimeError("Ollama VLM is not available")

    prompt = META_PROMPT
    if lang and lang != "en":
        prompt += f"\n\nNote: The document may be in language code '{lang}'."

    response = await backend.generate(image_bytes, prompt)
    return response


def _parse_fields(raw_response: str) -> list[dict]:
    """Parse VLM JSON response into validated field list."""
    # Try direct JSON parse of stripped response
    stripped = raw_response.strip()
    try:
        data = json.loads(stripped)
        if isinstance(data, list):
            return [f for f in (_validate_field(item) for item in data) if f]
    except json.JSONDecodeError:
        pass

    # Try regex extraction of JSON array
    json_match = re.search(r'\[.*?\]', stripped, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group())
            if isinstance(data, list):
                return [f for f in (_validate_field(item) for item in data) if f]
        except json.JSONDecodeError:
            pass

    logger.warning(f"Could not parse VLM response for schema suggestion: {stripped[:200]}")
    return []


def _validate_field(field: Any) -> dict | None:
    """Validate and normalize a suggested field dict. Returns None if invalid."""
    if not isinstance(field, dict):
        return None

    # Normalize label to snake_case
    label = str(field.get("label", "")).strip().lower().replace(" ", "_")
    if not label:
        return None

    field_type = field.get("type", "text")
    if field_type not in VALID_TYPES:
        field_type = "text"

    occurrence = field.get("occurrence", "optional once")
    if occurrence not in VALID_OCCURRENCES:
        occurrence = "optional once"

    confidence = float(field.get("confidence", 0.5))
    confidence = max(0.0, min(1.0, confidence))

    return {
        "label": label,
        "type": field_type,
        "occurrence": occurrence,
        "confidence": confidence,
    }
