"""SQLAlchemy declarative base and shared mixins."""

from datetime import datetime

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """Adds created_at / updated_at ISO-string columns."""

    created_at: Mapped[str] = mapped_column(
        String,
        default=lambda: datetime.utcnow().isoformat(),
    )
    updated_at: Mapped[str] = mapped_column(
        String,
        default=lambda: datetime.utcnow().isoformat(),
        onupdate=lambda: datetime.utcnow().isoformat(),
    )
