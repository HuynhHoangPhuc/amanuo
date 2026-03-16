"""E2E tests for workspace isolation.

Workspace scoping is via X-API-Key header, not URL nesting.
These tests verify workspace CRUD and basic isolation.
"""

import pytest


@pytest.mark.e2e
async def test_workspace_create(client):
    """Create workspace."""
    resp = await client.post(
        "/workspaces",
        json={"name": "test-workspace"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "test-workspace"
    assert "id" in data


@pytest.mark.e2e
async def test_workspace_list(client):
    """List workspaces."""
    resp = await client.get("/workspaces")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.e2e
async def test_workspace_get(client):
    """Get workspace by ID."""
    resp = await client.post(
        "/workspaces",
        json={"name": "get-test"},
    )
    ws_id = resp.json()["id"]

    resp = await client.get(f"/workspaces/{ws_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == ws_id


@pytest.mark.e2e
async def test_workspace_cannot_delete_default(client):
    """Default workspace cannot be deleted."""
    resp = await client.delete("/workspaces/default")
    assert resp.status_code == 400


@pytest.mark.e2e
async def test_workspace_delete_custom(client):
    """Custom workspace can be deleted."""
    resp = await client.post(
        "/workspaces",
        json={"name": "delete-test"},
    )
    ws_id = resp.json()["id"]

    resp = await client.delete(f"/workspaces/{ws_id}")
    assert resp.status_code == 200

    resp = await client.get(f"/workspaces/{ws_id}")
    assert resp.status_code == 404


@pytest.mark.e2e
async def test_default_workspace_schemas_scoped(client):
    """Schemas created with default key are scoped to default workspace."""
    fields = [{"label_name": "f", "data_type": "plain text", "occurrence": "required once"}]
    resp = await client.post(
        "/schemas",
        json={"name": "scoped-schema", "fields": fields},
    )
    assert resp.status_code == 201

    # List schemas — should see the one we created
    resp = await client.get("/schemas")
    assert resp.status_code == 200
    names = [s["name"] for s in resp.json()]
    assert "scoped-schema" in names


@pytest.mark.e2e
async def test_default_workspace_jobs_scoped(client):
    """Jobs listing works for default workspace."""
    resp = await client.get("/jobs")
    assert resp.status_code == 200
    data = resp.json()
    assert "jobs" in data
    assert "total" in data


@pytest.mark.e2e
async def test_default_workspace_pipelines_scoped(client):
    """Pipelines listing works for default workspace."""
    resp = await client.get("/pipelines")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.e2e
async def test_default_workspace_webhooks_scoped(client):
    """Webhooks listing works for default workspace."""
    resp = await client.get("/webhooks")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
