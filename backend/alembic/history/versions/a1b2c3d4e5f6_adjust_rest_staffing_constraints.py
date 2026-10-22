"""adjust_rest_staffing_constraints

Revision ID: a1b2c3d4e5f6
Revises: 29cd235460df
Create Date: 2026-09-29 21:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '29cd235460df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. rest_records: allow negative turnaround deficits
    op.execute("ALTER TABLE rest_records DROP CONSTRAINT IF EXISTS rest_records_rest_hours_check")
    op.execute("ALTER TABLE rest_records DROP CONSTRAINT IF EXISTS rest_records_rest_gap_hours_check")
    op.execute("ALTER TABLE rest_records ALTER COLUMN rest_hours TYPE NUMERIC(6,2)")

    # 2. staffing: allow surplus staffing coverage above 100%
    op.execute("ALTER TABLE staffing DROP CONSTRAINT IF EXISTS staffing_coverage_percent_check")
    op.execute("ALTER TABLE staffing ADD CONSTRAINT staffing_coverage_percent_check CHECK (coverage_percent >= 0)")


def downgrade() -> None:
    op.execute("ALTER TABLE staffing DROP CONSTRAINT IF EXISTS staffing_coverage_percent_check")
    op.execute("ALTER TABLE staffing ADD CONSTRAINT staffing_coverage_percent_check CHECK (coverage_percent >= 0 AND coverage_percent <= 100)")
    op.execute("ALTER TABLE rest_records ADD CONSTRAINT rest_records_rest_hours_check CHECK (rest_hours >= 0)")
    op.execute("ALTER TABLE rest_records ADD CONSTRAINT rest_records_rest_gap_hours_check CHECK (rest_gap_hours >= 0)")
