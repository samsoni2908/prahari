import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AvailabilityInterval(Base):
    """Published personnel availability and unavailability interval."""

    __tablename__ = "availability_intervals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    personnel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("personnel.id", ondelete="RESTRICT", name="availability_intervals_personnel_id_fkey"), nullable=False
    )
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    reason_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    source_revision: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False)

    __table_args__ = (
        CheckConstraint("end_at > start_at", name="chk_availability_intervals_window"),
        CheckConstraint("state IN ('AVAILABLE', 'UNAVAILABLE')", name="chk_availability_intervals_state"),
        CheckConstraint(
            "((state = 'AVAILABLE' AND reason_code IS NULL) OR (state = 'UNAVAILABLE' AND reason_code IS NOT NULL AND reason_code IN ('LEAVE', 'TRAINING', 'DEPLOYMENT', 'OTHER')))",
            name="chk_availability_intervals_reason",
        ),
        CheckConstraint("length(btrim(source_revision)) > 0", name="chk_availability_intervals_source"),
        Index("ix_availability_intervals_personnel_start", "personnel_id", "start_at"),
    )


__all__ = ["AvailabilityInterval"]
