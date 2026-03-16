"""Convert extraction schemas to provider-specific formats and normalize output."""

import importlib

_models = importlib.import_module("src.schemas.schema-models")
DataType = _models.DataType
ExtractionResult = _models.ExtractionResult
ExtractionSchema = _models.ExtractionSchema
SchemaField = _models.SchemaField

# Mapping from user data_type to JSON Schema type
_TYPE_MAP: dict[str, dict] = {
    "plain text": {"type": "string"},
    "number": {"type": "number"},
    "address": {"type": "string", "description": "Address value"},
    "datetime": {"type": "string", "description": "ISO 8601 datetime"},
    "currency": {"type": "string", "description": "Currency amount with symbol"},
    "checkbox": {"type": "boolean"},
}


def _field_to_json_schema(field: SchemaField) -> dict:
    """Convert a single field to JSON Schema property definition."""
    base = dict(_TYPE_MAP.get(field.data_type, {"type": "string"}))

    if field.prompt_for_label:
        base["description"] = field.prompt_for_label

    # Handle "multiple" occurrence -> wrap in array
    if "multiple" in field.occurrence:
        return {"type": "array", "items": base}

    return base


def to_json_schema(schema: ExtractionSchema) -> dict:
    """Convert to JSON Schema for Qwen3-VL response_format."""
    properties = {}
    required = []

    for field in schema.fields:
        properties[field.label_name] = _field_to_json_schema(field)
        if "required" in field.occurrence:
            required.append(field.label_name)

    return {
        "type": "json_schema",
        "json_schema": {
            "strict": True,
            "schema": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        },
    }


def to_gemini_schema(schema: ExtractionSchema) -> dict:
    """Convert to Gemini response_schema format."""
    properties = {}
    required = []

    for field in schema.fields:
        prop = _field_to_json_schema(field)
        properties[field.label_name] = prop
        if "required" in field.occurrence:
            required.append(field.label_name)

    return {
        "type": "OBJECT",
        "properties": properties,
        "required": required,
    }


def to_extraction_prompt(schema: ExtractionSchema) -> str:
    """Build extraction prompt text from schema (used for all providers)."""
    lines = ["Extract the following fields from this document image."]
    lines.append("Return ONLY valid JSON matching the schema below.\n")
    lines.append("Fields:")

    for field in schema.fields:
        desc = f"  - {field.label_name} ({field.data_type}, {field.occurrence})"
        if field.prompt_for_label:
            desc += f": {field.prompt_for_label}"
        lines.append(desc)

    lines.append("\nRules:")
    lines.append("- Extract exact values as they appear in the document")
    lines.append("- Set null for fields not found in the document")
    lines.append('- For "multiple" occurrence fields, return arrays')

    return "\n".join(lines)


def normalize_output(
    raw: dict, schema: ExtractionSchema
) -> list[ExtractionResult]:
    """Normalize provider output back to unified [{label_name, data_type, value}] format."""
    results = []

    for field in schema.fields:
        value = raw.get(field.label_name)

        # Coerce to expected type
        if value is not None:
            if "multiple" in field.occurrence and not isinstance(value, list):
                value = [str(value)]
            elif "multiple" not in field.occurrence and isinstance(value, list):
                value = value[0] if value else None

            # Convert non-string single values to string (except None)
            if value is not None and not isinstance(value, list):
                value = str(value)
            elif isinstance(value, list):
                value = [str(v) for v in value]

        results.append(
            ExtractionResult(
                label_name=field.label_name,
                data_type=field.data_type,
                value=value,
            )
        )

    return results
