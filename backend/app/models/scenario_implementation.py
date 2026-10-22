import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ScenarioImplementation(Base):
    __tablename__ = "scenario_implementations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    scenario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roster_scenarios.id", ondelete="RESTRICT"), nullable=False)
    approval_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("approvals.id", ondelete="RESTRICT"), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    implemented_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    effective_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_assignments_json: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('IMPLEMENTATION_PENDING','IMPLEMENTED','NOT_IMPLEMENTED')", name="implementation_status_check"),
        CheckConstraint("status <> 'IMPLEMENTED' OR (effective_at IS NOT NULL AND implemented_by_user_id IS NOT NULL)", name="implementation_confirmed_check"),
        CheckConstraint("status <> 'NOT_IMPLEMENTED' OR effective_at IS NULL", name="implementation_not_effective_check"),
    )


__all__ = ["ScenarioImplementation"]
