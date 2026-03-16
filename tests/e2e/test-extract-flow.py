"""E2E tests for the extraction flow API."""

import json

import pytest


@pytest.mark.e2e
async def test_health_endpoint(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "degraded")
    assert data["app"] == "amanuo"


@pytest.mark.e2e
async def test_extract_missing_file(client):
    resp = await client.post("/extract", data={"mode": "cloud"})
    assert resp.status_code == 422  # Missing required file


@pytest.mark.e2e
async def test_extract_missing_schema(client):
    # Create a minimal 1x1 PNG
    png_bytes = _minimal_png()
    resp = await client.post(
        "/extract",
        files={"file": ("test.png", png_bytes, "image/png")},
        data={"mode": "cloud"},
    )
    assert resp.status_code == 400
    assert "schema" in resp.text.lower()


@pytest.mark.e2e
async def test_extract_submit_returns_job_id(client):
    """Submit a valid extraction request and get a job ID back."""
    schema = json.dumps([
        {"label_name": "color", "data_type": "plain text", "occurrence": "required once"}
    ])
    png_bytes = _minimal_png()

    resp = await client.post(
        "/extract",
        files={"file": ("test.png", png_bytes, "image/png")},
        data={"mode": "cloud", "schema_fields": schema},
    )
    assert resp.status_code == 202
    data = resp.json()
    assert "job_id" in data
    assert data["status"] == "pending"


@pytest.mark.e2e
async def test_get_job_not_found(client):
    resp = await client.get("/jobs/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.e2e
async def test_get_job_after_submit(client):
    """Job should exist after submission."""
    schema = json.dumps([
        {"label_name": "test", "data_type": "plain text", "occurrence": "required once"}
    ])
    png_bytes = _minimal_png()

    resp = await client.post(
        "/extract",
        files={"file": ("test.png", png_bytes, "image/png")},
        data={"mode": "cloud", "schema_fields": schema},
    )
    job_id = resp.json()["job_id"]

    resp = await client.get(f"/jobs/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] in ("pending", "processing", "completed", "failed")


@pytest.mark.e2e
async def test_list_jobs(client):
    resp = await client.get("/jobs")
    assert resp.status_code == 200
    data = resp.json()
    assert "jobs" in data
    assert "total" in data


def _minimal_png() -> bytes:
    """Generate a minimal valid 1x1 white PNG."""
    import struct
    import zlib

    def _chunk(chunk_type, data):
        c = chunk_type + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc

    header = b"\x89PNG\r\n\x1a\n"
    ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    raw = b"\x00\xff\xff\xff"  # filter byte + RGB
    idat = _chunk(b"IDAT", zlib.compress(raw))
    iend = _chunk(b"IEND", b"")
    return header + ihdr + idat + iend
