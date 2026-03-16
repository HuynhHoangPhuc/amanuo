"""Abstract base provider interface for extraction pipelines."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from src.schemas import ExtractionResult, ExtractionSchema


@dataclass
class CostInfo:
    """Cost tracking for a single extraction request."""

    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0


@dataclass
class PipelineResult:
    """Result from an extraction pipeline."""

    raw_output: dict = field(default_factory=dict)
    normalized: list[ExtractionResult] = field(default_factory=list)
    confidence: float = 0.0
    cost: CostInfo = field(default_factory=CostInfo)
    latency_ms: int = 0
    provider: str = ""


class BaseProvider(ABC):
    """Abstract interface for all extraction providers (cloud and local)."""

    @abstractmethod
    async def extract(
        self, image: bytes, schema: ExtractionSchema, **kwargs
    ) -> PipelineResult:
        """Extract structured data from an image using the given schema."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is available and ready."""
        ...

    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider's identifier name."""
        ...
