"""Pydantic request/response models for the pipelines API, plus SQLAlchemy ORM model."""

from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel

from src.models.base import Base, TimestampMixin


# --- SQLAlchemy ORM Model ---

class PipelineORM(Base, TimestampMixin):
    __tablename__ = "pipelines"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    config: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


# --- Pydantic Models ---

class PipelineCreateRequest(BaseModel):
    """Request body for creating a new pipeline."""

    name: str
    description: str | None = None
    config: str  # YAML string


class PipelineUpdateRequest(BaseModel):
    """Request body for updating an existing pipeline."""

    name: str | None = None
    description: str | None = None
    config: str | None = None  # YAML string


class PipelineResponse(BaseModel):
    """Pipeline record returned by the API."""

    id: str
    workspace_id: str
    name: str
    description: str | None
    config: str
    is_active: bool
    created_at: str
    updated_at: str
