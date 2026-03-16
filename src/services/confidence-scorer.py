"""Confidence scoring for extraction results."""

from src.pipelines import PipelineResult
from src.schemas import ExtractionSchema


def score(result: PipelineResult, schema: ExtractionSchema) -> float:
    """Calculate confidence score for an extraction result.

    Combined score: 0.7 * completeness + 0.3 * provider_confidence
    """
    completeness = _schema_completeness(result, schema)
    provider_conf = _provider_confidence(result)

    return round(0.7 * completeness + 0.3 * provider_conf, 3)


def _schema_completeness(result: PipelineResult, schema: ExtractionSchema) -> float:
    """Percentage of required fields with non-null values."""
    required_fields = [f for f in schema.fields if "required" in f.occurrence]
    if not required_fields:
        return 1.0

    filled = 0
    extracted_map = {r.label_name: r.value for r in result.normalized}

    for field in required_fields:
        value = extracted_map.get(field.label_name)
        if value is not None and value != "" and value != []:
            filled += 1

    return filled / len(required_fields)


def _provider_confidence(result: PipelineResult) -> float:
    """Average per-field confidence from provider (if available)."""
    confidences = [r.confidence for r in result.normalized if r.confidence is not None]
    if not confidences:
        return 0.5  # Default when provider doesn't report confidence
    return sum(confidences) / len(confidences)
