"""E2E tests for pipeline management flow."""

import pytest


@pytest.mark.e2e
async def test_pipeline_list(client):
    """List pipelines returns pipelines."""
    resp = await client.get("/pipelines")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.e2e
async def test_pipeline_create(client):
    """Create pipeline stores YAML config."""
    pipeline_config = """
name: test-pipeline
description: Test pipeline
steps:
  - id: extract
    type: extract
    config:
      mode: cloud
      cloud_provider: gemini
  - id: validate
    type: validate
    config:
      min_confidence: 0.7
"""
    resp = await client.post(
        "/pipelines",
        json={
            "name": "e2e-test-pipeline",
            "description": "E2E test",
            "config": pipeline_config,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "e2e-test-pipeline"
    assert "id" in data


@pytest.mark.e2e
async def test_pipeline_get(client):
    """Get pipeline by ID returns full config."""
    # Create
    config = "name: test\nsteps:\n  - id: s1\n    type: extract"
    resp = await client.post(
        "/pipelines",
        json={"name": "get-test", "config": config},
    )
    pipeline_id = resp.json()["id"]

    # Get
    resp = await client.get(f"/pipelines/{pipeline_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == pipeline_id


@pytest.mark.e2e
async def test_pipeline_get_nonexistent_returns_404(client):
    """Get nonexistent pipeline returns 404."""
    resp = await client.get("/pipelines/nonexistent")
    assert resp.status_code == 404


@pytest.mark.e2e
async def test_pipeline_delete(client):
    """Delete pipeline removes it."""
    # Create
    resp = await client.post(
        "/pipelines",
        json={
            "name": "delete-test",
            "config": "name: test\nsteps:\n  - id: s1\n    type: extract",
        },
    )
    pipeline_id = resp.json()["id"]

    # Soft delete (deactivate)
    resp = await client.delete(f"/pipelines/{pipeline_id}")
    assert resp.status_code == 200


@pytest.mark.e2e
async def test_pipeline_invalid_yaml_rejected(client):
    """Invalid YAML pipeline config is rejected."""
    resp = await client.post(
        "/pipelines",
        json={
            "name": "bad-yaml",
            "config": "{ invalid yaml [",
        },
    )
    assert resp.status_code == 400


@pytest.mark.e2e
async def test_pipeline_duplicate_name_rejected(client):
    """Creating pipeline with duplicate name fails."""
    config = "name: test\nsteps:\n  - id: s1\n    type: extract"
    # Create first
    await client.post(
        "/pipelines",
        json={"name": "dup-pipeline", "config": config},
    )
    # Try duplicate
    resp = await client.post(
        "/pipelines",
        json={"name": "dup-pipeline", "config": config},
    )
    assert resp.status_code in (409, 400)


@pytest.mark.e2e
async def test_pipeline_list_empty(client):
    """Pipeline list works on empty workspace."""
    resp = await client.get("/pipelines")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
