import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Training(Base):
    __tablename__ = "training"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    personnel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("personnel.id", ondelete="CASCADE"), nullable=False, index=True
    )
    training_name: Mapped[str] = mapped_column(String(150), nullable=False)
    training_type: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    hours: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="chk_training_dates"),
        CheckConstraint("hours IS NULL OR hours >= 0", name="chk_training_hours"),
    )


__all__ = ["Training"]
