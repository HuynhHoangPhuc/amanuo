"""Pipeline CRUD endpoints — workspace-scoped pipeline configuration management."""

import importlib
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from src.config import settings
from src.database import get_connection, get_db_path
from src.models.pipeline import PipelineCreateRequest, PipelineResponse, PipelineUpdateRequest

_auth = importlib.import_module("src.middleware.auth-middleware")
_pipeline_config = importlib.import_module("src.engine.pipeline-config")

get_workspace_id = _auth.get_workspace_id

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


async def _get_db():
    return await get_connection(get_db_path(settings.database_url))


def _row_to_response(row) -> PipelineResponse:
    """Convert a SQLite Row to a PipelineResponse model."""
    return PipelineResponse(
        id=row["id"],
        workspace_id=row["workspace_id"],
        name=row["name"],
        description=row["description"],
        config=row["config"],
        is_active=bool(row["is_active"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.post("", response_model=PipelineResponse, status_code=201)
async def create_pipeline(
    req: PipelineCreateRequest,
    workspace_id: str = Depends(get_workspace_id),
):
    """Create a new pipeline for the current workspace.

    Validates the YAML config before persisting. Returns 400 if YAML is invalid,
    409 if a pipeline with the same name already exists in this workspace.
    """
    # Validate YAML before saving
    try:
        config = _pipeline_config.parse_pipeline_yaml(req.config)
    except (ValueError, Exception) as exc:
        raise HTTPException(400, f"Invalid pipeline config: {exc}") from exc

    warnings = _pipeline_config.validate_pipeline(config)
    if warnings:
        # Log warnings but don't block creation — unknown step types are caught here
        import logging
        logging.getLogger(__name__).warning("Pipeline warnings: %s", warnings)

    pipeline_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    db = await _get_db()
    try:
        await db.execute(
            """INSERT INTO pipelines (id, workspace_id, name, description, config, is_active, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, 1, ?, ?)""",
            (pipeline_id, workspace_id, req.name, req.description, req.config, now, now),
        )
        await db.commit()

        cursor = await db.execute(
            "SELECT * FROM pipelines WHERE id = ?", (pipeline_id,)
        )
        row = await cursor.fetchone()
        return _row_to_response(row)
    except Exception as exc:
        if "UNIQUE constraint" in str(exc):
            raise HTTPException(
                409, f"Pipeline '{req.name}' already exists in this workspace"
            ) from exc
        raise
    finally:
        await db.close()


@router.get("", response_model=list[PipelineResponse])
async def list_pipelines(workspace_id: str = Depends(get_workspace_id)):
    """List all active pipelines for the current workspace."""
    db = await _get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM pipelines WHERE workspace_id = ? AND is_active = 1 ORDER BY created_at DESC",
            (workspace_id,),
        )
        rows = await cursor.fetchall()
        return [_row_to_response(r) for r in rows]
    finally:
        await db.close()


@router.get("/{pipeline_id}", response_model=PipelineResponse)
async def get_pipeline(
    pipeline_id: str,
    workspace_id: str = Depends(get_workspace_id),
):
    """Get a single pipeline by ID (must belong to the current workspace)."""
    db = await _get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM pipelines WHERE id = ? AND workspace_id = ?",
            (pipeline_id, workspace_id),
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(404, f"Pipeline {pipeline_id} not found")
        return _row_to_response(row)
    finally:
        await db.close()


@router.put("/{pipeline_id}", response_model=PipelineResponse)
async def update_pipeline(
    pipeline_id: str,
    req: PipelineUpdateRequest,
    workspace_id: str = Depends(get_workspace_id),
):
    """Update pipeline name, description, and/or config YAML.

    Only provided fields are updated. Returns 400 if the new YAML is invalid,
    404 if the pipeline doesn't exist in this workspace.
    """
    db = await _get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM pipelines WHERE id = ? AND workspace_id = ?",
            (pipeline_id, workspace_id),
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(404, f"Pipeline {pipeline_id} not found")

        # Validate new config if provided
        if req.config is not None:
            try:
                _pipeline_config.parse_pipeline_yaml(req.config)
            except (ValueError, Exception) as exc:
                raise HTTPException(400, f"Invalid pipeline config: {exc}") from exc

        now = datetime.now().isoformat()
        new_name = req.name if req.name is not None else row["name"]
        new_description = req.description if req.description is not None else row["description"]
        new_config = req.config if req.config is not None else row["config"]

        await db.execute(
            """UPDATE pipelines SET name = ?, description = ?, config = ?, updated_at = ?
               WHERE id = ? AND workspace_id = ?""",
            (new_name, new_description, new_config, now, pipeline_id, workspace_id),
        )
        await db.commit()

        cursor = await db.execute(
            "SELECT * FROM pipelines WHERE id = ?", (pipeline_id,)
        )
        updated = await cursor.fetchone()
        return _row_to_response(updated)
    finally:
        await db.close()


@router.delete("/{pipeline_id}")
async def deactivate_pipeline(
    pipeline_id: str,
    workspace_id: str = Depends(get_workspace_id),
):
    """Deactivate a pipeline (soft delete — sets is_active = 0).

    Returns 404 if the pipeline doesn't exist in this workspace.
    """
    db = await _get_db()
    try:
        cursor = await db.execute(
            "SELECT id FROM pipelines WHERE id = ? AND workspace_id = ?",
            (pipeline_id, workspace_id),
        )
        if not await cursor.fetchone():
            raise HTTPException(404, f"Pipeline {pipeline_id} not found")

        now = datetime.now().isoformat()
        await db.execute(
            "UPDATE pipelines SET is_active = 0, updated_at = ? WHERE id = ? AND workspace_id = ?",
            (now, pipeline_id, workspace_id),
        )
        await db.commit()
        return {"deactivated": True, "id": pipeline_id}
    finally:
        await db.close()
