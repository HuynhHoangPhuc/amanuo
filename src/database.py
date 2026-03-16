"""Database setup: SQLAlchemy async engine + session factory.

Keeps legacy get_connection() / init_db() interface for backward compatibility
with existing test fixtures that use raw aiosqlite SQL.
"""

import hashlib
import importlib
import secrets
from datetime import datetime
from typing import AsyncGenerator

import aiosqlite
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import event, text

# Default DB path
_DB_PATH = "amanuo.db"

# --- SQLAlchemy engine + session factory (module-level singletons) ---

_engine = None
_async_session_factory: async_sessionmaker | None = None


def get_engine():
    return _engine


def create_engine_from_url(database_url: str):
    """Initialise SQLAlchemy engine and session factory from a URL."""
    global _engine, _async_session_factory

    connect_args = {}
    if "sqlite" in database_url:
        connect_args = {"check_same_thread": False}

    _engine = create_async_engine(
        database_url,
        echo=False,
        connect_args=connect_args,
    )

    # Enable WAL mode for SQLite via connection event
    if "sqlite" in database_url:
        @event.listens_for(_engine.sync_engine, "connect")
        def _set_sqlite_pragma(dbapi_conn, _):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    _async_session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields an AsyncSession per request."""
    if _async_session_factory is None:
        raise RuntimeError("Database not initialised. Call create_engine_from_url() first.")
    async with _async_session_factory() as session:
        yield session


def get_session_factory() -> async_sessionmaker:
    """Return the session factory for use outside FastAPI Depends (e.g. workers)."""
    if _async_session_factory is None:
        raise RuntimeError("Database not initialised. Call create_engine_from_url() first.")
    return _async_session_factory


# --- Schema migrations (raw SQL, kept for init_db compatibility) ---

_SCHEMA_VERSION = 3

_MIGRATIONS = {
    1: [
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'pending',
            mode TEXT NOT NULL,
            cloud_provider TEXT,
            schema_fields TEXT,
            schema_id TEXT,
            input_file TEXT,
            result TEXT,
            confidence REAL,
            cost_input_tokens INTEGER,
            cost_output_tokens INTEGER,
            cost_estimated_usd REAL,
            error TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS schemas (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            fields TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY
        )
        """,
    ],
    2: [
        """
        CREATE TABLE IF NOT EXISTS workspaces (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            display_name TEXT,
            workspace_id TEXT NOT NULL REFERENCES workspaces(id),
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS api_keys (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL REFERENCES workspaces(id),
            name TEXT NOT NULL,
            key_hash TEXT NOT NULL UNIQUE,
            key_prefix TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            last_used_at TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS pipelines (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL REFERENCES workspaces(id),
            name TEXT NOT NULL,
            description TEXT,
            config TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(workspace_id, name)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS batches (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL REFERENCES workspaces(id),
            status TEXT NOT NULL DEFAULT 'pending',
            total_items INTEGER NOT NULL DEFAULT 0,
            completed_items INTEGER NOT NULL DEFAULT 0,
            failed_items INTEGER NOT NULL DEFAULT 0,
            pipeline_id TEXT REFERENCES pipelines(id),
            created_at TEXT NOT NULL,
            completed_at TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS batch_items (
            id TEXT PRIMARY KEY,
            batch_id TEXT NOT NULL REFERENCES batches(id),
            job_id TEXT NOT NULL REFERENCES jobs(id),
            item_index INTEGER NOT NULL,
            filename TEXT,
            status TEXT NOT NULL DEFAULT 'pending'
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS webhooks (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL REFERENCES workspaces(id),
            url TEXT NOT NULL,
            events TEXT NOT NULL,
            secret TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS webhook_deliveries (
            id TEXT PRIMARY KEY,
            webhook_id TEXT NOT NULL REFERENCES webhooks(id),
            event_type TEXT NOT NULL,
            payload TEXT NOT NULL,
            response_status INTEGER,
            response_body TEXT,
            attempt INTEGER NOT NULL DEFAULT 1,
            delivered_at TEXT,
            next_retry_at TEXT,
            status TEXT NOT NULL DEFAULT 'pending'
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS schema_versions (
            id TEXT PRIMARY KEY,
            schema_id TEXT NOT NULL REFERENCES schemas(id),
            version TEXT NOT NULL,
            fields TEXT NOT NULL,
            changelog TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(schema_id, version)
        )
        """,
        "ALTER TABLE jobs ADD COLUMN workspace_id TEXT REFERENCES workspaces(id)",
        "ALTER TABLE jobs ADD COLUMN batch_id TEXT REFERENCES batches(id)",
        "ALTER TABLE jobs ADD COLUMN pipeline_id TEXT REFERENCES pipelines(id)",
        "ALTER TABLE schemas ADD COLUMN workspace_id TEXT REFERENCES workspaces(id)",
        "ALTER TABLE schemas ADD COLUMN current_version TEXT DEFAULT '1.0.0'",
    ],
    3: [
        """
        CREATE TABLE IF NOT EXISTS extraction_reviews (
            id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL UNIQUE REFERENCES jobs(id),
            workspace_id TEXT NOT NULL REFERENCES workspaces(id),
            status TEXT NOT NULL,
            original_result TEXT NOT NULL,
            corrected_result TEXT,
            corrections TEXT,
            reviewer_id TEXT,
            review_time_ms INTEGER,
            created_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS accuracy_metrics (
            id TEXT PRIMARY KEY,
            schema_id TEXT NOT NULL REFERENCES schemas(id),
            workspace_id TEXT NOT NULL REFERENCES workspaces(id),
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            total_reviews INTEGER NOT NULL DEFAULT 0,
            approved_count INTEGER NOT NULL DEFAULT 0,
            corrected_count INTEGER NOT NULL DEFAULT 0,
            accuracy_pct REAL NOT NULL DEFAULT 0.0,
            field_accuracy TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        )
        """,
        "ALTER TABLE schemas ADD COLUMN require_review INTEGER NOT NULL DEFAULT 0",
    ],
}

