"""Pydantic models for workspaces and API keys."""

from pydantic import BaseModel


class Workspace(BaseModel):
    id: str
    name: str
    created_at: str
    updated_at: str


class WorkspaceCreate(BaseModel):
    name: str


class ApiKey(BaseModel):
    """API key metadata (never includes the raw key)."""

    id: str
    workspace_id: str
    name: str
    key_prefix: str
    is_active: bool = True
    created_at: str
    last_used_at: str | None = None


class ApiKeyCreate(BaseModel):
    name: str


class ApiKeyCreated(BaseModel):
    """Returned once on creation — includes full key."""

    id: str
    name: str
    key: str  # full key, only shown once
    key_prefix: str
