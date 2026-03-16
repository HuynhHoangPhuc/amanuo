"""Webhook CRUD operations and event publishing."""

import importlib
import json
import logging
import secrets
import uuid
from datetime import datetime

from src.config import settings
from src.database import get_connection, get_db_path
from src.models.webhook import WebhookResponse, WebhookDeliveryResponse

logger = logging.getLogger(__name__)

# Lazy-loaded to avoid circular imports
_delivery = None


def _get_delivery():
    """Lazy-load delivery module (avoids import-time circular deps)."""
    global _delivery
    if _delivery is None:
        _delivery = importlib.import_module("src.services.webhook-delivery")
    return _delivery


async def _get_db():
    """Open a database connection."""
    return await get_connection(get_db_path(settings.database_url))


def _row_to_response(row, secret: str | None = None) -> WebhookResponse:
    """Convert a DB row to WebhookResponse model.

    Args:
        row: aiosqlite Row from webhooks table
        secret: Plain-text secret — only passed at creation time

    Returns:
        WebhookResponse instance
    """
    return WebhookResponse(
        id=row["id"],
        url=row["url"],
        events=json.loads(row["events"]),
        is_active=bool(row["is_active"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        secret=secret,
    )


async def create_webhook(workspace_id: str, url: str, events: list[str]) -> WebhookResponse:
    """Create a new webhook subscription.

    Generates an HMAC signing secret returned once to the caller.

    Args:
        workspace_id: Owning workspace
        url: Target URL for event delivery
        events: List of event type strings to subscribe to

    Returns:
        WebhookResponse with secret populated (only on creation)
    """
    webhook_id = str(uuid.uuid4())
    raw_secret = secrets.token_urlsafe(32)
    events_json = json.dumps(events)
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")

    db = await _get_db()
    try:
        await db.execute(
            """
            INSERT INTO webhooks (id, workspace_id, url, events, secret, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (webhook_id, workspace_id, url, events_json, raw_secret, now, now),
        )
        await db.commit()

        cursor = await db.execute(
            "SELECT id, url, events, is_active, created_at, updated_at FROM webhooks WHERE id = ?",
            (webhook_id,),
        )
        row = await cursor.fetchone()
        return _row_to_response(row, secret=raw_secret)
    finally:
        await db.close()


async def list_webhooks(workspace_id: str) -> list[WebhookResponse]:
    """Return all webhook subscriptions for a workspace.

    Args:
        workspace_id: Owning workspace

    Returns:
        List of WebhookResponse (no secrets)
    """
    db = await _get_db()
    try:
        cursor = await db.execute(
            """
            SELECT id, url, events, is_active, created_at, updated_at
            FROM webhooks
            WHERE workspace_id = ?
            ORDER BY created_at DESC
            """,
            (workspace_id,),
        )
        rows = await cursor.fetchall()
        return [_row_to_response(row) for row in rows]
    finally:
        await db.close()


async def get_webhook(workspace_id: str, webhook_id: str) -> WebhookResponse | None:
    """Fetch a single webhook subscription.

    Args:
        workspace_id: Owning workspace (enforces scoping)
        webhook_id: Webhook primary key

    Returns:
        WebhookResponse or None if not found / not in workspace
    """
    db = await _get_db()
    try:
        cursor = await db.execute(
            """
            SELECT id, url, events, is_active, created_at, updated_at
            FROM webhooks
            WHERE id = ? AND workspace_id = ?
            """,
            (webhook_id, workspace_id),
        )
        row = await cursor.fetchone()
        return _row_to_response(row) if row else None
    finally:
        await db.close()


async def delete_webhook(workspace_id: str, webhook_id: str) -> bool:
    """Delete a webhook subscription.

    Args:
        workspace_id: Owning workspace (enforces scoping)
        webhook_id: Webhook primary key

    Returns:
        True if deleted, False if not found
    """
    db = await _get_db()
    try:
        cursor = await db.execute(
            "DELETE FROM webhooks WHERE id = ? AND workspace_id = ?",
            (webhook_id, workspace_id),
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def get_subscriptions(workspace_id: str, event_type: str) -> list[dict]:
    """Find active webhooks subscribed to a specific event type.

    Args:
        workspace_id: Owning workspace
        event_type: e.g. 'job.completed'

    Returns:
        List of dicts with webhook id, url, secret
    """
    db = await _get_db()
    try:
        cursor = await db.execute(
            """
            SELECT id, url, secret, events
            FROM webhooks
            WHERE workspace_id = ? AND is_active = 1
            """,
            (workspace_id,),
        )
        rows = await cursor.fetchall()
        matched = []
        for row in rows:
            subscribed = json.loads(row["events"])
            if event_type in subscribed:
                matched.append({
                    "id": row["id"],
                    "url": row["url"],
                    "secret": row["secret"],
                })
        return matched
    finally:
        await db.close()


async def publish_event(workspace_id: str, event_type: str, data: dict) -> None:
    """Fan out an event to all matching webhook subscriptions.

    Creates a delivery record per subscription and enqueues async delivery.

    Args:
        workspace_id: Owning workspace
        event_type: e.g. 'job.completed'
        data: Arbitrary event payload dict
    """
    subscriptions = await get_subscriptions(workspace_id, event_type)
    if not subscriptions:
        return

    payload = {
        "event": event_type,
        "workspace_id": workspace_id,
        "data": data,
    }
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")

    db = await _get_db()
    try:
        delivery_ids = []
        for sub in subscriptions:
            delivery_id = str(uuid.uuid4())
            await db.execute(
                """
                INSERT INTO webhook_deliveries
                    (id, webhook_id, event_type, payload, attempt, status)
                VALUES (?, ?, ?, ?, 1, 'pending')
                """,
                (delivery_id, sub["id"], event_type, payload_json),
            )
            delivery_ids.append(delivery_id)

        await db.commit()
    finally:
        await db.close()

    delivery_mod = _get_delivery()
    for delivery_id in delivery_ids:
        delivery_mod.enqueue_delivery(delivery_id)

    logger.info(
        "Published event '%s' to %d webhook(s) for workspace %s",
        event_type,
        len(delivery_ids),
        workspace_id,
    )


async def list_deliveries(workspace_id: str, webhook_id: str) -> list[WebhookDeliveryResponse]:
    """Return recent delivery attempts for a webhook.

    Args:
        workspace_id: Owning workspace (enforces scoping)
        webhook_id: Webhook primary key

    Returns:
        List of WebhookDeliveryResponse (latest 50)
    """
    db = await _get_db()
    try:
        # Verify ownership first
        cursor = await db.execute(
            "SELECT id FROM webhooks WHERE id = ? AND workspace_id = ?",
            (webhook_id, workspace_id),
        )
        if not await cursor.fetchone():
            return []

        cursor = await db.execute(
            """
            SELECT id, event_type, status, attempt, response_status, delivered_at
            FROM webhook_deliveries
            WHERE webhook_id = ?
            ORDER BY rowid DESC
            LIMIT 50
            """,
            (webhook_id,),
        )
        rows = await cursor.fetchall()
        return [
            WebhookDeliveryResponse(
                id=row["id"],
                event_type=row["event_type"],
                status=row["status"],
                attempt=row["attempt"],
                response_status=row["response_status"],
                delivered_at=row["delivered_at"],
            )
            for row in rows
        ]
    finally:
        await db.close()
