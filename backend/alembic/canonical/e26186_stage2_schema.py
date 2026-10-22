"""Stage-2 approved persistence delta; no business-data backfill.

PENDING and RESOLVED in action history are LEGACY_COMPATIBILITY_ONLY.
Downgrade is for disposable/development databases, never retained data.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "e26186_stage2_schema"
down_revision = "d26186_leave_lifecycle"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "welfare_case_actions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("case_id", UUID(as_uuid=True), nullable=False),
        sa.Column("actor_user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("action_type", sa.String(40), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("visibility", sa.String(20), nullable=False),
        sa.Column("follow_up_date", sa.Date(), nullable=True),
        sa.Column("case_status", sa.String(40), nullable=True),
        sa.Column("assigned_to_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("idempotency_key", sa.CHAR(64), nullable=False),
        sa.Column("request_hash", sa.CHAR(64), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["support_requests.id"], ondelete="RESTRICT", name="welfare_case_actions_case_id_fkey"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT", name="welfare_case_actions_actor_user_id_fkey"),
        sa.ForeignKeyConstraint(["assigned_to_user_id"], ["users.id"], ondelete="RESTRICT", name="welfare_case_actions_assigned_to_user_id_fkey"),
        sa.CheckConstraint("action_type IN ('CONTACT_ATTEMPT','DISCUSSION','WORKLOAD_REVIEW','REFERRAL','FOLLOW_UP','ASSIGN','REASSIGN','STATUS_CHANGE','CLOSE')", name="welfare_case_actions_action_type_check"),
        sa.CheckConstraint("visibility IN ('PERSONNEL','OFFICER')", name="welfare_case_actions_visibility_check"),
        sa.CheckConstraint("char_length(note) <= 2000", name="welfare_case_actions_note_length_check"),
        sa.CheckConstraint("case_status IN ('OPEN','ASSIGNED','IN_PROGRESS','CLOSED','WITHDRAWN','PENDING','RESOLVED')", name="welfare_case_actions_case_status_check"),
        sa.UniqueConstraint("case_id", "actor_user_id", "idempotency_key", name="welfare_case_actions_case_actor_idempotency_key"),
    )
    op.create_index("idx_welfare_case_actions_case_created_id", "welfare_case_actions", ["case_id", "created_at", "id"])
    op.create_table(
        "notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("recipient_user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("notification_type", sa.String(40), nullable=False),
        sa.Column("message", sa.String(255), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("resource_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dedupe_key", sa.CHAR(64), nullable=False),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], ondelete="RESTRICT", name="notifications_recipient_user_id_fkey"),
        sa.UniqueConstraint("recipient_user_id", "dedupe_key", name="notifications_recipient_dedupe_key"),
    )
    op.create_index("idx_notifications_recipient_created_id", "notifications", ["recipient_user_id", "created_at", "id"])
    op.add_column("support_requests", sa.Column("request_key_hash", sa.CHAR(64), nullable=True))
    op.add_column("support_requests", sa.Column("request_hash", sa.CHAR(64), nullable=True))
    op.create_index("uq_support_requests_personnel_request_key", "support_requests", ["personnel_id", "request_key_hash"], unique=True, postgresql_where=sa.text("request_key_hash IS NOT NULL"))
    op.add_column("auth_sessions", sa.Column("refresh_secret_hash", sa.CHAR(64), nullable=True))


def downgrade():
    op.drop_index("uq_support_requests_personnel_request_key", table_name="support_requests")
    op.drop_column("auth_sessions", "refresh_secret_hash")
    op.drop_column("support_requests", "request_hash")
    op.drop_column("support_requests", "request_key_hash")
    op.drop_index("idx_notifications_recipient_created_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("idx_welfare_case_actions_case_created_id", table_name="welfare_case_actions")
    op.drop_table("welfare_case_actions")
