"""Job model for OCR extraction tracking."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Job(BaseModel):
    id: str
    status: Literal["pending", "processing", "completed", "failed"] = "pending"
    mode: Literal["local_only", "cloud", "auto"]
    cloud_provider: str | None = None
    schema_fields: str | None = None  # JSON-serialized schema
    schema_id: str | None = None
    input_file: str | None = None
    result: str | None = None  # JSON-serialized extraction result
    confidence: float | None = None
    cost_input_tokens: int | None = None
    cost_output_tokens: int | None = None
    cost_estimated_usd: float | None = None
    error: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str | None = None
