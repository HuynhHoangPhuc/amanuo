"""SQLAlchemy ORM model for schema template marketplace."""

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class SchemaTemplate(Base, TimestampMixin):
    """Curated or workspace-scoped extraction schema template."""

    __tablename__ = "schema_templates"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    # category: invoice, receipt, identity, medical, other
    category: Mapped[str] = mapped_column(String, nullable=False, default="other")
    # JSON: list of SchemaField-compatible dicts (label, type, occurrence)
    fields: Mapped[str] = mapped_column(Text, nullable=False)
    # JSON array of language codes e.g. ["en", "ja"]
    languages: Mapped[str] = mapped_column(Text, default='["en"]')
    is_curated: Mapped[bool] = mapped_column(Boolean, default=False)
    # null = global/curated; set = belongs to a workspace
    workspace_id: Mapped[str | None] = mapped_column(String, nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[str] = mapped_column(String, default="1.0.0")
