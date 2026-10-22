"""Prepare disposable PostgreSQL databases used by the complete test suite.

This utility is deliberately guarded: it accepts only local hosts, database
names beginning with ``prahari_test_``, and an explicit reset opt-in. It is
intended for CI and disposable local verification, never retained databases.
"""

from __future__ import annotations

import csv
import io
import os
from pathlib import Path

import psycopg
from psycopg import sql
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
SEED_DIRECTORY = REPOSITORY_ROOT / "data" / "seed26186"
STAGE3_DATABASE = "prahari_test_stage3_20261018"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "postgres"}

SEED_TABLES = (
    "units",
    "personnel",
    "users",
    "skills",
    "person_skills",
    "posting_history",
    "deployments",
    "duties",
    "rest_records",
    "leave_records",
    "training",
    "staffing",
    "support_requests",
)


def _require_disposable(url: str) -> str:
    parsed = make_url(url)
    database = parsed.database or ""
    if parsed.host not in LOCAL_HOSTS or not database.startswith("prahari_test_"):
        raise RuntimeError(
            "Refusing database operation: target must be a local prahari_test_ database"
        )
    return database


def _reset_database(admin_url: str, database: str) -> None:
    with psycopg.connect(admin_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (database,),
            )
            cursor.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(database)))
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))


def _personnel_copy_source(path: Path) -> io.StringIO:
    output = io.StringIO(newline="")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        fields.insert(3, "full_name")
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in reader:
            row["full_name"] = f"Synthetic Personnel {row['pseudo_id']}"
            writer.writerow(row)
    output.seek(0)
    return output


def _copy_seed_table(connection: psycopg.Connection, table: str) -> int:
    path = SEED_DIRECTORY / f"{table}.csv"
    if table == "personnel":
        source = _personnel_copy_source(path)
    else:
        source = path.open("r", encoding="utf-8-sig", newline="")
    try:
        header = next(csv.reader(io.StringIO(source.readline())))
        source.seek(0)
        statement = sql.SQL(
            "COPY {} ({}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE, NULL '')"
        ).format(
            sql.Identifier(table),
            sql.SQL(", ").join(sql.Identifier(column) for column in header),
        )
        with connection.cursor() as cursor, cursor.copy(statement) as copy:
            while chunk := source.read(1024 * 1024):
                copy.write(chunk)
        with connection.cursor() as cursor:
            cursor.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table)))
            return int(cursor.fetchone()[0])
    finally:
        source.close()


def main() -> int:
    if os.environ.get("PRAHARI_ALLOW_TEST_DB_RESET") != "1":
        raise RuntimeError("Set PRAHARI_ALLOW_TEST_DB_RESET=1 for disposable test setup")

    target_async_url = os.environ["PRAHARI_TEST_DATABASE_URL"]
    target_url = make_url(target_async_url).set(drivername="postgresql").render_as_string(
        hide_password=False
    )
    target_database = _require_disposable(target_url)
    admin_url = os.environ["PRAHARI_TEST_ADMIN_URL"]
    admin_identity = make_url(admin_url)
    if admin_identity.host not in LOCAL_HOSTS:
        raise RuntimeError("Test database administrator URL must use a local host")

    _reset_database(admin_url, target_database)
    _reset_database(admin_url, STAGE3_DATABASE)

    # Alembic reads DATABASE_URL_SYNC from the process environment through settings.
    os.environ["DATABASE_URL_SYNC"] = target_url
    from alembic import command
    from alembic.config import Config

    command.upgrade(Config(str(BACKEND_ROOT / "alembic.ini")), "head")

    counts: dict[str, int] = {}
    with psycopg.connect(target_url) as connection:
        for table in SEED_TABLES:
            counts[table] = _copy_seed_table(connection, table)
        connection.commit()

    from tools.data_generation.planning_sources import PlanningSourceService

    engine = create_engine(target_url)
    with Session(engine) as session:
        planning = PlanningSourceService(session).import_synthetic_planning_data()
    engine.dispose()

    expected = {
        "status": "INSERTED",
        "source_hash": "98248f3ddab2e4b7801ea5f10f797fa115f1398ddba5c4867e56132bb20515aa",
        "shifts_count": 28,
        "assignments_count": 126,
        "availability_count": 48,
    }
    for key, value in expected.items():
        if planning.get(key) != value:
            raise RuntimeError(f"Planning fixture mismatch for {key}: {planning.get(key)!r}")

    print(
        f"PASS: prepared {target_database} ({sum(counts.values())} seed rows) "
        f"and blank {STAGE3_DATABASE}; planning source {planning['source_hash']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
