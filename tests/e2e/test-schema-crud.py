"""E2E tests for schema CRUD endpoints."""

import pytest


@pytest.mark.e2e
async def test_list_schemas(client):
    resp = await client.get("/schemas")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.e2e
async def test_create_and_list_schema(client):
    schema_data = {
        "name": "test-e2e-schema",
        "fields": [
            {"label_name": "test_field", "data_type": "plain text", "occurrence": "required once"}
        ],
    }

    resp = await client.post("/schemas", json=schema_data)
    # Could be 201 or 409 if already exists from previous run
    assert resp.status_code in (201, 409)

    if resp.status_code == 201:
        data = resp.json()
        assert data["name"] == "test-e2e-schema"
        schema_id = data["id"]

        # Verify it appears in list
        resp = await client.get("/schemas")
        names = [s["name"] for s in resp.json()]
        assert "test-e2e-schema" in names

        # Cleanup
        await client.delete(f"/schemas/{schema_id}")


@pytest.mark.e2e
async def test_delete_nonexistent_schema(client):
    resp = await client.delete("/schemas/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.e2e
async def test_create_invalid_schema(client):
    schema_data = {
        "name": "bad-schema",
        "fields": [
            {
                "label_name": "a.b.c.d",
                "data_type": "plain text",
                "occurrence": "required once",
            }
        ],
    }
    resp = await client.post("/schemas", json=schema_data)
    assert resp.status_code == 400