_SEED_DEFAULT_WORKSPACE = """
    INSERT OR IGNORE INTO workspaces (id, name, created_at, updated_at)
    VALUES ('default', 'Default Workspace', datetime('now'), datetime('now'))
"""

_BACKFILL_JOBS = "UPDATE jobs SET workspace_id = 'default' WHERE workspace_id IS NULL"
_BACKFILL_SCHEMAS = "UPDATE schemas SET workspace_id = 'default' WHERE workspace_id IS NULL"

_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_jobs_workspace ON jobs(workspace_id)",
    "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)",
    "CREATE INDEX IF NOT EXISTS idx_jobs_batch ON jobs(batch_id)",
    "CREATE INDEX IF NOT EXISTS idx_schemas_workspace ON schemas(workspace_id)",
    "CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash)",
    "CREATE INDEX IF NOT EXISTS idx_batches_workspace ON batches(workspace_id)",
    "CREATE INDEX IF NOT EXISTS idx_webhooks_workspace ON webhooks(workspace_id)",
    "CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_status ON webhook_deliveries(status)",
    "CREATE INDEX IF NOT EXISTS idx_schema_versions_schema ON schema_versions(schema_id)",
    "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
    "CREATE INDEX IF NOT EXISTS idx_users_workspace ON users(workspace_id)",
    "CREATE INDEX IF NOT EXISTS idx_reviews_job ON extraction_reviews(job_id)",
    "CREATE INDEX IF NOT EXISTS idx_reviews_workspace ON extraction_reviews(workspace_id)",
    "CREATE INDEX IF NOT EXISTS idx_reviews_status ON extraction_reviews(status)",
    "CREATE INDEX IF NOT EXISTS idx_accuracy_schema ON accuracy_metrics(schema_id)",
    "CREATE INDEX IF NOT EXISTS idx_accuracy_workspace ON accuracy_metrics(workspace_id)",
]


def is_sqlite(database_url: str) -> bool:
    """Check if the database URL targets SQLite."""
    return "sqlite" in database_url


async def init_db_postgres() -> None:
    """Initialize PostgreSQL: create all tables via ORM metadata, then seed defaults."""
    from src.models.base import Base
    import src.models.workspace  # noqa: F401
    import src.models.pipeline  # noqa: F401
    import src.models.webhook  # noqa: F401
    import src.models.batch  # noqa: F401
    import src.models.job  # noqa: F401
    importlib.import_module("src.models.schema-orm")
    importlib.import_module("src.models.schema-template")
    importlib.import_module("src.models.extraction-review")
    importlib.import_module("src.models.accuracy-metric")

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await _seed_postgres_defaults()


