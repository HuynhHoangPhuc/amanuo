"""SQLAlchemy ORM models for schema templates and version history."""

from sqlalchemy import String, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class SchemaORM(Base, TimestampMixin):
    __tablename__ = "schemas"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    fields: Mapped[str] = mapped_column(String, nullable=False)  # JSON array
    workspace_id: Mapped[str | None] = mapped_column(String, nullable=True)
    current_version: Mapped[str] = mapped_column(String, nullable=False, default="1.0.0")
    require_review: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # boolean flag
    approval_policy_id: Mapped[str | None] = mapped_column(String, nullable=True)


class SchemaVersionORM(Base):
    __tablename__ = "schema_versions"

    __table_args__ = (UniqueConstraint("schema_id", "version"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    schema_id: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False)
    fields: Mapped[str] = mapped_column(String, nullable=False)  # JSON array
    changelog: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
