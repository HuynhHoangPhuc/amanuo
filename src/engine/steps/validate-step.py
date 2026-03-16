"""Validate step — confidence threshold check and required-field presence validation."""

import importlib
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_iface = importlib.import_module("src.engine.step-interface")
PipelineStep = _iface.PipelineStep
StepContext = _iface.StepContext


class ValidateStep(PipelineStep):
    """Validate extraction results against schema rules and confidence threshold.

    Config options:
        min_confidence (float): Minimum acceptable overall confidence. Default 0.0.
        require_all_required (bool): Abort if required fields are missing. Default True.
    """

    def __init__(self, step_id: str, config: dict[str, Any] | None = None):
        super().__init__(step_id, config)
        self._min_confidence: float = float(self.config.get("min_confidence", 0.0))
        self._require_all_required: bool = bool(
            self.config.get("require_all_required", True)
        )

    @property
    def step_type(self) -> str:
        return "validate"

    @property
    def input_type(self) -> str:
        return "extraction_result"

    @property
    def output_type(self) -> str:
        return "extraction_result"

    async def execute(self, context: StepContext) -> StepContext:
        """Check confidence and required field presence. Sets abort flag on critical failure."""
        if context.result is None:
            logger.warning("validate: no result in context, skipping")
            return context

        warnings: list[str] = []

        # Check overall confidence threshold
        confidence = context.confidence or 0.0
        if self._min_confidence > 0.0 and confidence < self._min_confidence:
            msg = (
                f"Confidence {confidence:.3f} below minimum {self._min_confidence:.3f}"
            )
            logger.warning("validate: %s", msg)
            warnings.append(msg)
            context.metadata["abort"] = True
            context.metadata["abort_reason"] = msg

        # Check required fields have non-null values
        if self._require_all_required and context.schema_fields:
            missing = _find_missing_required(context.schema_fields, context.result)
            if missing:
                msg = f"Required fields missing values: {', '.join(missing)}"
                logger.warning("validate: %s", msg)
                warnings.append(msg)
                # Only abort if confidence threshold hasn't already aborted
                if not context.metadata.get("abort"):
                    context.metadata["validation_warnings"] = warnings

        if warnings:
            context.metadata.setdefault("validation_warnings", warnings)

        return context


def _find_missing_required(schema_fields_json: str, result: list[dict]) -> list[str]:
    """Return label names of required fields that have null/empty values in result."""
    try:
        raw = json.loads(schema_fields_json)
        fields = raw if isinstance(raw, list) else raw.get("fields", [])
    except (json.JSONDecodeError, AttributeError):
        return []

    # Build result lookup: label_name -> value
    result_map = {r.get("label_name"): r.get("value") for r in result}

    missing: list[str] = []
    for field in fields:
        occurrence = field.get("occurrence", "required once")
        if "required" in occurrence:
            label = field.get("label_name", "")
            value = result_map.get(label)
            # Missing if not present at all, None, or empty string/list
            if value is None or value == "" or value == []:
                missing.append(label)

    return missing
