"""Async webhook delivery worker with retry backoff."""

import asyncio
import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timedelta

import httpx

from src.config import settings
from src.database import get_connection, get_db_path

logger = logging.getLogger(__name__)

_delivery_queue: asyncio.Queue[str] = asyncio.Queue()

# Retry delay in seconds: 1min, 5min, 30min, 2hrs
RETRY_BACKOFFS = [60, 300, 1800, 7200]

# Timeout per HTTP delivery attempt
_DELIVERY_TIMEOUT = 10.0


def sign_payload(secret: str, payload: dict) -> str:
    """Sign payload with HMAC-SHA256.

    Args:
        secret: Webhook signing secret
        payload: JSON-serializable event payload

    Returns:
        Signature string in format 'sha256=<hex>'
    """
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"sha256={sig}"


async def _get_db():
    """Open a database connection."""
    return await get_connection(get_db_path(settings.database_url))


def enqueue_delivery(delivery_id: str) -> None:
    """Add a delivery record ID to the async delivery queue.

    Args:
        delivery_id: Primary key of the webhook_deliveries row
    """
    _delivery_queue.put_nowait(delivery_id)


async def deliver(delivery_id: str) -> bool:
    """Load delivery record and POST signed payload to webhook URL.

    Marks delivery as 'delivered' on success, schedules retry on failure.

    Args:
        delivery_id: Primary key of the webhook_deliveries row

    Returns:
        True if delivery succeeded (2xx response), False otherwise
    """
    db = await _get_db()
    try:
        # Load delivery + webhook in one query
        cursor = await db.execute(
            """
            SELECT d.id, d.webhook_id, d.event_type, d.payload, d.attempt,
                   w.url, w.secret, w.is_active
            FROM webhook_deliveries d
            JOIN webhooks w ON w.id = d.webhook_id
            WHERE d.id = ?
            """,
            (delivery_id,),
        )
        row = await cursor.fetchone()
        if not row:
            logger.warning("Delivery %s not found, skipping", delivery_id)
            return False

        if not row["is_active"]:
            # Webhook was disabled — mark failed, no retry
            await db.execute(
                "UPDATE webhook_deliveries SET status = 'failed' WHERE id = ?",
                (delivery_id,),
            )
            await db.commit()
            return False

        payload = json.loads(row["payload"])
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        signature = sign_payload(row["secret"], payload)

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
            "X-Webhook-Event": row["event_type"],
            "X-Webhook-Delivery": delivery_id,
        }

        try:
            async with httpx.AsyncClient(timeout=_DELIVERY_TIMEOUT) as client:
                response = await client.post(row["url"], content=body, headers=headers)

            success = response.is_success
            response_body = response.text[:2000]  # cap stored response

            if success:
                await db.execute(
                    """
                    UPDATE webhook_deliveries
                    SET status = 'delivered',
                        response_status = ?,
                        response_body = ?,
                        delivered_at = datetime('now')
                    WHERE id = ?
                    """,
                    (response.status_code, response_body, delivery_id),
                )
                await db.commit()
                logger.info("Webhook delivery %s succeeded (%s)", delivery_id, response.status_code)
                return True

            # Non-2xx — schedule retry if attempts remain
            await _schedule_retry(db, delivery_id, row["attempt"], response.status_code, response_body)
            return False

        except httpx.TimeoutException:
            logger.warning("Webhook delivery %s timed out", delivery_id)
            await _schedule_retry(db, delivery_id, row["attempt"], None, "timeout")
            return False
        except httpx.RequestError as exc:
            logger.warning("Webhook delivery %s request error: %s", delivery_id, exc)
            await _schedule_retry(db, delivery_id, row["attempt"], None, str(exc))
            return False

    finally:
        await db.close()


async def _schedule_retry(
    db,
    delivery_id: str,
    attempt: int,
    response_status: int | None,
    response_body: str | None,
) -> None:
    """Update delivery record with retry schedule or mark permanently failed.

    Args:
        db: Open database connection
        delivery_id: Delivery row primary key
        attempt: Current attempt number (1-based)
        response_status: HTTP status code (None if network error)
        response_body: Response body text or error message
    """
    if attempt <= len(RETRY_BACKOFFS):
        delay = RETRY_BACKOFFS[attempt - 1]
        next_retry = datetime.utcnow() + timedelta(seconds=delay)
        next_retry_str = next_retry.strftime("%Y-%m-%dT%H:%M:%S")
        await db.execute(
            """
            UPDATE webhook_deliveries
            SET status = 'pending',
                attempt = ?,
                response_status = ?,
                response_body = ?,
                next_retry_at = ?
            WHERE id = ?
            """,
            (attempt + 1, response_status, response_body, next_retry_str, delivery_id),
        )
        logger.info("Webhook delivery %s scheduled retry #%d in %ds", delivery_id, attempt + 1, delay)
    else:
        await db.execute(
            """
            UPDATE webhook_deliveries
            SET status = 'failed',
                response_status = ?,
                response_body = ?
            WHERE id = ?
            """,
            (response_status, response_body, delivery_id),
        )
        logger.warning("Webhook delivery %s permanently failed after %d attempts", delivery_id, attempt)

    await db.commit()


async def _worker_loop() -> None:
    """Consume delivery IDs from the queue and attempt delivery."""
    logger.info("Webhook delivery worker started")
    while True:
        delivery_id = await _delivery_queue.get()
        try:
            await deliver(delivery_id)
        except Exception as exc:
            logger.error("Unexpected error delivering %s: %s", delivery_id, exc, exc_info=True)
        finally:
            _delivery_queue.task_done()


async def _retry_checker_loop() -> None:
    """Poll database every 30s and re-enqueue overdue pending deliveries."""
    logger.info("Webhook retry checker started")
    while True:
        await asyncio.sleep(30)
        try:
            db = await _get_db()
            try:
                cursor = await db.execute(
                    """
                    SELECT id FROM webhook_deliveries
                    WHERE status = 'pending'
                      AND next_retry_at IS NOT NULL
                      AND next_retry_at <= datetime('now')
                    """,
                )
                rows = await cursor.fetchall()
                for row in rows:
                    enqueue_delivery(row["id"])
                    logger.debug("Re-enqueued overdue delivery %s", row["id"])
            finally:
                await db.close()
        except Exception as exc:
            logger.error("Retry checker error: %s", exc, exc_info=True)


def start_delivery_worker() -> asyncio.Task:
    """Start the async delivery worker task.

    Returns:
        asyncio.Task that can be cancelled on shutdown
    """
    return asyncio.create_task(_worker_loop(), name="webhook-delivery-worker")


def stop_delivery_worker(task: asyncio.Task) -> None:
    """Cancel the delivery worker task.

    Args:
        task: Task returned by start_delivery_worker
    """
    task.cancel()
    logger.info("Webhook delivery worker stopped")


def start_retry_checker() -> asyncio.Task:
    """Start the retry checker task that polls for overdue deliveries.

    Returns:
        asyncio.Task that can be cancelled on shutdown
    """
    return asyncio.create_task(_retry_checker_loop(), name="webhook-retry-checker")


def stop_retry_checker(task: asyncio.Task) -> None:
    """Cancel the retry checker task.

    Args:
        task: Task returned by start_retry_checker
    """
    task.cancel()
    logger.info("Webhook retry checker stopped")
