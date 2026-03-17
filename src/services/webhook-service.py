"""Webhook CRUD operations and event publishing — SQLAlchemy ORM."""

import importlib
import json
import logging
import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session_factory
from src.models.webhook import WebhookORM, WebhookDeliveryORM, WebhookResponse, WebhookDeliveryResponse

logger = logging.getLogger(__name__)

# Lazy-loaded to avoid circular imports
_delivery = None


def _get_delivery():
    global _delivery
    if _delivery is None:
        _delivery = importlib.import_module("src.services.webhook-delivery")
    return _delivery


def _get_session():
    return get_session_factory()()


def _orm_to_response(row: WebhookORM, secret: str | None = None) -> WebhookResponse:
    return WebhookResponse(
        id=row.id,
        url=row.url,
        events=json.loads(row.events),
        is_active=bool(row.is_active),
        created_at=row.created_at,
        updated_at=row.updated_at,
        secret=secret,
    )


async def create_webhook(workspace_id: str, url: str, events: list[str]) -> WebhookResponse:
    """Create a new webhook subscription. Returns response with secret (once)."""
    webhook_id = str(uuid.uuid4())
    raw_secret = secrets.token_urlsafe(32)
    events_json = json.dumps(events)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    async with _get_session() as session:
        webhook = WebhookORM(
            id=webhook_id,
            workspace_id=workspace_id,
            url=url,
            events=events_json,
            secret=raw_secret,
            is_active=1,
            created_at=now,
            updated_at=now,
        )
        session.add(webhook)
        await session.commit()
        await session.refresh(webhook)
        return _orm_to_response(webhook, secret=raw_secret)


async def list_webhooks(workspace_id: str) -> list[WebhookResponse]:
    """Return all webhook subscriptions for a workspace (no secrets)."""
    async with _get_session() as session:
        result = await session.execute(
            select(WebhookORM)
            .where(WebhookORM.workspace_id == workspace_id)
            .order_by(WebhookORM.created_at.desc())
        )
        rows = result.scalars().all()
        return [_orm_to_response(r) for r in rows]


async def get_webhook(workspace_id: str, webhook_id: str) -> WebhookResponse | None:
    """Fetch a single webhook subscription."""
    async with _get_session() as session:
        result = await session.execute(
            select(WebhookORM).where(
                WebhookORM.id == webhook_id, WebhookORM.workspace_id == workspace_id
            )
        )
        row = result.scalar_one_or_none()
        return _orm_to_response(row) if row else None


async def delete_webhook(workspace_id: str, webhook_id: str) -> bool:
    """Delete a webhook subscription."""
    async with _get_session() as session:
        result = await session.execute(
            delete(WebhookORM).where(
                WebhookORM.id == webhook_id, WebhookORM.workspace_id == workspace_id
            )
        )
        await session.commit()
        return result.rowcount > 0


async def get_subscriptions(workspace_id: str, event_type: str) -> list[dict]:
    """Find active webhooks subscribed to a specific event type."""
    async with _get_session() as session:
        result = await session.execute(
            select(WebhookORM).where(
                WebhookORM.workspace_id == workspace_id,
                WebhookORM.is_active == 1,
            )
        )
        rows = result.scalars().all()
        matched = []
        for row in rows:
            subscribed = json.loads(row.events)
            if event_type in subscribed:
                matched.append({"id": row.id, "url": row.url, "secret": row.secret})
        return matched


async def publish_event(workspace_id: str, event_type: str, data: dict) -> None:
    """Fan out an event to all matching webhook subscriptions."""
    subscriptions = await get_subscriptions(workspace_id, event_type)
    if not subscriptions:
        return

    payload = {"event": event_type, "workspace_id": workspace_id, "data": data}
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    delivery_ids = []
    async with _get_session() as session:
        for sub in subscriptions:
            delivery_id = str(uuid.uuid4())
            delivery = WebhookDeliveryORM(
                id=delivery_id,
                webhook_id=sub["id"],
                event_type=event_type,
                payload=payload_json,
                attempt=1,
                status="pending",
            )
            session.add(delivery)
            delivery_ids.append(delivery_id)
        await session.commit()

    delivery_mod = _get_delivery()
    for delivery_id in delivery_ids:
        delivery_mod.enqueue_delivery(delivery_id)

    logger.info(
        "Published event '%s' to %d webhook(s) for workspace %s",
        event_type, len(delivery_ids), workspace_id,
    )


async def list_deliveries(workspace_id: str, webhook_id: str) -> list[WebhookDeliveryResponse]:
    """Return recent delivery attempts for a webhook (latest 50)."""
    async with _get_session() as session:
        # Verify ownership
        owns = await session.execute(
            select(WebhookORM).where(
                WebhookORM.id == webhook_id, WebhookORM.workspace_id == workspace_id
            )
        )
        if not owns.scalar_one_or_none():
            return []

        result = await session.execute(
            select(WebhookDeliveryORM)
            .where(WebhookDeliveryORM.webhook_id == webhook_id)
            .order_by(WebhookDeliveryORM.id.desc())
            .limit(50)
        )
        rows = result.scalars().all()
        return [
            WebhookDeliveryResponse(
                id=r.id,
                event_type=r.event_type,
                status=r.status,
                attempt=r.attempt,
                response_status=r.response_status,
                delivered_at=r.delivered_at,
            )
            for r in rows
        ]
