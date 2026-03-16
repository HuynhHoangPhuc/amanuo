"""Extract step — wraps router-service provider to run structured OCR extraction."""

import importlib
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_iface = importlib.import_module("src.engine.step-interface")
PipelineStep = _iface.PipelineStep
StepContext = _iface.StepContext


class ExtractStep(PipelineStep):
    """Run extraction via the router-service provider pipeline.

    Reads mode and cloud_provider from config (or falls back to context values),
    deserializes schema_fields JSON into an ExtractionSchema, calls provider.extract(),
    and populates context.result, context.confidence, and cost fields.

    Config options:
        mode (str): "auto" | "cloud" | "local_only". Default "auto".
        cloud_provider (str): "gemini" | "mistral". Default "gemini".
    """

    def __init__(self, step_id: str, config: dict[str, Any] | None = None):
        super().__init__(step_id, config)

    @property
    def step_type(self) -> str:
        return "extract"

    @property
    def input_type(self) -> str:
        return "image"

    @property
    def output_type(self) -> str:
        return "extraction_result"

    async def execute(self, context: StepContext) -> StepContext:
        """Run extraction and populate context with results."""
        if context.image is None:
            logger.error("extract: no image in context")
            context.metadata["abort"] = True
            context.metadata["abort_reason"] = "No image provided"
            return context

        if not context.schema_fields:
            logger.error("extract: no schema_fields in context")
            context.metadata["abort"] = True
            context.metadata["abort_reason"] = "No schema fields provided"
            return context

        # Config values override context defaults
        mode = self.config.get("mode", context.mode)
        cloud_provider = self.config.get("cloud_provider", context.cloud_provider)

        # Deserialize schema from JSON string
        schema = _parse_schema(context.schema_fields)

        # Get provider from router-service
        _router = importlib.import_module("src.services.router-service")
        provider = _router.route(mode, cloud_provider)

        logger.debug(
            "extract: using provider=%s mode=%s",
            getattr(provider, "provider_name", lambda: "unknown")(),
            mode,
        )

        # Run extraction
        result = await provider.extract(context.image, schema)

        # Populate context from PipelineResult
        context.result = [r.model_dump() for r in result.normalized]
        context.confidence = result.confidence
        context.cost_input_tokens = result.cost.input_tokens
        context.cost_output_tokens = result.cost.output_tokens
        context.cost_estimated_usd = result.cost.estimated_cost_usd
        context.raw_response = getattr(result, "raw_response", None)

        logger.debug(
            "extract: got %d fields, confidence=%.3f",
            len(context.result),
            context.confidence or 0.0,
        )

        return context


def _parse_schema(schema_fields_json: str):
    """Deserialize JSON schema_fields string into an ExtractionSchema instance."""
    _schema_models = importlib.import_module("src.schemas.schema-models")
    ExtractionSchema = _schema_models.ExtractionSchema
    SchemaField = _schema_models.SchemaField

    raw = json.loads(schema_fields_json)

    # Support both list-of-dicts (schema fields) and full schema dict
    if isinstance(raw, list):
        fields = [SchemaField(**f) if isinstance(f, dict) else f for f in raw]
        return ExtractionSchema(fields=fields)
    elif isinstance(raw, dict):
        return ExtractionSchema(**raw)
    else:
        raise ValueError(f"Unexpected schema_fields format: {type(raw)}")
