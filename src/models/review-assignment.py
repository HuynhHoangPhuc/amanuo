"""SQLAlchemy ORM model for review assignments (individual reviewer actions)."""

from sqlalchemy import String, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class ReviewAssignmentORM(Base):
    """Individual reviewer assignment within a review round."""

    __tablename__ = "review_assignments"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    round_id: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")  # pending|in_progress|approved|corrected|rejected
    corrected_result: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    corrections: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON diff
    review_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    completed_at: Mapped[str | None] = mapped_column(String, nullable=True)
