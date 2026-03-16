"""Workspace CRUD endpoints."""

import importlib

from fastapi import APIRouter, Depends, HTTPException

_auth_middleware = importlib.import_module("src.middleware.auth-middleware")
_workspace_service = importlib.import_module("src.services.workspace-service")
_workspace_models = importlib.import_module("src.models.workspace")

get_workspace_id = _auth_middleware.get_workspace_id

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", status_code=201)
async def create_workspace(req: _workspace_models.WorkspaceCreate):
    """Create a new workspace."""
    try:
        return await _workspace_service.create_workspace(req.name)
    except Exception as e:
        if "UNIQUE constraint" in str(e):
            raise HTTPException(409, f"Workspace '{req.name}' already exists")
        raise


@router.get("")
async def list_workspaces():
    """List all workspaces."""
    return await _workspace_service.list_workspaces()


@router.get("/{workspace_id}")
async def get_workspace(workspace_id: str):
    """Get workspace by ID."""
    ws = await _workspace_service.get_workspace(workspace_id)
    if not ws:
        raise HTTPException(404, "Workspace not found")
    return ws


@router.delete("/{workspace_id}")
async def delete_workspace(workspace_id: str):
    """Delete a workspace (cannot delete 'default')."""
    if workspace_id == "default":
        raise HTTPException(400, "Cannot delete the default workspace")
    deleted = await _workspace_service.delete_workspace(workspace_id)
    if not deleted:
        raise HTTPException(404, "Workspace not found")
    return {"deleted": True}
