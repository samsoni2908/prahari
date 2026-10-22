"""Migration d26186_leave_lifecycle: extend leave_records with operational disruption and planning fields.

Revision ID: d26186_leave_lifecycle
Revises: c26186_implementation
Create Date: 2026-10-04

Exact columns added (all nullable for 100% backward compatibility):
- planning_classification: VARCHAR(30) (PLANNED | UNPLANNED)
- approved_at: TIMESTAMPTZ
- actual_start_date: DATE
- actual_end_date: DATE
- disruption_type: VARCHAR(30) (CANCELLED | DEFERRED | RECALLED | SHORTENED)
- disruption_initiator: VARCHAR(30) (SERVICE | PERSONNEL)
- disrupted_at: TIMESTAMPTZ
"""

from alembic import op
import sqlalchemy as sa

revision = "d26186_leave_lifecycle"
down_revision = "c26186_implementation"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add nullable columns to leave_records
    op.add_column("leave_records", sa.Column("planning_classification", sa.String(30), nullable=True))
    op.add_column("leave_records", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("leave_records", sa.Column("actual_start_date", sa.Date(), nullable=True))
    op.add_column("leave_records", sa.Column("actual_end_date", sa.Date(), nullable=True))
    op.add_column("leave_records", sa.Column("disruption_type", sa.String(30), nullable=True))
    op.add_column("leave_records", sa.Column("disruption_initiator", sa.String(30), nullable=True))
    op.add_column("leave_records", sa.Column("disrupted_at", sa.DateTime(timezone=True), nullable=True))

    # 2. Add domain check constraints
    op.create_check_constraint(
        "chk_leave_planning_classification",
        "leave_records",
        "planning_classification IS NULL OR planning_classification IN ('PLANNED', 'UNPLANNED')",
    )
    op.create_check_constraint(
        "chk_leave_disruption_type",
        "leave_records",
        "disruption_type IS NULL OR disruption_type IN ('CANCELLED', 'DEFERRED', 'RECALLED', 'SHORTENED')",
    )
    op.create_check_constraint(
        "chk_leave_disruption_initiator",
        "leave_records",
        "disruption_initiator IS NULL OR disruption_initiator IN ('SERVICE', 'PERSONNEL')",
    )
    op.create_check_constraint(
        "chk_leave_actual_dates",
        "leave_records",
        "actual_end_date IS NULL OR actual_start_date IS NULL OR actual_end_date >= actual_start_date",
    )

    # 3. Add performance indexes for cutoff window queries
    op.create_index(
        "ix_leave_records_actual_start",
        "leave_records",
        ["actual_start_date"],
    )
    op.create_index(
        "ix_leave_records_disrupted_at",
        "leave_records",
        ["disrupted_at"],
    )


def downgrade():
    op.drop_index("ix_leave_records_disrupted_at", table_name="leave_records")
    op.drop_index("ix_leave_records_actual_start", table_name="leave_records")
    op.drop_constraint("chk_leave_actual_dates", "leave_records", type_="check")
    op.drop_constraint("chk_leave_disruption_initiator", "leave_records", type_="check")
    op.drop_constraint("chk_leave_disruption_type", "leave_records", type_="check")
    op.drop_constraint("chk_leave_planning_classification", "leave_records", type_="check")
    op.drop_column("leave_records", "disrupted_at")
    op.drop_column("leave_records", "disruption_initiator")
    op.drop_column("leave_records", "disruption_type")
    op.drop_column("leave_records", "actual_end_date")
    op.drop_column("leave_records", "actual_start_date")
    op.drop_column("leave_records", "approved_at")
    op.drop_column("leave_records", "planning_classification")
