"""SQLAlchemy ORM model for approval policies."""

from sqlalchemy import String, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class ApprovalPolicyORM(Base, TimestampMixin):
    """Workspace-scoped approval policy defining chain or quorum workflow."""

    __tablename__ = "approval_policies"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    policy_type: Mapped[str] = mapped_column(String, nullable=False)  # "chain" | "quorum"
    config: Mapped[str] = mapped_column(Text, nullable=False)  # JSON config
    deadline_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
