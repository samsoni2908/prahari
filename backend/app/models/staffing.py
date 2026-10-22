import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Staffing(Base):
    __tablename__ = "staffing"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("units.id", ondelete="CASCADE"), nullable=False, index=True
    )
    record_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    sanctioned_strength: Mapped[int] = mapped_column(Integer, nullable=False)
    available_strength: Mapped[int] = mapped_column(Integer, nullable=False)
    required_strength: Mapped[int] = mapped_column(Integer, nullable=False)
    coverage_percent: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("sanctioned_strength >= 0", name="chk_staffing_sanctioned"),
        CheckConstraint("available_strength >= 0", name="chk_staffing_available"),
        CheckConstraint("required_strength >= 0", name="chk_staffing_required"),
        CheckConstraint("coverage_percent IS NULL OR coverage_percent >= 0", name="chk_staffing_coverage"),
    )


__all__ = ["Staffing"]