async def _seed_postgres_defaults() -> None:
    """Seed default workspace and API key for PostgreSQL databases."""
    from sqlalchemy import select
    from src.models.workspace import WorkspaceORM, ApiKeyORM

    async with _async_session_factory() as session:
        now = datetime.utcnow().isoformat()

        result = await session.execute(select(WorkspaceORM).where(WorkspaceORM.id == "default"))
        if not result.scalar_one_or_none():
            session.add(WorkspaceORM(id="default", name="Default Workspace", created_at=now, updated_at=now))
            await session.flush()

        result = await session.execute(
            select(ApiKeyORM).where(ApiKeyORM.workspace_id == "default", ApiKeyORM.name == "Default Key")
        )
        if not result.scalar_one_or_none():
            raw_key = secrets.token_urlsafe(32)
            key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
            session.add(ApiKeyORM(
                id="default-key",
                workspace_id="default",
                name="Default Key",
                key_hash=key_hash,
                key_prefix=raw_key[:8],
                is_active=1,
                created_at=now,
            ))
            print(f"\n{'='*60}")
            print(f"  DEFAULT API KEY (shown once): {raw_key}")
            print(f"  Prefix: {raw_key[:8]}")
            print(f"{'='*60}\n")

        await session.commit()


def get_db_path(database_url: str) -> str:
    """Extract file path from sqlite URL."""
    prefix = "sqlite+aiosqlite:///"
    if database_url.startswith(prefix):
        return database_url[len(prefix):]
    return _DB_PATH


async def get_connection(db_path: str = _DB_PATH) -> aiosqlite.Connection:
    """Get a raw aiosqlite connection (legacy interface for tests and seed helpers)."""
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db(db_path: str = _DB_PATH) -> None:
    """Run migrations to initialise/update the database schema (legacy interface)."""
    db = await get_connection(db_path)
    try:
        current_version = 0
        try:
            cursor = await db.execute("SELECT MAX(version) FROM schema_version")
            row = await cursor.fetchone()
            if row and row[0] is not None:
                current_version = row[0]
        except aiosqlite.OperationalError:
            pass

        for version in sorted(_MIGRATIONS.keys()):
            if version > current_version:
                for sql in _MIGRATIONS[version]:
                    try:
                        await db.execute(sql)
                    except aiosqlite.OperationalError as exc:
                        # Ignore "duplicate column" errors from ALTER TABLE
                        if "duplicate column" not in str(exc).lower():
                            raise
                await db.execute(
                    "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
                    (version,),
                )

        if current_version < 2:
            await db.execute(_SEED_DEFAULT_WORKSPACE)
            await db.execute(_BACKFILL_JOBS)
            await db.execute(_BACKFILL_SCHEMAS)
            await _seed_default_api_key(db)

        # Always ensure indexes exist (idempotent CREATE IF NOT EXISTS)
        for idx_sql in _INDEXES:
            try:
                await db.execute(idx_sql)
            except aiosqlite.OperationalError:
                pass  # Table may not exist yet in edge cases

        await db.commit()
    finally:
        await db.close()

    # Also synchronise the SQLAlchemy engine if it has been initialised so that
    # the same on-disk database is visible to ORM sessions.
    if _engine is not None and "sqlite" in str(_engine.url):
        # Nothing extra needed — the engine and aiosqlite both target the same file.
        pass


async def _seed_default_api_key(db: aiosqlite.Connection) -> None:
    """Create a default API key for the default workspace if none exists."""
    cursor = await db.execute(
        "SELECT id FROM api_keys WHERE workspace_id = 'default' AND name = 'Default Key'"
    )
    if await cursor.fetchone():
        return

    raw_key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = raw_key[:8]

    await db.execute(
        """INSERT INTO api_keys (id, workspace_id, name, key_hash, key_prefix, created_at)
           VALUES ('default-key', 'default', 'Default Key', ?, ?, datetime('now'))""",
        (key_hash, key_prefix),
    )

    print(f"\n{'='*60}")
    print(f"  DEFAULT API KEY (shown once): {raw_key}")
    print(f"  Prefix: {key_prefix}")
    print(f"{'='*60}\n")
