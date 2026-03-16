"""Pydantic models for batch processing API, plus SQLAlchemy ORM models."""

from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel

from src.models.base import Base


# --- SQLAlchemy ORM Models ---

class BatchORM(Base):
    __tablename__ = "batches"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    total_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pipeline_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    completed_at: Mapped[str | None] = mapped_column(String, nullable=True)


class BatchItemORM(Base):
    __tablename__ = "batch_items"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    batch_id: Mapped[str] = mapped_column(String, nullable=False)
    job_id: Mapped[str] = mapped_column(String, nullable=False)
    item_index: Mapped[int] = mapped_column(Integer, nullable=False)
    filename: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")


# --- Pydantic Models ---

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
