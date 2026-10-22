import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LeaveRecord(Base):
    __tablename__ = "leave_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    personnel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("personnel.id", ondelete="CASCADE"), nullable=False, index=True
    )
    leave_type: Mapped[str] = mapped_column(String(60), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    days: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Operational lifecycle and disruption extension (Task 11)
    # All fields nullable for 100% backward compatibility with retained historical rows
    planning_classification: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    actual_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    disruption_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    disruption_initiator: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    disrupted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="chk_leave_records_dates"),
        CheckConstraint("days >= 0", name="chk_leave_records_days"),
        CheckConstraint(
            "planning_classification IS NULL OR planning_classification IN ('PLANNED', 'UNPLANNED')",
            name="chk_leave_planning_classification",
        ),
        CheckConstraint(
            "disruption_type IS NULL OR disruption_type IN ('CANCELLED', 'DEFERRED', 'RECALLED', 'SHORTENED')",
            name="chk_leave_disruption_type",
        ),
        CheckConstraint(
            "disruption_initiator IS NULL OR disruption_initiator IN ('SERVICE', 'PERSONNEL')",
            name="chk_leave_disruption_initiator",
        ),
        CheckConstraint(
            "actual_end_date IS NULL OR actual_start_date IS NULL OR actual_end_date >= actual_start_date",
            name="chk_leave_actual_dates",
        ),
        Index("ix_leave_records_actual_start", "actual_start_date"),
        Index("ix_leave_records_disrupted_at", "disrupted_at"),
    )


__all__ = ["LeaveRecord"]
