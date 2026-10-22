import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BaselineMetric(Base):
    __tablename__ = "baseline_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    personnel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("personnel.id", ondelete="CASCADE"), nullable=False, index=True
    )
    metric_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(80), nullable=False)
    current_value: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    median_value: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    mad_value: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    z_score: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    ewma_value: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    history_count: Mapped[int] = mapped_column(Integer, nullable=False)
    baseline_status: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("history_count >= 0", name="chk_baseline_history_count"),
    )


__all__ = ["BaselineMetric"]
