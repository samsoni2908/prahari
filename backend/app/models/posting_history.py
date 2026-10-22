import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PostingHistory(Base):
    __tablename__ = "posting_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    personnel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("personnel.id", ondelete="CASCADE"), nullable=False, index=True
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("units.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    posting_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    posting_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    posting_type: Mapped[str] = mapped_column(String(80), nullable=False)
    location_label: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    hardship_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("posting_end_date IS NULL OR posting_end_date >= posting_start_date", name="chk_posting_dates"),
        CheckConstraint("hardship_level >= 1 AND hardship_level <= 5", name="posting_history_hardship_level_check"),
    )


__all__ = ["PostingHistory"]
