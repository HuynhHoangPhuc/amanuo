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


@pytest.fixture
async def db_with_users_and_roles():
    """Create a workspace with admin + 3 reviewers + 1 approver, all with roles."""
    import uuid
    from datetime import datetime

    import bcrypt

    workspace_id = str(uuid.uuid4())
    raw_key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    password_hash = bcrypt.hashpw(b"testpass123", bcrypt.gensalt(rounds=4)).decode()

    admin_id = str(uuid.uuid4())
    reviewer_ids = [str(uuid.uuid4()) for _ in range(3)]
    approver_id = str(uuid.uuid4())

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

        # Create users
        users = [(admin_id, "admin@test.com", "admin")] + \
                [(rid, f"reviewer{i}@test.com", "reviewer") for i, rid in enumerate(reviewer_ids)] + \
                [(approver_id, "approver@test.com", "approver")]

        for uid, email, _role in users:
            await db.execute(
                """INSERT INTO users (id, email, password_hash, workspace_id, is_active, created_at, updated_at)
                   VALUES (?, ?, ?, ?, 1, ?, ?)""",
                (uid, email, password_hash, workspace_id, now, now),
            )
            await db.execute(
                """INSERT INTO role_assignments (id, user_id, workspace_id, role, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), uid, workspace_id, _role, now),
            )

        # Give admin the admin role
        await db.execute(
            """INSERT OR IGNORE INTO role_assignments (id, user_id, workspace_id, role, created_at)
               VALUES (?, ?, ?, 'member', ?)""",
            (str(uuid.uuid4()), admin_id, workspace_id, now),
        )

        await db.commit()
    finally:
        await db.close()

    return {
        "workspace_id": workspace_id,
        "api_key": raw_key,
        "admin_id": admin_id,
        "reviewer_ids": reviewer_ids,
        "approver_id": approver_id,
        "password": "testpass123",
    }


@pytest.fixture
async def db_with_analytics_jobs():
    """Create a workspace with API key + 24 varied jobs for analytics testing."""
    import uuid
    import hashlib
    import secrets
    from datetime import datetime, timedelta

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
            (workspace_id, f"analytics-ws-{workspace_id[:8]}", now_iso, now_iso),
        )
        await db.execute(
            """INSERT INTO api_keys (id, workspace_id, name, key_hash, key_prefix, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (key_id, workspace_id, "analytics-key", key_hash, raw_key[:8], now_iso),
        )

        # Insert 24 jobs with varied provider, status, cost, and date spread
        providers = ["gemini", "mistral", None]
        statuses = ["completed", "failed", "pending_review"]
        costs = [0.001, 0.01, 0.05, 0.0]

        for i in range(24):
            job_id = str(uuid.uuid4())
            provider = providers[i % 3]
            mode = "cloud" if provider else "local_only"
            status = statuses[i % 3]
            cost = costs[i % 4]
            job_date = (now - timedelta(days=i % 20)).isoformat()
            completed_at = (now - timedelta(days=i % 20, seconds=30)).isoformat() if status == "completed" else None
            confidence = 0.85 + (i % 10) * 0.01 if status == "completed" else None

            await db.execute(
                """INSERT INTO jobs (
                    id, workspace_id, status, mode, cloud_provider,
                    cost_estimated_usd, cost_input_tokens, cost_output_tokens,
                    confidence, created_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    job_id, workspace_id, status, mode, provider,
                    cost, int(cost * 10000), int(cost * 5000),
                    confidence, job_date, completed_at,
                ),
            )

        await db.commit()
    finally:
        await db.close()

    return workspace_id, raw_key
