import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RestRecord(Base):
    __tablename__ = "rest_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    personnel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("personnel.id", ondelete="CASCADE"), nullable=False, index=True
    )
    record_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    rest_hours: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    rest_gap_hours: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    data_quality_status: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("rest_hours IS NULL OR rest_hours >= -24", name="chk_rest_records_hours"),
    )


__all__ = ["RestRecord"]
