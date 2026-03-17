"""SQLAlchemy ORM model for review rounds (approval workflow steps)."""

from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class ReviewRoundORM(Base):
    """A single round in an approval workflow for a job."""

    __tablename__ = "review_rounds"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    job_id: Mapped[str] = mapped_column(String, nullable=False)
    policy_id: Mapped[str] = mapped_column(String, nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    round_type: Mapped[str] = mapped_column(String, nullable=False)  # "review" | "approve" | "escalation"
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")  # pending|in_progress|completed|escalated
    required_approvals: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    deadline_at: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    completed_at: Mapped[str | None] = mapped_column(String, nullable=True)
