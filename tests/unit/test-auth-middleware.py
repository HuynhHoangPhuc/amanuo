"""Unit tests for auth middleware."""

import importlib
import hashlib
import pytest

from fastapi import HTTPException

_auth_middleware = importlib.import_module("src.middleware.auth-middleware")


class TestAuthMiddleware:
    """Test auth middleware workspace extraction."""

    @pytest.mark.unit
    async def test_no_api_key_returns_default_workspace(self):
        """Without X-API-Key header, default workspace is returned."""
        # Create a mock request with no X-API-Key header
        class MockRequest:
            def __init__(self):
                self.headers = {}

        request = MockRequest()
        workspace_id = await _auth_middleware.get_workspace_id(request)
        assert workspace_id == "default"

    @pytest.mark.unit
    async def test_valid_api_key_returns_workspace_id(self, client, db_with_api_key):
        """Valid API key returns associated workspace ID."""
        # db_with_api_key fixture provides (workspace_id, raw_key)
        workspace_id, raw_key = db_with_api_key

        class MockRequest:
            def __init__(self, key):
                self.headers = {"X-API-Key": key}

        request = MockRequest(raw_key)
        result = await _auth_middleware.get_workspace_id(request)
        assert result == workspace_id

    @pytest.mark.unit
    async def test_invalid_api_key_raises_401(self, db_with_api_key):
        """Invalid API key raises HTTPException with 401."""
        _, _ = db_with_api_key

        class MockRequest:
            def __init__(self):
                self.headers = {"X-API-Key": "invalid-key-xyz"}

        request = MockRequest()
        with pytest.raises(HTTPException) as exc_info:
            await _auth_middleware.get_workspace_id(request)
        assert exc_info.value.status_code == 401
        assert "Invalid or inactive" in exc_info.value.detail

    @pytest.mark.unit
    async def test_revoked_api_key_raises_401(self, client, db_with_revoked_api_key):
        """Revoked API key (is_active=0) raises 401."""
        workspace_id, raw_key = db_with_revoked_api_key

        class MockRequest:
            def __init__(self, key):
                self.headers = {"X-API-Key": key}

        request = MockRequest(raw_key)
        with pytest.raises(HTTPException) as exc_info:
            await _auth_middleware.get_workspace_id(request)
        assert exc_info.value.status_code == 401
        assert "Invalid or inactive" in exc_info.value.detail
