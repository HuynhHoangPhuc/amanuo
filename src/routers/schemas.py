"""Schema CRUD endpoints with versioning support — SQLAlchemy ORM."""

import importlib
import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy import select, update, delete

from src.database import get_session_factory
from src.schemas import ExtractionSchema, SchemaField, SchemaValidationError, validate_or_raise

_api = importlib.import_module("src.models.api-models")
_schema_orm_mod = importlib.import_module("src.models.schema-orm")
SchemaORM = _schema_orm_mod.SchemaORM
SchemaVersionORM = _schema_orm_mod.SchemaVersionORM

_auth = importlib.import_module("src.middleware.auth-middleware")
_versioning = importlib.import_module("src.schemas.schema-versioning")
_migration = importlib.import_module("src.schemas.schema-migration")

router = APIRouter(prefix="/schemas", tags=["schemas"])


def _get_session():
    return get_session_factory()()


@router.get("", response_model=list[_api.SchemaResponse])
async def list_schemas(workspace_id: str = Depends(_auth.get_workspace_id)):
    """List all saved schemas for the workspace."""
    async with _get_session() as session:
        result = await session.execute(
            select(SchemaORM)
            .where(SchemaORM.workspace_id == workspace_id)
            .order_by(SchemaORM.created_at.desc())
        )
        rows = result.scalars().all()
        return [
            _api.SchemaResponse(
                id=r.id, name=r.name,
                fields=[SchemaField(**f) for f in json.loads(r.fields)],
                created_at=r.created_at, updated_at=r.updated_at,
            )
            for r in rows
        ]


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

    schema_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    fields_json = json.dumps([f.model_dump() for f in schema.fields])

    try:
        async with _get_session() as session:
            orm = SchemaORM(
                id=schema_id, name=req.name, fields=fields_json,
                created_at=now, updated_at=now,
                workspace_id=workspace_id, current_version="1.0.0",
            )
            session.add(orm)

            version_id = str(uuid.uuid4())
            ver = SchemaVersionORM(
                id=version_id, schema_id=schema_id, version="1.0.0",
                fields=fields_json, changelog="Initial version", created_at=now,
            )
            session.add(ver)
            await session.commit()
    except Exception as e:
        if "UNIQUE constraint" in str(e):
            raise HTTPException(409, f"Schema with name '{req.name}' already exists")
        raise

    return _api.SchemaResponse(
        id=schema_id, name=req.name, fields=schema.fields,
        version="1.0.0", created_at=now, updated_at=now,
    )


@router.put("/{schema_id}", response_model=_api.SchemaResponse)
async def update_schema(
    schema_id: str,
    req: _api.SchemaCreateRequest,
    workspace_id: str = Depends(_auth.get_workspace_id),
):
    """Update schema fields. Auto-assigns semver based on diff."""
    async with _get_session() as session:
        result = await session.execute(
            select(SchemaORM).where(SchemaORM.id == schema_id, SchemaORM.workspace_id == workspace_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(404, f"Schema {schema_id} not found")

        old_fields = json.loads(row.fields)
        new_fields = [f.model_dump() for f in req.fields]
        current_version = row.current_version or "1.0.0"

        next_version = _versioning.compute_next_version(old_fields, new_fields, current_version)
        warnings = _migration.validate_migration(old_fields, new_fields)

        now = datetime.now().isoformat()
        new_fields_json = json.dumps(new_fields)

        await session.execute(
            update(SchemaORM)
            .where(SchemaORM.id == schema_id)
            .values(fields=new_fields_json, current_version=next_version, updated_at=now)
        )

        if next_version != current_version:
            version_id = str(uuid.uuid4())
            changelog = "; ".join(warnings) if warnings else f"Updated to {next_version}"
            ver = SchemaVersionORM(
                id=version_id, schema_id=schema_id, version=next_version,
                fields=new_fields_json, changelog=changelog, created_at=now,
            )
            session.add(ver)

        await session.commit()

    return _api.SchemaResponse(
        id=schema_id, name=req.name,
        fields=[SchemaField(**f) for f in new_fields],
        version=next_version, created_at=row.created_at, updated_at=now,
    )


@router.get("/{schema_id}/versions")
async def get_schema_versions(
    schema_id: str,
    workspace_id: str = Depends(_auth.get_workspace_id),
):
    """Get version history for a schema."""
    async with _get_session() as session:
        owns = await session.execute(
            select(SchemaORM).where(SchemaORM.id == schema_id, SchemaORM.workspace_id == workspace_id)
        )
        if not owns.scalar_one_or_none():
            raise HTTPException(404, f"Schema {schema_id} not found")

        result = await session.execute(
            select(SchemaVersionORM)
            .where(SchemaVersionORM.schema_id == schema_id)
            .order_by(SchemaVersionORM.created_at.desc())
        )
        rows = result.scalars().all()
        return [
            {
                "id": r.id, "version": r.version,
                "fields": json.loads(r.fields),
                "changelog": r.changelog, "created_at": r.created_at,
            }
            for r in rows
        ]


@router.post("/suggest", response_model=_api.SuggestSchemaResponse)
async def suggest_schema(
    file: UploadFile,
    lang: str = Query("en", description="Document language code (en, ja, vi)"),
    workspace_id: str = Depends(_auth.get_workspace_id),
):
    """Upload a document image and get AI-suggested extraction fields.

    BETA: Always verify suggested fields before saving as a schema.
    Returns empty fields list if VLM is unavailable (graceful degradation).
    """
    content = await file.read()
    _suggest_svc = importlib.import_module("src.services.schema-suggest-service")
    fields = await _suggest_svc.suggest_schema_fields(content, lang)
    return _api.SuggestSchemaResponse(
        fields=[_api.SuggestedField(**f) for f in fields],
        warning="AI-suggested fields — please verify accuracy before saving as a schema.",
        beta=True,
    )


@router.delete("/{schema_id}")
async def delete_schema(
    schema_id: str,
    workspace_id: str = Depends(_auth.get_workspace_id),
):
    """Delete a saved schema by ID."""
    async with _get_session() as session:
        # Delete version snapshots first (FK constraint)
        await session.execute(
            delete(SchemaVersionORM).where(SchemaVersionORM.schema_id == schema_id)
        )
        result = await session.execute(
            delete(SchemaORM).where(SchemaORM.id == schema_id, SchemaORM.workspace_id == workspace_id)
        )
        await session.commit()
        if result.rowcount == 0:
            raise HTTPException(404, f"Schema {schema_id} not found")
        return {"deleted": True}
