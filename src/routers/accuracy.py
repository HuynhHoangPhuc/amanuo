"""Accuracy metrics API endpoints."""

import importlib

from fastapi import APIRouter, Depends

_accuracy_service = importlib.import_module("src.services.accuracy-service")
_auth = importlib.import_module("src.middleware.auth-middleware")

router = APIRouter(prefix="/accuracy", tags=["accuracy"])


@router.get("/{schema_id}")
async def get_accuracy(
    schema_id: str,
    days: int = 30,
    workspace_id: str = Depends(_auth.get_workspace_id),
):
    """Get accuracy metrics history for a schema."""
    return await _accuracy_service.get_metrics(
        workspace_id=workspace_id,
        schema_id=schema_id,
        limit=days,
    )


@router.get("/{schema_id}/fields")
async def get_field_accuracy(
    schema_id: str,
    workspace_id: str = Depends(_auth.get_workspace_id),
):
    """Get current field-level accuracy breakdown."""
    return await _accuracy_service.compute_accuracy(
        workspace_id=workspace_id,
        schema_id=schema_id,
    )


@router.post("/{schema_id}/compute")
async def trigger_computation(
    schema_id: str,
    workspace_id: str = Depends(_auth.get_workspace_id),
):
    """On-demand accuracy computation and storage."""
    return await _accuracy_service.compute_and_store(
        workspace_id=workspace_id,
        schema_id=schema_id,
    )
