"""Pydantic request/response models for webhook management."""

from pydantic import BaseModel

# Supported event types for webhook subscriptions
VALID_EVENTS = {"job.completed", "job.failed", "batch.completed", "batch.failed"}


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
