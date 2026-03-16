"""Pydantic models for workspaces and API keys, plus SQLAlchemy ORM models."""

from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel

from src.models.base import Base, TimestampMixin


# --- SQLAlchemy ORM Models ---

class WorkspaceORM(Base, TimestampMixin):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)


class UserORM(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    workspace_id: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class ApiKeyORM(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    key_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    key_prefix: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    last_used_at: Mapped[str | None] = mapped_column(String, nullable=True)


# --- Pydantic Models ---

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
