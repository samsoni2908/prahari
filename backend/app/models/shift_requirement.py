import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ShiftRequirement(Base):
    """Published planning shift requirement and skill demand."""

    __tablename__ = "shift_requirements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("units.id", ondelete="RESTRICT", name="shift_requirements_unit_id_fkey"), nullable=False
    )
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    required_count: Mapped[int] = mapped_column(Integer, nullable=False)
    required_skills_json: Mapped[Any] = mapped_column(JSONB, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source_revision: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False)

    __table_args__ = (
        CheckConstraint("end_at > start_at", name="chk_shift_requirements_window"),
        CheckConstraint("required_count > 0", name="chk_shift_requirements_count"),
        CheckConstraint("jsonb_typeof(required_skills_json) = 'array'", name="chk_shift_requirements_skills"),
        CheckConstraint("length(btrim(source_revision)) > 0", name="chk_shift_requirements_source"),
        Index("ix_shift_requirements_unit_start", "unit_id", "start_at"),
    )


__all__ = ["ShiftRequirement"]
