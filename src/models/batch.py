"""Pydantic models for batch processing API."""

from pydantic import BaseModel


class BatchCreateRequest(BaseModel):
    schema_fields: str | None = None
    schema_id: str | None = None
    pipeline_id: str | None = None
    mode: str = "auto"
    cloud_provider: str = "gemini"


class BatchItemResponse(BaseModel):
    id: str
    job_id: str
    filename: str | None
    status: str
    item_index: int


class BatchResponse(BaseModel):
    id: str
    status: str  # pending, processing, completed, failed, partial
    total_items: int
    completed_items: int
    failed_items: int
    progress_pct: float
    pipeline_id: str | None = None
    created_at: str
    completed_at: str | None = None
    items: list[BatchItemResponse] | None = None


class BatchListResponse(BaseModel):
    batches: list[BatchResponse]
    total: int
