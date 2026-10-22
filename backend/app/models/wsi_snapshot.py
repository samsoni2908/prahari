import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WsiSnapshot(Base):
    __tablename__ = "wsi_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    personnel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("personnel.id", ondelete="CASCADE"), nullable=False, index=True
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("units.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    wsi_score: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    d_component: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    r_component: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    c_component: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    n_component: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    l_component: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    h_component: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    s_component: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("wsi_score >= 0 AND wsi_score <= 100", name="chk_wsi_score"),
        CheckConstraint("d_component >= 0 AND d_component <= 100", name="chk_wsi_d"),
        CheckConstraint("r_component >= 0 AND r_component <= 100", name="chk_wsi_r"),
        CheckConstraint("c_component >= 0 AND c_component <= 100", name="chk_wsi_c"),
        CheckConstraint("n_component >= 0 AND n_component <= 100", name="chk_wsi_n"),
        CheckConstraint("l_component >= 0 AND l_component <= 100", name="chk_wsi_l"),
        CheckConstraint("h_component >= 0 AND h_component <= 100", name="chk_wsi_h"),
        CheckConstraint("s_component >= 0 AND s_component <= 100", name="chk_wsi_s"),
    )


__all__ = ["WsiSnapshot"]
