"""Template marketplace API endpoints.

Mount in main.py:
    _templates_router = importlib.import_module("src.routers.templates")
    app.include_router(_templates_router.router)
"""

import importlib

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session

_auth = importlib.import_module("src.middleware.auth-middleware")
_template_svc = importlib.import_module("src.services.template-service")

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("")
async def list_templates(
    category: str | None = Query(None, description="Filter by category (invoice, receipt, identity, medical)"),
    lang: str | None = Query(None, description="Filter by language code (en, ja, vi)"),
    search: str | None = Query(None, description="Search by template name"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    """List curated and workspace templates with optional filtering."""
    templates = await _template_svc.list_templates(
        session, category=category, lang=lang, search=search, limit=limit, offset=offset
    )
    return {"templates": templates, "total": len(templates)}


@router.get("/{template_id}")
async def get_template(
    template_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get a single template by ID."""
    template = await _template_svc.get_template(session, template_id)
    if not template:
        raise HTTPException(404, f"Template {template_id} not found")
    return template


@router.post("/{template_id}/import", status_code=200)
async def import_template(
    template_id: str,
    session: AsyncSession = Depends(get_session),
    workspace_id: str = Depends(_auth.get_workspace_id),
):
    """Clone a template into the workspace as an importable field set.

    Returns template fields ready for use in schema creation.
    Also increments usage_count on the source template.
    """
    try:
        result = await _template_svc.import_template(session, template_id, workspace_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return result
