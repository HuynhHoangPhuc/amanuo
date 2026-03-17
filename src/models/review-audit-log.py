"""SQLAlchemy ORM model for review audit log (immutable action history)."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class ReviewAuditLogORM(Base):
    """Immutable audit trail for all review/approval actions."""

    __tablename__ = "review_audit_log"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    job_id: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    created_at: Mapped[str] = mapped_column(String, nullable=False)
