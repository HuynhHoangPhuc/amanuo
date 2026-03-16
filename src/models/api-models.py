"""API request/response Pydantic models."""

from typing import Literal

from pydantic import BaseModel

from src.schemas import ExtractionResult, SchemaField


class ExtractionRequest(BaseModel):
    """Request body for POST /extract (sent as form field alongside file upload)."""

    mode: Literal["local_only", "cloud", "auto"] = "auto"
    schema_fields: list[SchemaField] | None = None
    schema_id: str | None = None
    cloud_provider: Literal["gemini", "mistral"] = "gemini"
    lang: str = "en"


class CostResponse(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0


class JobResponse(BaseModel):
    id: str
    status: Literal["pending", "processing", "completed", "failed"]
    mode: str
    cloud_provider: str | None = None
    created_at: str
    completed_at: str | None = None
    result: list[ExtractionResult] | None = None
    confidence: float | None = None
    cost: CostResponse | None = None
    error: str | None = None


class JobListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int


class SchemaCreateRequest(BaseModel):
    name: str
    fields: list[SchemaField]


class SchemaResponse(BaseModel):
    id: str
    name: str
    fields: list[SchemaField]
    version: str = "1.0.0"
    created_at: str
    updated_at: str


class SuggestedField(BaseModel):
    label: str
    type: str  # text, number, date, boolean
    occurrence: str
    confidence: float


class SuggestSchemaResponse(BaseModel):
    fields: list[SuggestedField]
    warning: str
    beta: bool = True


class SchemaTemplateResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    fields: list[dict]
    languages: list[str]
    is_curated: bool
    usage_count: int
    version: str
    created_at: str
