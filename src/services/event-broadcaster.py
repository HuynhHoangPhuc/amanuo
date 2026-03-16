"""Publish/subscribe events for WebSocket delivery via Redis pub/sub."""

import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Lazy import: broadcaster may not be installed in test environments
try:
    from broadcaster import Broadcast
    _BROADCASTER_AVAILABLE = True
except ImportError:
    _BROADCASTER_AVAILABLE = False

_broadcast = None


async def init_broadcaster(redis_url: str) -> None:
    """Connect broadcaster to Redis. No-op if broadcaster not available."""
    global _broadcast
    if not _BROADCASTER_AVAILABLE:
        logger.warning("broadcaster package not available — WebSocket events disabled")
        return
    _broadcast = Broadcast(redis_url)
    await _broadcast.connect()
    logger.info("Broadcaster connected to %s", redis_url)


async def shutdown_broadcaster() -> None:
    """Disconnect broadcaster. No-op if not connected."""
    global _broadcast
    if _broadcast:
        await _broadcast.disconnect()
        _broadcast = None


def get_broadcast():
    """Return broadcaster instance (may be None if unavailable)."""
    return _broadcast


async def publish(workspace_id: str, event_type: str, data: dict) -> None:
    """Publish event to workspace channel. Silent no-op if broadcaster not connected."""
    if not _broadcast:
        return
    payload = json.dumps({
        "type": event_type,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    try:
        await _broadcast.publish(channel=f"workspace:{workspace_id}", message=payload)
    except Exception as e:
        logger.debug("Broadcaster publish failed: %s", e)
