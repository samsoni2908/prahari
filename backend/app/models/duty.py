import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Duty(Base):
    __tablename__ = "duties"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    personnel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("personnel.id", ondelete="CASCADE"), nullable=False, index=True
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("units.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    duty_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duty_type: Mapped[str] = mapped_column(String(80), nullable=False)
    shift_type: Mapped[str] = mapped_column(String(40), nullable=False)
    is_night: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hours: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    deployment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deployments.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("end_at > start_at", name="chk_duties_time_window"),
        CheckConstraint("hours >= 0", name="chk_duties_hours"),
    )


__all__ = ["Duty"]
