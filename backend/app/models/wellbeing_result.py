import uuid
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WellbeingResult(Base):
    """Existing derived-result storage only; no scoring or disclosure behavior."""

    __tablename__ = "wellbeing_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    wellbeing_private_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wellbeing_private.id", ondelete="CASCADE", name="wellbeing_results_wellbeing_private_id_fkey"), nullable=False
    )
    personnel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("personnel.id", ondelete="CASCADE", name="wellbeing_results_personnel_id_fkey"), nullable=False
    )
    instrument_name: Mapped[str] = mapped_column(String(100), nullable=False)
    assessment_date: Mapped[date] = mapped_column(Date, nullable=False)
    score_summary_json: Mapped[Any] = mapped_column(JSONB, nullable=False)
    category_label: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    trend_label: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False)

    __table_args__ = (Index("idx_wb_results_personnel", "personnel_id"),)


__all__ = ["WellbeingResult"]
