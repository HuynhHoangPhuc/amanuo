"""WebSocket endpoint for real-time event streaming per workspace."""

import asyncio
import hashlib
import importlib
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()

_event_broadcaster = importlib.import_module("src.services.event-broadcaster")
_auth_service = importlib.import_module("src.services.auth-service")


@router.websocket("/ws/events")
async def websocket_events(
    ws: WebSocket,
    api_key: str = Query(default=""),
) -> None:
    """Stream workspace events to authenticated WebSocket clients."""
    workspace_id = await _authenticate_ws(api_key)
    if not workspace_id:
        await ws.close(code=4401, reason="Unauthorized")
        return

    await ws.accept()
    logger.debug("WS connected: workspace=%s", workspace_id)

    broadcast = _event_broadcaster.get_broadcast()

    if not broadcast:
        # No broadcaster — connected in polling fallback mode, keep alive with pings
        await ws.send_json({
            "type": "system.connected",
            "data": {"mode": "polling", "workspace_id": workspace_id},
            "timestamp": _now(),
        })
        await _keepalive(ws)
        return

    # Subscribe and relay events
    async with broadcast.subscribe(channel=f"workspace:{workspace_id}") as subscriber:
        await ws.send_json({
            "type": "system.connected",
            "data": {"workspace_id": workspace_id},
            "timestamp": _now(),
        })
        ping_task = asyncio.create_task(_heartbeat(ws))
        try:
            async for event in subscriber:
                await ws.send_text(event.message)
        except (WebSocketDisconnect, Exception):
            pass
        finally:
            ping_task.cancel()
            try:
                await ping_task
            except asyncio.CancelledError:
                pass

    logger.debug("WS disconnected: workspace=%s", workspace_id)


async def _authenticate_ws(api_key: str) -> str | None:
    """Validate API key from query param. Returns workspace_id or None."""
    if not api_key:
        return None
    try:
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        record = await _auth_service.validate_key(key_hash)
        if record and record.get("is_active"):
            return record["workspace_id"]
    except Exception as e:
        logger.debug("WS auth failed: %s", e)
    return None


async def _heartbeat(ws: WebSocket, interval: int = 30) -> None:
    """Send ping every 30s to keep connection alive."""
    while True:
        await asyncio.sleep(interval)
        try:
            await ws.send_json({"type": "ping", "data": {}, "timestamp": _now()})
        except Exception:
            break


async def _keepalive(ws: WebSocket, interval: int = 30) -> None:
    """Keep alive loop when broadcaster is unavailable."""
    try:
        while True:
            await asyncio.sleep(interval)
            await ws.send_json({"type": "ping", "data": {}, "timestamp": _now()})
    except (WebSocketDisconnect, Exception):
        pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
