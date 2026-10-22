import uuid
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import Date, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WellbeingPrivate(Base):
    __tablename__ = "wellbeing_private"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    personnel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("personnel.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assessment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    instrument_name: Mapped[str] = mapped_column(String(100), nullable=False)
    instrument_version: Mapped[str] = mapped_column(String(50), nullable=False)
    answers_json: Mapped[Any] = mapped_column(JSONB, nullable=False)
    score_json: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


__all__ = ["WellbeingPrivate"]
