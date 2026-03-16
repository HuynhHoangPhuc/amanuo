"""Build CSV-in-prompt format for token-efficient extraction prompts."""

import importlib

_models = importlib.import_module("src.schemas.schema-models")
ExtractionSchema = _models.ExtractionSchema


def to_csv_prompt(schema: ExtractionSchema) -> str:
    """Convert schema to CSV-in-prompt format (~33% fewer tokens than JSON)."""
    lines = [
        "Extract fields from this document image using the schema below.",
        "Return ONLY valid JSON with the extracted values.\n",
        "Schema (CSV: label_name;data_type;occurrence;prompt):",
    ]

    for field in schema.fields:
        prompt = field.prompt_for_label or ""
        lines.append(
            f"{field.label_name};{field.data_type};{field.occurrence};{prompt}"
        )

    lines.append("\nOutput format: JSON object where keys are label_name values.")
    lines.append("Rules:")
    lines.append("- Extract exact values as they appear")
    lines.append("- null for missing fields")
    lines.append("- Arrays for 'multiple' occurrence fields")

    return "\n".join(lines)
