"""SQLAlchemy ORM model for extraction reviews (HITL corrections)."""

from sqlalchemy import String, Integer, Text, Float
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class ExtractionReviewORM(Base):
    __tablename__ = "extraction_reviews"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    job_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    workspace_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)  # "approved" | "corrected"
    original_result: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    corrected_result: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    corrections: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON diff
    reviewer_id: Mapped[str | None] = mapped_column(String, nullable=True)
    review_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
