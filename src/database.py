"""Async SQLite database setup and connection management."""

import hashlib
import secrets

import aiosqlite

# Default DB path (extracted from sqlite+aiosqlite:///./amanuo.db)
_DB_PATH = "amanuo.db"

_SCHEMA_VERSION = 2

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
        # -- Workspaces --
        """
        CREATE TABLE IF NOT EXISTS workspaces (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """,
        # -- Users (for session auth in Phase 2) --
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
        # -- API Keys --
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
        # -- Pipelines (YAML config stored as TEXT) --
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
        # -- Batches --
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
        # -- Batch Items (link batch -> job) --
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
        # -- Webhooks --
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
        # -- Webhook Deliveries (audit log) --
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
        # -- Schema Versions --
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
        # -- Add workspace_id + batch_id + pipeline_id to jobs --
        "ALTER TABLE jobs ADD COLUMN workspace_id TEXT REFERENCES workspaces(id)",
        "ALTER TABLE jobs ADD COLUMN batch_id TEXT REFERENCES batches(id)",
        "ALTER TABLE jobs ADD COLUMN pipeline_id TEXT REFERENCES pipelines(id)",
        # -- Add workspace_id + current_version to schemas --
        "ALTER TABLE schemas ADD COLUMN workspace_id TEXT REFERENCES workspaces(id)",
        "ALTER TABLE schemas ADD COLUMN current_version TEXT DEFAULT '1.0.0'",
    ],
}

# Post-migration seed SQL (run after migration 2 is applied)
_SEED_DEFAULT_WORKSPACE = """
    INSERT OR IGNORE INTO workspaces (id, name, created_at, updated_at)
    VALUES ('default', 'Default Workspace', datetime('now'), datetime('now'))
"""

_BACKFILL_JOBS = "UPDATE jobs SET workspace_id = 'default' WHERE workspace_id IS NULL"
_BACKFILL_SCHEMAS = "UPDATE schemas SET workspace_id = 'default' WHERE workspace_id IS NULL"

# Indexes for frequently queried columns
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
]


def get_db_path(database_url: str) -> str:
    """Extract file path from sqlite URL."""
    # "sqlite+aiosqlite:///./amanuo.db" -> "./amanuo.db"
    prefix = "sqlite+aiosqlite:///"
    if database_url.startswith(prefix):
        return database_url[len(prefix):]
    return _DB_PATH


async def get_connection(db_path: str = _DB_PATH) -> aiosqlite.Connection:
    """Get a database connection with WAL mode enabled."""
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db(db_path: str = _DB_PATH) -> None:
    """Run migrations to initialize/update the database schema."""
    db = await get_connection(db_path)
    try:
        # Check current version
        current_version = 0
        try:
            cursor = await db.execute("SELECT MAX(version) FROM schema_version")
            row = await cursor.fetchone()
            if row and row[0] is not None:
                current_version = row[0]
        except aiosqlite.OperationalError:
            pass  # Table doesn't exist yet

        # Apply pending migrations
        for version in sorted(_MIGRATIONS.keys()):
            if version > current_version:
                for sql in _MIGRATIONS[version]:
                    await db.execute(sql)
                await db.execute(
                    "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
                    (version,),
                )

        # Post-migration seeding and backfill (idempotent)
        if current_version < 2:
            await db.execute(_SEED_DEFAULT_WORKSPACE)
            await db.execute(_BACKFILL_JOBS)
            await db.execute(_BACKFILL_SCHEMAS)
            for idx_sql in _INDEXES:
                await db.execute(idx_sql)
            # Generate default API key for Gradio UI / backward compat
            await _seed_default_api_key(db)

        await db.commit()
    finally:
        await db.close()


async def _seed_default_api_key(db: aiosqlite.Connection) -> None:
    """Create a default API key for the default workspace if none exists."""
    cursor = await db.execute(
        "SELECT id FROM api_keys WHERE workspace_id = 'default' AND name = 'Default Key'"
    )
    if await cursor.fetchone():
        return  # Already seeded

    raw_key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = raw_key[:8]

    await db.execute(
        """INSERT INTO api_keys (id, workspace_id, name, key_hash, key_prefix, created_at)
           VALUES ('default-key', 'default', 'Default Key', ?, ?, datetime('now'))""",
        (key_hash, key_prefix),
    )

    # Print key to stdout so operator can capture it on first run
    print(f"\n{'='*60}")
    print(f"  DEFAULT API KEY (shown once): {raw_key}")
    print(f"  Prefix: {key_prefix}")
    print(f"{'='*60}\n")
