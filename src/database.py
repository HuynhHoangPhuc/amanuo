"""Async SQLite database setup and connection management."""

import aiosqlite

# Default DB path (extracted from sqlite+aiosqlite:///./amanuo.db)
_DB_PATH = "amanuo.db"

_SCHEMA_VERSION = 1

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
}


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

        await db.commit()
    finally:
        await db.close()
