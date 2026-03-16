"""Shared test fixtures."""

import hashlib
import secrets

import pytest
from httpx import ASGITransport, AsyncClient

from src.config import settings
from src.database import create_engine_from_url, get_connection, get_db_path, init_db
from src.main import app


@pytest.fixture
async def client():
    """Async test client for FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
async def _init_test_db(tmp_path):
    """Initialise a temporary test database for each test."""
    db_file = str(tmp_path / "test.db")
    original_url = settings.database_url
    original_upload = settings.upload_dir

    test_url = f"sqlite+aiosqlite:///{db_file}"
    settings.database_url = test_url
    settings.upload_dir = str(tmp_path / "uploads")

    import os
    os.makedirs(settings.upload_dir, exist_ok=True)

    # Initialise schema via raw migrations
    await init_db(db_file)

    # Wire up SQLAlchemy engine so ORM services work in tests
    create_engine_from_url(test_url)

    yield

    settings.database_url = original_url
    settings.upload_dir = original_upload


@pytest.fixture
async def db_with_api_key():
    """Create a workspace with a valid API key."""
    import uuid
    from datetime import datetime

    workspace_id = str(uuid.uuid4())
    raw_key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    db = await get_connection(get_db_path(settings.database_url))
    try:
        await db.execute(
            "INSERT INTO workspaces (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (workspace_id, f"test-ws-{workspace_id[:8]}", now, now),
        )
        await db.execute(
            """INSERT INTO api_keys (id, workspace_id, name, key_hash, key_prefix, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (key_id, workspace_id, "test-key", key_hash, raw_key[:8], now),
        )
        await db.commit()
    finally:
        await db.close()

    return workspace_id, raw_key


@pytest.fixture
async def db_with_revoked_api_key():
    """Create a workspace with a revoked API key."""
    import uuid
    from datetime import datetime

    workspace_id = str(uuid.uuid4())
    raw_key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    db = await get_connection(get_db_path(settings.database_url))
    try:
        await db.execute(
            "INSERT INTO workspaces (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (workspace_id, f"test-ws-{workspace_id[:8]}", now, now),
        )
        await db.execute(
            """INSERT INTO api_keys (id, workspace_id, name, key_hash, key_prefix, is_active, created_at)
               VALUES (?, ?, ?, ?, ?, 0, ?)""",
            (key_id, workspace_id, "revoked-key", key_hash, raw_key[:8], now),
        )
        await db.commit()
    finally:
        await db.close()

    return workspace_id, raw_key


@pytest.fixture
async def db_workspace():
    """Create a test workspace."""
    import uuid
    from datetime import datetime

    workspace_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    db = await get_connection(get_db_path(settings.database_url))
    try:
        await db.execute(
            "INSERT INTO workspaces (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (workspace_id, f"test-ws-{workspace_id[:8]}", now, now),
        )
        await db.commit()
    finally:
        await db.close()

    return workspace_id
