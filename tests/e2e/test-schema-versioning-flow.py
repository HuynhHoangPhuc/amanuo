"""E2E tests for schema versioning flow."""

import pytest


@pytest.mark.e2e
async def test_schema_create_v1(client):
    """Create schema initializes version 1.0.0."""
    resp = await client.post(
        "/schemas",
        json={
            "name": "versioned-schema",
            "fields": [
                {"label_name": "field_a", "data_type": "plain text", "occurrence": "required once"}
            ],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["version"] == "1.0.0"


@pytest.mark.e2e
async def test_schema_add_optional_bumps_minor(client):
    """Adding optional field bumps minor version."""
    resp = await client.post(
        "/schemas",
        json={
            "name": "minor-bump-test",
            "fields": [
                {"label_name": "field_a", "data_type": "plain text", "occurrence": "required once"}
            ],
        },
    )
    schema_id = resp.json()["id"]

    resp = await client.put(
        f"/schemas/{schema_id}",
        json={
            "name": "minor-bump-test",
            "fields": [
                {"label_name": "field_a", "data_type": "plain text", "occurrence": "required once"},
                {"label_name": "field_b", "data_type": "plain text", "occurrence": "optional once"},
            ],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "1.1.0"


@pytest.mark.e2e
async def test_schema_remove_field_bumps_major(client):
    """Removing field bumps major version."""
    resp = await client.post(
        "/schemas",
        json={
            "name": "major-bump-test",
            "fields": [
                {"label_name": "field_a", "data_type": "plain text", "occurrence": "required once"},
                {"label_name": "field_b", "data_type": "plain text", "occurrence": "required once"},
            ],
        },
    )
    schema_id = resp.json()["id"]

    resp = await client.put(
        f"/schemas/{schema_id}",
        json={
            "name": "major-bump-test",
            "fields": [
                {"label_name": "field_a", "data_type": "plain text", "occurrence": "required once"},
            ],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "2.0.0"


@pytest.mark.e2e
async def test_schema_type_change_bumps_major(client):
    """Changing field type bumps major version."""
    resp = await client.post(
        "/schemas",
        json={
            "name": "type-change-test",
            "fields": [
                {"label_name": "field_a", "data_type": "plain text", "occurrence": "required once"}
            ],
        },
    )
    schema_id = resp.json()["id"]

    resp = await client.put(
        f"/schemas/{schema_id}",
        json={
            "name": "type-change-test",
            "fields": [
                {"label_name": "field_a", "data_type": "number", "occurrence": "required once"}
            ],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "2.0.0"


@pytest.mark.e2e
async def test_schema_prompt_change_bumps_patch(client):
    """Changing prompt bumps patch version."""
    resp = await client.post(
        "/schemas",
        json={
            "name": "patch-bump-test",
            "fields": [
                {
                    "label_name": "field_a",
                    "data_type": "plain text",
                    "occurrence": "required once",
                    "prompt_for_label": "Original prompt",
                }
            ],
        },
    )
    schema_id = resp.json()["id"]

    resp = await client.put(
        f"/schemas/{schema_id}",
        json={
            "name": "patch-bump-test",
            "fields": [
                {
                    "label_name": "field_a",
                    "data_type": "plain text",
                    "occurrence": "required once",
                    "prompt_for_label": "Updated prompt",
                }
            ],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "1.0.1"


@pytest.mark.e2e
async def test_schema_list_versions(client):
    """List schema versions returns all versions."""
    resp = await client.post(
        "/schemas",
        json={
            "name": "list-versions-test",
            "fields": [
                {"label_name": "f", "data_type": "plain text", "occurrence": "required once"}
            ],
        },
    )
    schema_id = resp.json()["id"]

    await client.put(
        f"/schemas/{schema_id}",
        json={
            "name": "list-versions-test",
            "fields": [
                {"label_name": "f", "data_type": "plain text", "occurrence": "required once"},
                {"label_name": "g", "data_type": "plain text", "occurrence": "optional once"},
            ],
        },
    )

    resp = await client.get(f"/schemas/{schema_id}/versions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2
