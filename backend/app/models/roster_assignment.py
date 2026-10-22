import uuid
from datetime import datetime
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RosterAssignment(Base):
    """Published baseline roster assignment."""

    __tablename__ = "roster_assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    shift_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shift_requirements.id", ondelete="RESTRICT", name="roster_assignments_shift_id_fkey"), nullable=False
    )
    personnel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("personnel.id", ondelete="RESTRICT", name="roster_assignments_personnel_id_fkey"), nullable=False
    )
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source_revision: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False)

    __table_args__ = (
        UniqueConstraint("shift_id", "personnel_id", name="uq_roster_assignments_shift_person"),
        CheckConstraint("length(btrim(source_revision)) > 0", name="chk_roster_assignments_source"),
        Index("ix_roster_assignments_personnel", "personnel_id"),
    )


__all__ = ["RosterAssignment"]
