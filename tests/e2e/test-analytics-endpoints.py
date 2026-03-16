"""E2E tests for analytics API endpoints."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient

from src.database import get_connection, get_db_path
from src.config import settings


async def _create_workspace_with_jobs(n_jobs: int = 12) -> tuple[str, str]:
    """Seed a workspace with API key and varied jobs; return (workspace_id, raw_key)."""
    workspace_id = str(uuid.uuid4())
    raw_key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_id = str(uuid.uuid4())
    now = datetime.now()

    db = await get_connection(get_db_path(settings.database_url))
    try:
        now_iso = now.isoformat()
        await db.execute(
            "INSERT INTO workspaces (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (workspace_id, f"e2e-analytics-{workspace_id[:8]}", now_iso, now_iso),
        )
        await db.execute(
            "INSERT INTO api_keys (id, workspace_id, name, key_hash, key_prefix, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (key_id, workspace_id, "e2e-key", key_hash, raw_key[:8], now_iso),
        )
        providers = ["gemini", "mistral", None]
        statuses = ["completed", "failed", "pending_review"]
        for i in range(n_jobs):
            jid = str(uuid.uuid4())
            provider = providers[i % 3]
            mode = "cloud" if provider else "local_only"
            status = statuses[i % 3]
            cost = 0.005 * (i + 1)
            job_date = (now - timedelta(days=i % 15)).isoformat()
            await db.execute(
                """INSERT INTO jobs (
                    id, workspace_id, status, mode, cloud_provider,
                    cost_estimated_usd, cost_input_tokens, cost_output_tokens,
                    confidence, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (jid, workspace_id, status, mode, provider, cost, 100, 50, 0.9, job_date),
            )
        await db.commit()
    finally:
        await db.close()

    return workspace_id, raw_key


@pytest.mark.e2e
async def test_get_usage_requires_no_auth_defaults_to_default_workspace(client: AsyncClient):
    """Unauthenticated requests use 'default' workspace — should 200 with empty list."""
    resp = await client.get("/analytics/usage?period=30d")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.e2e
async def test_get_usage_returns_200_with_data(client: AsyncClient):
    workspace_id, raw_key = await _create_workspace_with_jobs()
    resp = await client.get("/analytics/usage?period=30d", headers={"X-API-Key": raw_key})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    first = data[0]
    assert "date" in first
    assert "job_count" in first
    assert "success_count" in first
    assert "failed_count" in first


@pytest.mark.e2e
async def test_get_usage_default_period_30d(client: AsyncClient):
    workspace_id, raw_key = await _create_workspace_with_jobs()
    resp = await client.get("/analytics/usage", headers={"X-API-Key": raw_key})
    assert resp.status_code == 200


@pytest.mark.e2e
async def test_get_costs_returns_provider_breakdown(client: AsyncClient):
    workspace_id, raw_key = await _create_workspace_with_jobs()
    resp = await client.get("/analytics/costs?period=30d", headers={"X-API-Key": raw_key})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if data:
        assert "total_cost_usd" in data[0]
        assert "provider_breakdown" in data[0]
        assert isinstance(data[0]["provider_breakdown"], dict)


@pytest.mark.e2e
async def test_get_costs_workspace_isolation(client: AsyncClient):
    ws_a, key_a = await _create_workspace_with_jobs(6)
    ws_b, key_b = await _create_workspace_with_jobs(0)  # no jobs
    resp_b = await client.get("/analytics/costs?period=30d", headers={"X-API-Key": key_b})
    assert resp_b.status_code == 200
    # Workspace B has no jobs — should return empty list
    assert resp_b.json() == []


@pytest.mark.e2e
async def test_get_providers_returns_comparison(client: AsyncClient):
    workspace_id, raw_key = await _create_workspace_with_jobs()
    resp = await client.get("/analytics/providers?period=30d", headers={"X-API-Key": raw_key})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if data:
        stat = data[0]
        assert "provider" in stat
        assert "job_count" in stat
        assert "success_rate" in stat
        assert "total_cost_usd" in stat


@pytest.mark.e2e
async def test_get_overview_returns_summary(client: AsyncClient):
    workspace_id, raw_key = await _create_workspace_with_jobs()
    resp = await client.get("/analytics/overview?period=30d", headers={"X-API-Key": raw_key})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_jobs"] > 0
    assert data["total_cost_usd"] >= 0
    assert data["period"] == "30d"


@pytest.mark.e2e
async def test_post_refresh_returns_200(client: AsyncClient):
    resp = await client.post("/analytics/refresh")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.e2e
async def test_invalid_period_returns_422(client: AsyncClient):
    resp = await client.get("/analytics/usage?period=365d")
    assert resp.status_code == 422


@pytest.mark.e2e
async def test_analytics_empty_workspace_returns_empty(client: AsyncClient):
    # Create workspace with API key but zero jobs
    workspace_id, raw_key = await _create_workspace_with_jobs(0)
    resp = await client.get("/analytics/usage?period=30d", headers={"X-API-Key": raw_key})
    assert resp.status_code == 200
    assert resp.json() == []
