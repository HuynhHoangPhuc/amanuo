"""E2E test fixtures with database initialization."""

import os

import pytest
from httpx import ASGITransport, AsyncClient

from src.config import settings
from src.database import init_db
from src.main import app


@pytest.fixture(autouse=True)
async def _init_test_db(tmp_path):
    """Initialize a temporary test database for each E2E test."""
    db_file = str(tmp_path / "test.db")
    original_url = settings.database_url
    original_upload = settings.upload_dir

    settings.database_url = f"sqlite+aiosqlite:///{db_file}"
    settings.upload_dir = str(tmp_path / "uploads")
    os.makedirs(settings.upload_dir, exist_ok=True)

    await init_db(db_file)
    yield
    settings.database_url = original_url
    settings.upload_dir = original_upload


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
