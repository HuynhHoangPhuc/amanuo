"""SQLAlchemy ORM model for accuracy metrics (per-schema tracking)."""

from sqlalchemy import String, Integer, Float, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class AccuracyMetricORM(Base):
    __tablename__ = "accuracy_metrics"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    schema_id: Mapped[str] = mapped_column(String, nullable=False)
    workspace_id: Mapped[str] = mapped_column(String, nullable=False)
    period_start: Mapped[str] = mapped_column(String, nullable=False)  # ISO date
    period_end: Mapped[str] = mapped_column(String, nullable=False)
    total_reviews: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    approved_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    corrected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accuracy_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    field_accuracy: Mapped[str] = mapped_column(Text, nullable=False, default="{}")  # JSON
    created_at: Mapped[str] = mapped_column(String, nullable=False)
