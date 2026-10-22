"""Migration Set A: record external implementation and optional outcome linkage."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "c26186_implementation"
down_revision = "b26186_baseline"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "scenario_implementations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("scenario_id", UUID(as_uuid=True), sa.ForeignKey("roster_scenarios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("approval_id", UUID(as_uuid=True), sa.ForeignKey("approvals.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("implemented_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_assignments_json", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("status IN ('IMPLEMENTATION_PENDING', 'IMPLEMENTED', 'NOT_IMPLEMENTED')", name="implementation_status_check"),
        sa.CheckConstraint("status <> 'IMPLEMENTED' OR (effective_at IS NOT NULL AND implemented_by_user_id IS NOT NULL)", name="implementation_confirmed_check"),
        sa.CheckConstraint("status <> 'NOT_IMPLEMENTED' OR effective_at IS NULL", name="implementation_not_effective_check"),
    )
    op.add_column("outcomes", sa.Column("implementation_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("outcomes_implementation_id_fkey", "outcomes", "scenario_implementations", ["implementation_id"], ["id"], ondelete="RESTRICT")


def downgrade():
    op.drop_constraint("outcomes_implementation_id_fkey", "outcomes", type_="foreignkey")
    op.drop_column("outcomes", "implementation_id")
    op.drop_table("scenario_implementations")
