import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AnomalyEvent(Base):
    __tablename__ = "anomaly_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    personnel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("personnel.id", ondelete="CASCADE"), nullable=False, index=True
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("units.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    event_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    algorithm: Mapped[str] = mapped_column(String(80), nullable=False)
    anomaly_score: Mapped[Optional[float]] = mapped_column(Numeric(10, 5), nullable=True)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, nullable=False)
    context_tag: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    feature_set_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


__all__ = ["AnomalyEvent"]
