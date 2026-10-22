import uuid
from datetime import date
from typing import Optional

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PersonSkill(Base):
    __tablename__ = "person_skills"

    personnel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("personnel.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )
    proficiency_level: Mapped[int] = mapped_column(Integer, nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    __table_args__ = (
        CheckConstraint("proficiency_level >= 1 AND proficiency_level <= 5", name="chk_person_skills_proficiency"),
    )


__all__ = ["PersonSkill"]
