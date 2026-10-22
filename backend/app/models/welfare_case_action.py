import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import CHAR, CheckConstraint, Date, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WelfareCaseAction(Base):
    """Case action persistence; legacy statuses are compatibility history only."""

    __tablename__ = "welfare_case_actions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("support_requests.id", ondelete="RESTRICT", name="welfare_case_actions_case_id_fkey"), nullable=False
    )
    actor_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT", name="welfare_case_actions_actor_user_id_fkey"), nullable=False
    )
    action_type: Mapped[str] = mapped_column(String(40), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    visibility: Mapped[str] = mapped_column(String(20), nullable=False)
    follow_up_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    case_status: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    assigned_to_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT", name="welfare_case_actions_assigned_to_user_id_fkey"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    request_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "action_type IN ('CONTACT_ATTEMPT','DISCUSSION','WORKLOAD_REVIEW','REFERRAL','FOLLOW_UP','ASSIGN','REASSIGN','STATUS_CHANGE','CLOSE')",
            name="welfare_case_actions_action_type_check",
        ),
        CheckConstraint("visibility IN ('PERSONNEL','OFFICER')", name="welfare_case_actions_visibility_check"),
        CheckConstraint("char_length(note) <= 2000", name="welfare_case_actions_note_length_check"),
        CheckConstraint(
            "case_status IN ('OPEN','ASSIGNED','IN_PROGRESS','CLOSED','WITHDRAWN','PENDING','RESOLVED')",
            name="welfare_case_actions_case_status_check",
        ),
        UniqueConstraint("case_id", "actor_user_id", "idempotency_key", name="welfare_case_actions_case_actor_idempotency_key"),
        Index("idx_welfare_case_actions_case_created_id", "case_id", "created_at", "id"),
    )


__all__ = ["WelfareCaseAction"]
