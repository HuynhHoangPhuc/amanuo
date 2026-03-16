"""Abstract interface and shared context dataclass for pipeline steps."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StepContext:
    """Data flowing between pipeline steps."""

    image: bytes | None = None
    schema_fields: str | None = None  # JSON-serialized schema fields
    schema_id: str | None = None
    result: list | None = None  # list of ExtractionResult dicts
    confidence: float | None = None
    cost_input_tokens: int = 0
    cost_output_tokens: int = 0
    cost_estimated_usd: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    workspace_id: str = "default"
    job_id: str = ""
    mode: str = "auto"
    cloud_provider: str = "gemini"
    raw_response: str | None = None


class PipelineStep(ABC):
    """Abstract interface for pipeline steps."""

    def __init__(self, step_id: str, config: dict[str, Any] | None = None):
        self.step_id = step_id
        self.config = config or {}

    @abstractmethod
    async def execute(self, context: StepContext) -> StepContext:
        """Process context and return modified context."""
        ...

    @property
    @abstractmethod
    def step_type(self) -> str:
        """Return the step type identifier string."""
        ...

    @property
    @abstractmethod
    def input_type(self) -> str:
        """Return the expected input type."""
        ...

    @property
    @abstractmethod
    def output_type(self) -> str:
        """Return the produced output type."""
        ...
