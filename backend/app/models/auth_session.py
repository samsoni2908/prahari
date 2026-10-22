import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import CHAR, DateTime, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuthSession(Base):
    """Existing session storage mapping; does not enforce authentication lifecycle."""

    __tablename__ = "auth_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE", name="auth_sessions_user_id_fkey"), nullable=False
    )
    jti: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoke_reason: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    refresh_secret_hash: Mapped[Optional[str]] = mapped_column(CHAR(64), nullable=True)

    __table_args__ = (
        UniqueConstraint("jti", name="auth_sessions_jti_key"),
        Index("idx_sessions_user_revoked", "user_id", "revoked_at"),
        Index("idx_sessions_expires", "expires_at"),
        Index("idx_sessions_jti", "jti"),
    )


__all__ = ["AuthSession"]
