"""Unit tests for WebSocket event broadcaster and router — no Redis required."""

import importlib
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── event-broadcaster ────────────────────────────────────────────────────────

_broadcaster = importlib.import_module("src.services.event-broadcaster")


class TestEventBroadcaster:
    """Tests for publish/subscribe helpers — broadcaster treated as optional."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_publish_noop_when_not_connected(self):
        """publish() must be silent when broadcaster is None."""
        original = _broadcaster._broadcast
        _broadcaster._broadcast = None
        try:
            # Should not raise
            await _broadcaster.publish("ws1", "job.completed", {"job_id": "j1"})
        finally:
            _broadcaster._broadcast = original

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_publish_calls_broadcast(self):
        """publish() forwards JSON payload to broadcaster.publish()."""
        mock_bc = AsyncMock()
        original = _broadcaster._broadcast
        _broadcaster._broadcast = mock_bc
        try:
            await _broadcaster.publish("ws1", "job.completed", {"job_id": "j1"})
            mock_bc.publish.assert_awaited_once()
            call_kwargs = mock_bc.publish.call_args.kwargs
            assert call_kwargs["channel"] == "workspace:ws1"
            payload = json.loads(call_kwargs["message"])
            assert payload["type"] == "job.completed"
            assert payload["data"]["job_id"] == "j1"
            assert "timestamp" in payload
        finally:
            _broadcaster._broadcast = original

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_publish_swallows_broadcast_error(self):
        """publish() must not raise when broadcaster.publish() fails."""
        mock_bc = AsyncMock()
        mock_bc.publish.side_effect = RuntimeError("redis gone")
        original = _broadcaster._broadcast
        _broadcaster._broadcast = mock_bc
        try:
            await _broadcaster.publish("ws1", "job.failed", {"job_id": "j2"})
        finally:
            _broadcaster._broadcast = original

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_shutdown_resets_to_none(self):
        """shutdown_broadcaster() sets _broadcast to None."""
        mock_bc = AsyncMock()
        original = _broadcaster._broadcast
        _broadcaster._broadcast = mock_bc
        try:
            await _broadcaster.shutdown_broadcaster()
            assert _broadcaster._broadcast is None
        finally:
            _broadcaster._broadcast = original

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_shutdown_noop_when_none(self):
        """shutdown_broadcaster() is safe when already None."""
        original = _broadcaster._broadcast
        _broadcaster._broadcast = None
        try:
            await _broadcaster.shutdown_broadcaster()  # Should not raise
        finally:
            _broadcaster._broadcast = original

    @pytest.mark.unit
    def test_get_broadcast_returns_instance(self):
        """get_broadcast() returns current instance (may be None)."""
        original = _broadcaster._broadcast
        try:
            _broadcaster._broadcast = None
            assert _broadcaster.get_broadcast() is None
            fake = MagicMock()
            _broadcaster._broadcast = fake
            assert _broadcaster.get_broadcast() is fake
        finally:
            _broadcaster._broadcast = original


# ── websocket-events router ───────────────────────────────────────────────────

_ws_router = importlib.import_module("src.routers.websocket-events")


class TestWebSocketAuth:
    """Tests for _authenticate_ws helper."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_empty_key_returns_none(self):
        result = await _ws_router._authenticate_ws("")
        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_key_returns_none(self):
        with patch.object(
            _ws_router._auth_service,
            "validate_key",
            new=AsyncMock(return_value=None),
        ):
            result = await _ws_router._authenticate_ws("bad-key")
            assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_inactive_key_returns_none(self):
        with patch.object(
            _ws_router._auth_service,
            "validate_key",
            new=AsyncMock(return_value={"workspace_id": "ws1", "is_active": False}),
        ):
            result = await _ws_router._authenticate_ws("inactive-key")
            assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_valid_key_returns_workspace_id(self):
        with patch.object(
            _ws_router._auth_service,
            "validate_key",
            new=AsyncMock(return_value={"workspace_id": "ws1", "is_active": True}),
        ):
            result = await _ws_router._authenticate_ws("valid-key")
            assert result == "ws1"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_auth_exception_returns_none(self):
        with patch.object(
            _ws_router._auth_service,
            "validate_key",
            new=AsyncMock(side_effect=RuntimeError("db error")),
        ):
            result = await _ws_router._authenticate_ws("some-key")
            assert result is None
