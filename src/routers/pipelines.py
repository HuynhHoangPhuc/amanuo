"""Pipeline CRUD endpoints — workspace-scoped pipeline configuration management."""

import importlib
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update

from src.database import get_session_factory
from src.models.pipeline import PipelineORM, PipelineCreateRequest, PipelineResponse, PipelineUpdateRequest

_auth = importlib.import_module("src.middleware.auth-middleware")
_pipeline_config = importlib.import_module("src.engine.pipeline-config")

get_workspace_id = _auth.get_workspace_id

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


def _get_session():
    return get_session_factory()()


def _orm_to_response(row: PipelineORM) -> PipelineResponse:
    return PipelineResponse(
        id=row.id,
        workspace_id=row.workspace_id,
        name=row.name,
        description=row.description,
        config=row.config,
        is_active=bool(row.is_active),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.post("", response_model=PipelineResponse, status_code=201)
async def create_pipeline(
    req: PipelineCreateRequest,
    workspace_id: str = Depends(get_workspace_id),
):
    """Create a new pipeline. Validates YAML before persisting."""
    try:
        config = _pipeline_config.parse_pipeline_yaml(req.config)
    except (ValueError, Exception) as exc:
        raise HTTPException(400, f"Invalid pipeline config: {exc}") from exc

    warnings = _pipeline_config.validate_pipeline(config)
    if warnings:
        import logging
        logging.getLogger(__name__).warning("Pipeline warnings: %s", warnings)

    pipeline_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    try:
        async with _get_session() as session:
            pipeline = PipelineORM(
                id=pipeline_id,
                workspace_id=workspace_id,
                name=req.name,
                description=req.description,
                config=req.config,
                is_active=1,
                created_at=now,
                updated_at=now,
            )
            session.add(pipeline)
            await session.commit()
            await session.refresh(pipeline)
            return _orm_to_response(pipeline)
    except Exception as exc:
        if "UNIQUE constraint" in str(exc):
            raise HTTPException(409, f"Pipeline '{req.name}' already exists in this workspace") from exc
        raise


@router.get("", response_model=list[PipelineResponse])
async def list_pipelines(workspace_id: str = Depends(get_workspace_id)):
    """List all active pipelines for the current workspace."""
    async with _get_session() as session:
        result = await session.execute(
            select(PipelineORM)
            .where(PipelineORM.workspace_id == workspace_id, PipelineORM.is_active == 1)
            .order_by(PipelineORM.created_at.desc())
        )
        rows = result.scalars().all()
        return [_orm_to_response(r) for r in rows]


@router.get("/{pipeline_id}", response_model=PipelineResponse)
async def get_pipeline(
    pipeline_id: str,
    workspace_id: str = Depends(get_workspace_id),
):
    """Get a single pipeline by ID (must belong to the current workspace)."""
    async with _get_session() as session:
        result = await session.execute(
            select(PipelineORM).where(
                PipelineORM.id == pipeline_id, PipelineORM.workspace_id == workspace_id
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(404, f"Pipeline {pipeline_id} not found")
        return _orm_to_response(row)


@router.put("/{pipeline_id}", response_model=PipelineResponse)
async def update_pipeline(
    pipeline_id: str,
    req: PipelineUpdateRequest,
    workspace_id: str = Depends(get_workspace_id),
):
    """Update pipeline name, description, and/or config YAML."""
    if req.config is not None:
        try:
            _pipeline_config.parse_pipeline_yaml(req.config)
        except (ValueError, Exception) as exc:
            raise HTTPException(400, f"Invalid pipeline config: {exc}") from exc

    async with _get_session() as session:
        result = await session.execute(
            select(PipelineORM).where(
                PipelineORM.id == pipeline_id, PipelineORM.workspace_id == workspace_id
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(404, f"Pipeline {pipeline_id} not found")

        now = datetime.now().isoformat()
        values = {"updated_at": now}
        if req.name is not None:
            values["name"] = req.name
        if req.description is not None:
            values["description"] = req.description
        if req.config is not None:
            values["config"] = req.config

        await session.execute(
            update(PipelineORM).where(PipelineORM.id == pipeline_id).values(**values)
        )
        await session.commit()

        # Reload updated row
        result = await session.execute(
            select(PipelineORM).where(PipelineORM.id == pipeline_id)
        )
        updated = result.scalar_one()
        return _orm_to_response(updated)


@router.delete("/{pipeline_id}")
async def deactivate_pipeline(
    pipeline_id: str,
    workspace_id: str = Depends(get_workspace_id),
):
    """Soft-delete a pipeline (sets is_active = 0)."""
    async with _get_session() as session:
        result = await session.execute(
            select(PipelineORM).where(
                PipelineORM.id == pipeline_id, PipelineORM.workspace_id == workspace_id
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(404, f"Pipeline {pipeline_id} not found")

        now = datetime.now().isoformat()
        await session.execute(
            update(PipelineORM)
            .where(PipelineORM.id == pipeline_id, PipelineORM.workspace_id == workspace_id)
            .values(is_active=0, updated_at=now)
        )
        await session.commit()
        return {"deactivated": True, "id": pipeline_id}
