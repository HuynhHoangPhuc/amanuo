"""Schema CRUD endpoints with versioning support."""

import importlib
import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from src.config import settings
from src.database import get_connection, get_db_path
from src.schemas import ExtractionSchema, SchemaField, SchemaValidationError, validate_or_raise

_api = importlib.import_module("src.models.api-models")
_store = importlib.import_module("src.schemas.schema-store")
_auth = importlib.import_module("src.middleware.auth-middleware")
_versioning = importlib.import_module("src.schemas.schema-versioning")
_migration = importlib.import_module("src.schemas.schema-migration")

router = APIRouter(prefix="/schemas", tags=["schemas"])


async def _get_db():
    return await get_connection(get_db_path(settings.database_url))


@router.get("", response_model=list[_api.SchemaResponse])
async def list_schemas(workspace_id: str = Depends(_auth.get_workspace_id)):
    """List all saved schemas for the workspace."""
    db = await _get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM schemas WHERE workspace_id = ? ORDER BY created_at DESC",
            (workspace_id,),
        )
        rows = await cursor.fetchall()
        return [
            _api.SchemaResponse(
                id=r["id"], name=r["name"],
                fields=[SchemaField(**f) for f in json.loads(r["fields"])],
                created_at=r["created_at"], updated_at=r["updated_at"],
            )
            for r in rows
        ]
    finally:
        await db.close()


@router.post("", response_model=_api.SchemaResponse, status_code=201)
async def create_schema(
    req: _api.SchemaCreateRequest,
    workspace_id: str = Depends(_auth.get_workspace_id),
):
    """Create and save a new extraction schema."""
    schema = ExtractionSchema(fields=req.fields, name=req.name)
    try:
        validate_or_raise(schema)
    except SchemaValidationError as e:
        raise HTTPException(400, f"Schema validation failed: {e.errors}")

    db = await _get_db()
    try:
        # Save schema with workspace_id and initial version
        schema_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        fields_json = json.dumps([f.model_dump() for f in schema.fields])

        await db.execute(
            """INSERT INTO schemas (id, name, fields, created_at, updated_at, workspace_id, current_version)
               VALUES (?, ?, ?, ?, ?, ?, '1.0.0')""",
            (schema_id, req.name, fields_json, now, now, workspace_id),
        )

        # Create initial version snapshot
        version_id = str(uuid.uuid4())
        await db.execute(
            """INSERT INTO schema_versions (id, schema_id, version, fields, changelog, created_at)
               VALUES (?, ?, '1.0.0', ?, 'Initial version', ?)""",
            (version_id, schema_id, fields_json, now),
        )
        await db.commit()

        return _api.SchemaResponse(
            id=schema_id, name=req.name, fields=schema.fields,
            version="1.0.0", created_at=now, updated_at=now,
        )
    except Exception as e:
        if "UNIQUE constraint" in str(e):
            raise HTTPException(409, f"Schema with name '{req.name}' already exists")
        raise
    finally:
        await db.close()


@router.put("/{schema_id}", response_model=_api.SchemaResponse)
async def update_schema(
    schema_id: str,
    req: _api.SchemaCreateRequest,
    workspace_id: str = Depends(_auth.get_workspace_id),
):
    """Update schema fields. Auto-assigns semver based on diff."""
    db = await _get_db()
    try:
        # Load current schema
        cursor = await db.execute(
            "SELECT * FROM schemas WHERE id = ? AND workspace_id = ?",
            (schema_id, workspace_id),
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(404, f"Schema {schema_id} not found")

        old_fields = json.loads(row["fields"])
        new_fields = [f.model_dump() for f in req.fields]
        current_version = row["current_version"] or "1.0.0"

        # Compute version bump
        next_version = _versioning.compute_next_version(old_fields, new_fields, current_version)
        warnings = _migration.validate_migration(old_fields, new_fields)

        now = datetime.now().isoformat()
        new_fields_json = json.dumps(new_fields)

        # Update schema
        await db.execute(
            "UPDATE schemas SET fields = ?, current_version = ?, updated_at = ? WHERE id = ?",
            (new_fields_json, next_version, now, schema_id),
        )

        # Create version snapshot (only if version actually changed)
        if next_version != current_version:
            version_id = str(uuid.uuid4())
            changelog = "; ".join(warnings) if warnings else f"Updated to {next_version}"
            await db.execute(
                """INSERT INTO schema_versions (id, schema_id, version, fields, changelog, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (version_id, schema_id, next_version, new_fields_json, changelog, now),
            )

        await db.commit()

        return _api.SchemaResponse(
            id=schema_id, name=req.name,
            fields=[SchemaField(**f) for f in new_fields],
            version=next_version, created_at=row["created_at"], updated_at=now,
        )
    finally:
        await db.close()


@router.get("/{schema_id}/versions")
async def get_schema_versions(
    schema_id: str,
    workspace_id: str = Depends(_auth.get_workspace_id),
):
    """Get version history for a schema."""
    db = await _get_db()
    try:
        # Verify ownership
        cursor = await db.execute(
            "SELECT id FROM schemas WHERE id = ? AND workspace_id = ?",
            (schema_id, workspace_id),
        )
        if not await cursor.fetchone():
            raise HTTPException(404, f"Schema {schema_id} not found")

        cursor = await db.execute(
            "SELECT * FROM schema_versions WHERE schema_id = ? ORDER BY created_at DESC",
            (schema_id,),
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": r["id"], "version": r["version"],
                "fields": json.loads(r["fields"]),
                "changelog": r["changelog"], "created_at": r["created_at"],
            }
            for r in rows
        ]
    finally:
        await db.close()


@router.delete("/{schema_id}")
async def delete_schema(
    schema_id: str,
    workspace_id: str = Depends(_auth.get_workspace_id),
):
    """Delete a saved schema by ID."""
    db = await _get_db()
    try:
        # Delete version snapshots first (FK constraint)
        await db.execute("DELETE FROM schema_versions WHERE schema_id = ?", (schema_id,))
        cursor = await db.execute(
            "DELETE FROM schemas WHERE id = ? AND workspace_id = ?",
            (schema_id, workspace_id),
        )
        await db.commit()
        if cursor.rowcount == 0:
            raise HTTPException(404, f"Schema {schema_id} not found")
        return {"deleted": True}
    finally:
        await db.close()
