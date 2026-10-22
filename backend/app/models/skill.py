import uuid
from typing import Optional

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    skill_name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


__all__ = ["Skill"]
