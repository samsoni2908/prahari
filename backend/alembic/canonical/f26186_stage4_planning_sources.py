"""Stage-4A planning sources: shift_requirements, roster_assignments, availability_intervals.

Downgrade is for disposable/development databases only, never retained data.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "f26186_stage4_planning_sources"
down_revision = "e26186_stage2_schema"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "shift_requirements",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("unit_id", UUID(as_uuid=True), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("required_count", sa.Integer(), nullable=False),
        sa.Column("required_skills_json", JSONB(), nullable=False),
        sa.Column("is_locked", sa.Boolean(), nullable=False),
        sa.Column("source_revision", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="RESTRICT", name="shift_requirements_unit_id_fkey"),
        sa.CheckConstraint("end_at > start_at", name="chk_shift_requirements_window"),
        sa.CheckConstraint("required_count > 0", name="chk_shift_requirements_count"),
        sa.CheckConstraint("jsonb_typeof(required_skills_json) = 'array'", name="chk_shift_requirements_skills"),
        sa.CheckConstraint("length(btrim(source_revision)) > 0", name="chk_shift_requirements_source"),
    )
    op.create_index("ix_shift_requirements_unit_start", "shift_requirements", ["unit_id", "start_at"])

    op.create_table(
        "roster_assignments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("shift_id", UUID(as_uuid=True), nullable=False),
        sa.Column("personnel_id", UUID(as_uuid=True), nullable=False),
        sa.Column("is_locked", sa.Boolean(), nullable=False),
        sa.Column("source_revision", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["shift_id"], ["shift_requirements.id"], ondelete="RESTRICT", name="roster_assignments_shift_id_fkey"),
        sa.ForeignKeyConstraint(["personnel_id"], ["personnel.id"], ondelete="RESTRICT", name="roster_assignments_personnel_id_fkey"),
        sa.UniqueConstraint("shift_id", "personnel_id", name="uq_roster_assignments_shift_person"),
        sa.CheckConstraint("length(btrim(source_revision)) > 0", name="chk_roster_assignments_source"),
    )
    op.create_index("ix_roster_assignments_personnel", "roster_assignments", ["personnel_id"])

    op.create_table(
        "availability_intervals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("personnel_id", UUID(as_uuid=True), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("reason_code", sa.String(20), nullable=True),
        sa.Column("source_revision", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["personnel_id"], ["personnel.id"], ondelete="RESTRICT", name="availability_intervals_personnel_id_fkey"),
        sa.CheckConstraint("end_at > start_at", name="chk_availability_intervals_window"),
        sa.CheckConstraint("state IN ('AVAILABLE', 'UNAVAILABLE')", name="chk_availability_intervals_state"),
        sa.CheckConstraint(
            "((state = 'AVAILABLE' AND reason_code IS NULL) OR (state = 'UNAVAILABLE' AND reason_code IS NOT NULL AND reason_code IN ('LEAVE', 'TRAINING', 'DEPLOYMENT', 'OTHER')))",
            name="chk_availability_intervals_reason",
        ),
        sa.CheckConstraint("length(btrim(source_revision)) > 0", name="chk_availability_intervals_source"),
    )
    op.create_index("ix_availability_intervals_personnel_start", "availability_intervals", ["personnel_id", "start_at"])


def downgrade():
    op.drop_index("ix_availability_intervals_personnel_start", table_name="availability_intervals")
    op.drop_table("availability_intervals")
    op.drop_index("ix_roster_assignments_personnel", table_name="roster_assignments")
    op.drop_table("roster_assignments")
    op.drop_index("ix_shift_requirements_unit_start", table_name="shift_requirements")
    op.drop_table("shift_requirements")
