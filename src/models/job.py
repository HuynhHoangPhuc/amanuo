"""Job model for OCR extraction tracking — Pydantic + SQLAlchemy ORM."""

from datetime import datetime
from typing import Literal

from sqlalchemy import String, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel, Field

from src.models.base import Base


# --- SQLAlchemy ORM Model ---

class JobORM(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    mode: Mapped[str] = mapped_column(String, nullable=False)
    cloud_provider: Mapped[str | None] = mapped_column(String, nullable=True)
    schema_fields: Mapped[str | None] = mapped_column(String, nullable=True)
    schema_id: Mapped[str | None] = mapped_column(String, nullable=True)
    input_file: Mapped[str | None] = mapped_column(String, nullable=True)
    result: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_estimated_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    error: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    completed_at: Mapped[str | None] = mapped_column(String, nullable=True)
    workspace_id: Mapped[str | None] = mapped_column(String, nullable=True)
    batch_id: Mapped[str | None] = mapped_column(String, nullable=True)
    pipeline_id: Mapped[str | None] = mapped_column(String, nullable=True)


# --- Pydantic Model (kept for backward compatibility) ---

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
