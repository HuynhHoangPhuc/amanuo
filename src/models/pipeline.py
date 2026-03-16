"""Pydantic request/response models for the pipelines API."""

from pydantic import BaseModel


class PipelineCreateRequest(BaseModel):
    """Request body for creating a new pipeline."""

    name: str
    description: str | None = None
    config: str  # YAML string


class PipelineUpdateRequest(BaseModel):
    """Request body for updating an existing pipeline."""

    name: str | None = None
    description: str | None = None
    config: str | None = None  # YAML string


class PipelineResponse(BaseModel):
    """Pipeline record returned by the API."""

    id: str
    workspace_id: str
    name: str
    description: str | None
    config: str
    is_active: bool
    created_at: str
    updated_at: str
