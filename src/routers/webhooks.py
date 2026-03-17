"""Webhook subscription management endpoints."""

import importlib
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from src.models.webhook import (
    VALID_EVENTS,
    WebhookCreateRequest,
    WebhookDeliveryResponse,
    WebhookResponse,
)

_auth = importlib.import_module("src.middleware.auth-middleware")
_svc = importlib.import_module("src.services.webhook-service")

get_workspace_id = _auth.get_workspace_id

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("", response_model=WebhookResponse, status_code=201)
async def create_webhook(
    req: WebhookCreateRequest,
    workspace_id: str = Depends(get_workspace_id),
):
    """Create a new webhook subscription.

    Returns signing secret once — store it safely, it will not be shown again.
    """
    invalid = [e for e in req.events if e not in VALID_EVENTS]
    if invalid:
        raise HTTPException(
            400,
            f"Invalid event type(s): {invalid}. Valid: {sorted(VALID_EVENTS)}",
        )
    if not req.events:
        raise HTTPException(400, "At least one event type is required")
    if not req.url.startswith(("http://", "https://")):
        raise HTTPException(400, "URL must start with http:// or https://")

    return await _svc.create_webhook(workspace_id, req.url, req.events)


@router.get("", response_model=list[WebhookResponse])
async def list_webhooks(workspace_id: str = Depends(get_workspace_id)):
    """List all webhook subscriptions for the authenticated workspace."""
    return await _svc.list_webhooks(workspace_id)


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: str,
    workspace_id: str = Depends(get_workspace_id),
):
    """Get details of a specific webhook subscription."""
    webhook = await _svc.get_webhook(workspace_id, webhook_id)
    if not webhook:
        raise HTTPException(404, f"Webhook {webhook_id} not found")
    return webhook


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    workspace_id: str = Depends(get_workspace_id),
):
    """Remove a webhook subscription."""
    deleted = await _svc.delete_webhook(workspace_id, webhook_id)
    if not deleted:
        raise HTTPException(404, f"Webhook {webhook_id} not found")
    return {"deleted": True}


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: str,
    workspace_id: str = Depends(get_workspace_id),
):
    """Send a test delivery to verify the webhook endpoint is reachable."""
    webhook = await _svc.get_webhook(workspace_id, webhook_id)
    if not webhook:
        raise HTTPException(404, f"Webhook {webhook_id} not found")

    await _svc.publish_event(
        workspace_id,
        event_type="job.completed",
        data={
            "test": True,
            "webhook_id": webhook_id,
            "message": "This is a test delivery from Amanuo",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        },
    )
    return {"queued": True, "webhook_id": webhook_id}


@router.get("/{webhook_id}/deliveries", response_model=list[WebhookDeliveryResponse])
async def list_deliveries(
    webhook_id: str,
    workspace_id: str = Depends(get_workspace_id),
):
    """List recent delivery attempts for a webhook (latest 50)."""
    webhook = await _svc.get_webhook(workspace_id, webhook_id)
    if not webhook:
        raise HTTPException(404, f"Webhook {webhook_id} not found")
    return await _svc.list_deliveries(workspace_id, webhook_id)
