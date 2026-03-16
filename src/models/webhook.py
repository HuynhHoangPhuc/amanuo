"""Pydantic request/response models for webhook management, plus SQLAlchemy ORM models."""

from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel

from src.models.base import Base, TimestampMixin

# Supported event types for webhook subscriptions
VALID_EVENTS = {"job.completed", "job.failed", "batch.completed", "batch.failed"}


# --- SQLAlchemy ORM Models ---

class WebhookORM(Base, TimestampMixin):
    __tablename__ = "webhooks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    events: Mapped[str] = mapped_column(String, nullable=False)  # JSON array
    secret: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class WebhookDeliveryORM(Base):
    __tablename__ = "webhook_deliveries"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    webhook_id: Mapped[str] = mapped_column(String, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[str] = mapped_column(String, nullable=False)  # JSON
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(String, nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    delivered_at: Mapped[str | None] = mapped_column(String, nullable=True)
    next_retry_at: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")


# --- Pydantic Models ---

class WebhookCreateRequest(BaseModel):
    """Payload for creating a new webhook subscription."""

    url: str
    events: list[str]  # e.g. ["job.completed", "job.failed"]


class WebhookResponse(BaseModel):
    """Webhook subscription details returned by API."""

    id: str
    url: str
    events: list[str]
    is_active: bool
    created_at: str
    updated_at: str
    secret: str | None = None  # only returned once at creation time


class WebhookDeliveryResponse(BaseModel):
    """Single webhook delivery attempt record."""

    id: str
    event_type: str
    status: str
    attempt: int
    response_status: int | None
    delivered_at: str | None
