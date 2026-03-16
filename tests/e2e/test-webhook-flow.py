"""E2E tests for webhook management flow."""

import pytest


@pytest.mark.e2e
async def test_webhook_create(client):
    """Create webhook subscription."""
    resp = await client.post(
        "/webhooks",
        json={
            "url": "https://example.com/webhook",
            "events": ["job.completed", "job.failed"],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["url"] == "https://example.com/webhook"
    assert "job.completed" in data["events"]
    assert "secret" in data


@pytest.mark.e2e
async def test_webhook_list(client):
    """List webhook subscriptions."""
    await client.post(
        "/webhooks",
        json={"url": "https://hook.com", "events": ["job.completed"]},
    )
    resp = await client.get("/webhooks")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.e2e
async def test_webhook_get(client):
    """Get single webhook."""
    resp = await client.post(
        "/webhooks",
        json={"url": "https://hook.com", "events": ["batch.completed"]},
    )
    webhook_id = resp.json()["id"]

    resp = await client.get(f"/webhooks/{webhook_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == webhook_id
    assert data["url"] == "https://hook.com"


@pytest.mark.e2e
async def test_webhook_delete(client):
    """Delete webhook subscription."""
    resp = await client.post(
        "/webhooks",
        json={"url": "https://hook.com", "events": ["job.completed"]},
    )
    webhook_id = resp.json()["id"]

    resp = await client.delete(f"/webhooks/{webhook_id}")
    assert resp.status_code == 200

    resp = await client.get(f"/webhooks/{webhook_id}")
    assert resp.status_code == 404


@pytest.mark.e2e
async def test_webhook_get_nonexistent_returns_404(client):
    """Get nonexistent webhook returns 404."""
    resp = await client.get("/webhooks/nonexistent")
    assert resp.status_code == 404


@pytest.mark.e2e
async def test_webhook_multiple_events(client):
    """Webhook can subscribe to multiple event types."""
    resp = await client.post(
        "/webhooks",
        json={
            "url": "https://hook.com",
            "events": ["job.completed", "job.failed", "batch.completed", "batch.failed"],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["events"]) == 4


@pytest.mark.e2e
async def test_webhook_deliveries_list(client):
    """List webhook delivery attempts."""
    resp = await client.post(
        "/webhooks",
        json={"url": "https://hook.com", "events": ["job.completed"]},
    )
    webhook_id = resp.json()["id"]

    resp = await client.get(f"/webhooks/{webhook_id}/deliveries")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
