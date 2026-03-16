"""E2E tests for authentication flow."""

import pytest


@pytest.mark.e2e
async def test_auth_register_user(client):
    """User registration endpoint creates user."""
    resp = await client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "password123"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "user@example.com"
    assert "id" in data


@pytest.mark.e2e
async def test_auth_duplicate_email_fails(client):
    """Registering duplicate email fails."""
    await client.post(
        "/auth/register",
        json={"email": "dup@example.com", "password": "password123"},
    )
    resp = await client.post(
        "/auth/register",
        json={"email": "dup@example.com", "password": "password456"},
    )
    assert resp.status_code in (400, 409)


@pytest.mark.e2e
async def test_auth_login_user(client):
    """User login returns JWT tokens."""
    await client.post(
        "/auth/register",
        json={"email": "login@example.com", "password": "password123"},
    )
    resp = await client.post(
        "/auth/login",
        json={"email": "login@example.com", "password": "password123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.e2e
async def test_auth_login_wrong_password_fails(client):
    """Login with wrong password fails."""
    await client.post(
        "/auth/register",
        json={"email": "test@example.com", "password": "correct"},
    )
    resp = await client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "wrong"},
    )
    assert resp.status_code == 401


@pytest.mark.e2e
async def test_auth_create_api_key(client):
    """Create API key for workspace."""
    resp = await client.post(
        "/api-keys",
        json={"name": "test-key"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "key" in data
    assert "key_prefix" in data
    assert data["name"] == "test-key"


@pytest.mark.e2e
async def test_auth_list_api_keys(client):
    """List API keys shows all for workspace."""
    await client.post("/api-keys", json={"name": "key1"})
    resp = await client.get("/api-keys")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    for key in data:
        assert "key_prefix" in key


@pytest.mark.e2e
async def test_auth_revoke_api_key(client):
    """Revoke API key disables it."""
    resp = await client.post("/api-keys", json={"name": "revoke-test"})
    key_id = resp.json()["id"]

    resp = await client.delete(f"/api-keys/{key_id}")
    assert resp.status_code == 200
