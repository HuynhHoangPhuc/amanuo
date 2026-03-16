"""Export step — normalize extraction result into clean JSON-serializable output."""

import importlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

_iface = importlib.import_module("src.engine.step-interface")
PipelineStep = _iface.PipelineStep
StepContext = _iface.StepContext


class ExportStep(PipelineStep):
    """Format extraction results as a clean JSON-serializable list of dicts.

    Config options:
        format (str): Output format identifier. Currently only "json" is supported.
                      Default "json".
    """

    def __init__(self, step_id: str, config: dict[str, Any] | None = None):
        super().__init__(step_id, config)
        self._format: str = str(self.config.get("format", "json")).lower()

    @property
    def step_type(self) -> str:
        return "export"

    @property
    def input_type(self) -> str:
        return "extraction_result"

    @property
    def output_type(self) -> str:
        return "formatted_output"

    async def execute(self, context: StepContext) -> StepContext:
        """Normalize result to a list of plain dicts with only JSON-safe values."""
        if context.result is None:
            logger.debug("export: no result in context, returning empty list")
            context.result = []
            return context

        normalized: list[dict] = []
        for item in context.result:
            if isinstance(item, dict):
                normalized.append(_sanitize_dict(item))
            else:
                # Handle Pydantic model instances (ExtractionResult) gracefully
                try:
                    normalized.append(_sanitize_dict(item.model_dump()))
                except AttributeError:
                    normalized.append(_sanitize_dict(vars(item)))

        context.result = normalized
        logger.debug("export: normalized %d result fields", len(normalized))
        return context


def _sanitize_dict(d: dict) -> dict:
    """Recursively ensure all dict values are JSON-serializable primitives."""
    clean: dict[str, Any] = {}
    for key, value in d.items():
        if isinstance(value, dict):
            clean[key] = _sanitize_dict(value)
        elif isinstance(value, list):
            clean[key] = [
                _sanitize_dict(v) if isinstance(v, dict) else _coerce(v)
                for v in value
            ]
        else:
            clean[key] = _coerce(value)
    return clean


def _coerce(value: Any) -> Any:
    """Coerce a value to a JSON-safe type (str/int/float/bool/None)."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)
