import uuid
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ModelOutput(Base):
    __tablename__ = "model_outputs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    personnel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("personnel.id", ondelete="CASCADE"), nullable=False, index=True
    )
    prediction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    target_name: Mapped[str] = mapped_column(String(120), nullable=False)
    hr_probability: Mapped[Optional[float]] = mapped_column(Numeric(7, 6), nullable=True)
    wellbeing_probability: Mapped[Optional[float]] = mapped_column(Numeric(7, 6), nullable=True)
    combined_probability: Mapped[Optional[float]] = mapped_column(Numeric(7, 6), nullable=True)
    risk_score: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    predicted_class: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    feature_set_version: Mapped[str] = mapped_column(String(50), nullable=False)
    training_data_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    data_completeness: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    explanation_json: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("hr_probability >= 0 AND hr_probability <= 1", name="model_outputs_hr_probability_check"),
        CheckConstraint("predicted_class IS NULL OR predicted_class IN (0, 1)", name="chk_model_class"),
    )


__all__ = ["ModelOutput"]
