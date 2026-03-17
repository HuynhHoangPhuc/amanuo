"""E2E tests for RBAC enforcement — role-based access control on endpoints."""

import importlib

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app

_auth_service = importlib.import_module("src.services.auth-service")


async def _login(email: str, password: str) -> str:
    """Login and return access token."""
    result = await _auth_service.login_user(email, password)
    return result["access_token"] if result else ""


@pytest.mark.e2e
async def test_admin_can_list_users(db_with_users_and_roles):
    data = db_with_users_and_roles
    token = await _login("admin@test.com", data["password"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.e2e
async def test_reviewer_cannot_list_users(db_with_users_and_roles):
    data = db_with_users_and_roles
    token = await _login("reviewer0@test.com", data["password"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


@pytest.mark.e2e
async def test_admin_can_create_policy(db_with_users_and_roles):
    data = db_with_users_and_roles
    token = await _login("admin@test.com", data["password"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/approval-policies",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "E2E Chain",
                "policy_type": "chain",
                "config": {"steps": [{"role": "reviewer", "label": "Review"}]},
            },
        )
    assert resp.status_code == 201


@pytest.mark.e2e
async def test_reviewer_cannot_create_policy(db_with_users_and_roles):
    data = db_with_users_and_roles
    token = await _login("reviewer0@test.com", data["password"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/approval-policies",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Blocked",
                "policy_type": "chain",
                "config": {"steps": [{"role": "reviewer", "label": "R"}]},
            },
        )
    assert resp.status_code == 403


@pytest.mark.e2e
async def test_api_key_auth_treated_as_admin(db_with_users_and_roles):
    """API key auth (no JWT) should be treated as admin for backward compat."""
    data = db_with_users_and_roles

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/users", headers={"X-API-Key": data["api_key"]}
        )
    assert resp.status_code == 200


@pytest.mark.e2e
async def test_unauthenticated_cannot_access_users():
    """No auth header should return 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/users")
    assert resp.status_code == 401


@pytest.mark.e2e
async def test_get_current_user_profile(db_with_users_and_roles):
    data = db_with_users_and_roles
    token = await _login("admin@test.com", data["password"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == data["admin_id"]
    assert "admin" in body["roles"]


@pytest.mark.e2e
async def test_admin_can_assign_role(db_with_users_and_roles):
    data = db_with_users_and_roles
    token = await _login("admin@test.com", data["password"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/users/{data['reviewer_ids'][0]}/roles",
            headers={"Authorization": f"Bearer {token}"},
            json={"role": "approver"},
        )
    assert resp.status_code == 201
    assert resp.json()["status"] == "assigned"


@pytest.mark.e2e
async def test_admin_cannot_remove_own_admin_role(db_with_users_and_roles):
    data = db_with_users_and_roles
    token = await _login("admin@test.com", data["password"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete(
            f"/users/{data['admin_id']}/roles/admin",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 400
    assert "own admin" in resp.json()["detail"].lower()


@pytest.mark.e2e
async def test_reviewer_can_access_review_queue(db_with_users_and_roles):
    data = db_with_users_and_roles
    token = await _login("reviewer0@test.com", data["password"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/review-queue", headers={"Authorization": f"Bearer {token}"}
        )
    assert resp.status_code == 200
