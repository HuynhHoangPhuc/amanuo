"""Schema CRUD endpoints."""

import importlib

from fastapi import APIRouter, HTTPException

from src.config import settings
from src.database import get_connection, get_db_path
from src.schemas import ExtractionSchema, SchemaValidationError, validate_or_raise

_api = importlib.import_module("src.models.api-models")
_store = importlib.import_module("src.schemas.schema-store")

router = APIRouter(prefix="/schemas", tags=["schemas"])


async def _get_db():
    return await get_connection(get_db_path(settings.database_url))


@router.get("", response_model=list[_api.SchemaResponse])
async def list_schemas():
    """List all saved schemas."""
    db = await _get_db()
    try:
        schemas = await _store.list_schemas(db)
        return [
            _api.SchemaResponse(
                id=s.id, name=s.name, fields=s.fields,
                created_at=s.created_at, updated_at=s.updated_at,
            )
            for s in schemas
        ]
    finally:
        await db.close()


@router.post("", response_model=_api.SchemaResponse, status_code=201)
async def create_schema(req: _api.SchemaCreateRequest):
    """Create and save a new extraction schema."""
    schema = ExtractionSchema(fields=req.fields, name=req.name)
    try:
        validate_or_raise(schema)
    except SchemaValidationError as e:
        raise HTTPException(400, f"Schema validation failed: {e.errors}")

    db = await _get_db()
    try:
        saved = await _store.save_schema(db, req.name, schema)
        return _api.SchemaResponse(
            id=saved.id, name=saved.name, fields=saved.fields,
            created_at=saved.created_at, updated_at=saved.updated_at,
        )
    except Exception as e:
        if "UNIQUE constraint" in str(e):
            raise HTTPException(409, f"Schema with name '{req.name}' already exists")
        raise
    finally:
        await db.close()


@router.delete("/{schema_id}")
async def delete_schema(schema_id: str):
    """Delete a saved schema by ID."""
    db = await _get_db()
    try:
        deleted = await _store.delete_schema(db, schema_id)
        if not deleted:
            raise HTTPException(404, f"Schema {schema_id} not found")
        return {"deleted": True}
    finally:
        await db.close()
