"""E2E tests for batch processing flow."""

import struct
import zlib

import pytest


def _minimal_png() -> bytes:
    """Generate a minimal valid 1x1 white PNG."""
    def _chunk(chunk_type, data):
        c = chunk_type + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc

    header = b"\x89PNG\r\n\x1a\n"
    ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    raw = b"\x00\xff\xff\xff"
    idat = _chunk(b"IDAT", zlib.compress(raw))
    iend = _chunk(b"IEND", b"")
    return header + ihdr + idat + iend


_SCHEMA = '[{"label_name": "test", "data_type": "plain text", "occurrence": "required once"}]'


@pytest.mark.e2e
async def test_batch_create(client):
    """Create batch via multi-file upload returns batch_id."""
    png = _minimal_png()
    resp = await client.post(
        "/extract/batch",
        files=[("files", ("f1.png", png, "image/png"))],
        data={"schema_fields": _SCHEMA},
    )
    assert resp.status_code == 202
    data = resp.json()
    assert "batch_id" in data
    assert data["total_items"] == 1


@pytest.mark.e2e
async def test_batch_list(client):
    """List batches returns batches."""
    png = _minimal_png()
    await client.post(
        "/extract/batch",
        files=[("files", ("f1.png", png, "image/png"))],
        data={"schema_fields": _SCHEMA},
    )
    resp = await client.get("/batches")
    assert resp.status_code == 200
    data = resp.json()
    assert "batches" in data
    assert "total" in data


@pytest.mark.e2e
async def test_batch_get(client):
    """Get batch by ID returns batch details."""
    png = _minimal_png()
    resp = await client.post(
        "/extract/batch",
        files=[("files", ("f1.png", png, "image/png")), ("files", ("f2.png", png, "image/png"))],
        data={"schema_fields": _SCHEMA},
    )
    batch_id = resp.json()["batch_id"]

    resp = await client.get(f"/batches/{batch_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == batch_id
    assert data["total_items"] == 2


@pytest.mark.e2e
async def test_batch_get_nonexistent_returns_404(client):
    """Get nonexistent batch returns 404."""
    resp = await client.get("/batches/nonexistent")
    assert resp.status_code == 404


@pytest.mark.e2e
async def test_batch_cancel(client):
    """Cancel batch."""
    png = _minimal_png()
    resp = await client.post(
        "/extract/batch",
        files=[("files", ("f1.png", png, "image/png"))],
        data={"schema_fields": _SCHEMA},
    )
    batch_id = resp.json()["batch_id"]

    resp = await client.post(f"/batches/{batch_id}/cancel")
    assert resp.status_code == 200
