"""Async webhook delivery worker with retry backoff — ARQ or asyncio fallback."""

import asyncio
import hashlib
import hmac
import importlib
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select, update

from src.database import get_session_factory
from src.models.webhook import WebhookDeliveryORM, WebhookORM

logger = logging.getLogger(__name__)

# Fallback in-memory queue used when Redis unavailable
_fallback_queue: asyncio.Queue[str] = asyncio.Queue()

# Retry delay in seconds: 1min, 5min, 30min, 2hrs
RETRY_BACKOFFS = [60, 300, 1800, 7200]

_DELIVERY_TIMEOUT = 10.0


def sign_payload(secret: str, payload: dict) -> str:
    """Sign payload with HMAC-SHA256. Returns 'sha256=<hex>'."""
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"sha256={sig}"


def _get_session():
    return get_session_factory()()


def enqueue_delivery(delivery_id: str) -> None:
    """Schedule delivery via ARQ if Redis available, else use in-memory fallback."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_enqueue_delivery_async(delivery_id))
        else:
            _fallback_queue.put_nowait(delivery_id)
    except RuntimeError:
        _fallback_queue.put_nowait(delivery_id)


async def _enqueue_delivery_async(delivery_id: str) -> None:
    """Internal async enqueue — uses ARQ if Redis pool available."""
    _redis_pool = importlib.import_module("src.services.redis-pool")
    redis = await _redis_pool.get_redis()
    if redis:
        await redis.enqueue_job("deliver_webhook_task", delivery_id)
        logger.debug("Delivery %s enqueued via ARQ", delivery_id)
    else:
        logger.warning("Redis unavailable — delivery %s using in-memory queue", delivery_id)
        await _fallback_queue.put(delivery_id)


async def process_delivery(delivery_id: str) -> bool:
    """Public entry point called by ARQ task. Delegates to deliver()."""
    return await deliver(delivery_id)


async def deliver(delivery_id: str) -> bool:
    """Load delivery record and POST signed payload to webhook URL."""
    async with _get_session() as session:
        result = await session.execute(
            select(WebhookDeliveryORM, WebhookORM)
            .join(WebhookORM, WebhookORM.id == WebhookDeliveryORM.webhook_id)
            .where(WebhookDeliveryORM.id == delivery_id)
        )
        row = result.first()
        if not row:
            logger.warning("Delivery %s not found, skipping", delivery_id)
            return False

        delivery, webhook = row

        if not webhook.is_active:
            await session.execute(
                update(WebhookDeliveryORM)
                .where(WebhookDeliveryORM.id == delivery_id)
                .values(status="failed")
            )
            await session.commit()
            return False

        payload = json.loads(delivery.payload)
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        signature = sign_payload(webhook.secret, payload)

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
            "X-Webhook-Event": delivery.event_type,
            "X-Webhook-Delivery": delivery_id,
        }

        try:
            async with httpx.AsyncClient(timeout=_DELIVERY_TIMEOUT) as client:
                response = await client.post(webhook.url, content=body, headers=headers)

            success = response.is_success
            response_body = response.text[:2000]

            if success:
                await session.execute(
                    update(WebhookDeliveryORM)
                    .where(WebhookDeliveryORM.id == delivery_id)
                    .values(
                        status="delivered",
                        response_status=response.status_code,
                        response_body=response_body,
                        delivered_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
                    )
                )
                await session.commit()
                logger.info("Webhook delivery %s succeeded (%s)", delivery_id, response.status_code)
                return True

            await _schedule_retry(session, delivery_id, delivery.attempt, response.status_code, response_body)
            return False

        except httpx.TimeoutException:
            logger.warning("Webhook delivery %s timed out", delivery_id)
            await _schedule_retry(session, delivery_id, delivery.attempt, None, "timeout")
            return False
        except httpx.RequestError as exc:
            logger.warning("Webhook delivery %s request error: %s", delivery_id, exc)
            await _schedule_retry(session, delivery_id, delivery.attempt, None, str(exc))
            return False


async def _schedule_retry(
    session,
    delivery_id: str,
    attempt: int,
    response_status: int | None,
    response_body: str | None,
) -> None:
    """Update delivery record with retry schedule or mark permanently failed."""
    if attempt <= len(RETRY_BACKOFFS):
        delay = RETRY_BACKOFFS[attempt - 1]
        next_retry = datetime.now(timezone.utc) + timedelta(seconds=delay)
        next_retry_str = next_retry.strftime("%Y-%m-%dT%H:%M:%S")
        await session.execute(
            update(WebhookDeliveryORM)
            .where(WebhookDeliveryORM.id == delivery_id)
            .values(
                status="pending",
                attempt=attempt + 1,
                response_status=response_status,
                response_body=response_body,
                next_retry_at=next_retry_str,
            )
        )
        logger.info("Webhook delivery %s scheduled retry #%d in %ds", delivery_id, attempt + 1, delay)
    else:
        await session.execute(
            update(WebhookDeliveryORM)
            .where(WebhookDeliveryORM.id == delivery_id)
            .values(
                status="failed",
                response_status=response_status,
                response_body=response_body,
            )
        )
        logger.warning("Webhook delivery %s permanently failed after %d attempts", delivery_id, attempt)

    await session.commit()


async def _worker_loop() -> None:
    """Consume delivery IDs from fallback queue and attempt delivery."""
    logger.info("Webhook delivery fallback worker started")
    while True:
        delivery_id = await _fallback_queue.get()
        try:
            await deliver(delivery_id)
        except Exception as exc:
            logger.error("Unexpected error delivering %s: %s", delivery_id, exc, exc_info=True)
        finally:
            _fallback_queue.task_done()


async def _retry_checker_loop() -> None:
    """Poll database every 30s and re-enqueue overdue pending deliveries."""
    logger.info("Webhook retry checker started")
    while True:
        await asyncio.sleep(30)
        try:
            async with _get_session() as session:
                result = await session.execute(
                    select(WebhookDeliveryORM)
                    .where(
                        WebhookDeliveryORM.status == "pending",
                        WebhookDeliveryORM.next_retry_at.isnot(None),
                        WebhookDeliveryORM.next_retry_at <= datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
                    )
                )
                rows = result.scalars().all()
                for row in rows:
                    enqueue_delivery(row.id)
                    logger.debug("Re-enqueued overdue delivery %s", row.id)
        except Exception as exc:
            logger.error("Retry checker error: %s", exc, exc_info=True)


def start_delivery_worker() -> asyncio.Task:
    """Start the fallback async delivery worker task."""
    return asyncio.create_task(_worker_loop(), name="webhook-delivery-worker")


def stop_delivery_worker(task: asyncio.Task) -> None:
    """Cancel the delivery worker task."""
    task.cancel()
    logger.info("Webhook delivery worker stopped")


def start_retry_checker() -> asyncio.Task:
    """Start the retry checker task that polls for overdue deliveries."""
    return asyncio.create_task(_retry_checker_loop(), name="webhook-retry-checker")


def stop_retry_checker(task: asyncio.Task) -> None:
    """Cancel the retry checker task."""
    task.cancel()
    logger.info("Webhook retry checker stopped")
