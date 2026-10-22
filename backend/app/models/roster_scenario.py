import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RosterScenario(Base):
    __tablename__ = "roster_scenarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("units.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    scenario_name: Mapped[str] = mapped_column(String(150), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    current_snapshot_json: Mapped[Any] = mapped_column(JSONB, nullable=False)
    proposed_snapshot_json: Mapped[Any] = mapped_column(JSONB, nullable=False)
    before_metrics_json: Mapped[Any] = mapped_column(JSONB, nullable=False)
    after_metrics_json: Mapped[Any] = mapped_column(JSONB, nullable=False)
    constraint_results_json: Mapped[Any] = mapped_column(JSONB, nullable=False)
    optimizer_method: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


__all__ = ["RosterScenario"]
