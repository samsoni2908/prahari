"""Verified retained PostgreSQL 16 physical baseline; no seed data."""

from pathlib import Path
import re

from alembic import op

revision = "b26186_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    sql = Path(__file__).with_name("baseline_28_tables.sql").read_text(encoding="utf-8")
    for statement in sql.split(";\n"):
        if statement.strip():
            op.get_bind().exec_driver_sql(statement)


def downgrade():
    sql = Path(__file__).with_name("baseline_28_tables.sql").read_text(encoding="utf-8")
    tables = re.findall(r"CREATE TABLE public\.([a-z_]+) \(", sql)
    if len(tables) != 28:
        raise RuntimeError("Unexpected baseline table inventory")
    op.get_bind().exec_driver_sql("DROP TABLE " + ", ".join("public." + name for name in tables))
