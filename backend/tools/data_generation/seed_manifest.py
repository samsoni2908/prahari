"""Generate and validate the public synthetic seed-file inventory.

The manifest inventories every CSV beside it except itself.  Excluding the
manifest avoids an impossible self-referential checksum while still making
all seed inputs, governed evaluation data, and derived demo fixtures auditable.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path
from typing import Iterable


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SEED_DIRECTORY = REPOSITORY_ROOT / "data" / "seed26186"
MANIFEST_PATH = SEED_DIRECTORY / "manifest.csv"

FIELDS = (
    "path",
    "category",
    "rows",
    "sha256",
    "dataset_version",
    "generator_version",
    "schema_version",
    "seed",
    "generation_period",
    "generation_date",
    "validation_status",
)

METADATA = {
    "dataset_version": "seed26186-public-v2",
    "generator_version": "prahari-synth-gen-2.0",
    "schema_version": "2.0",
    "seed": "26186",
    "generation_period": "2025-09-26..2026-09-25",
    "generation_date": "2026-09-26T06:00:00Z",
    "validation_status": "PASS",
}

RAW_FILES = {
    "deployments.csv",
    "duties.csv",
    "leave_records.csv",
    "person_skills.csv",
    "personnel.csv",
    "posting_history.csv",
    "rest_records.csv",
    "skills.csv",
    "staffing.csv",
    "support_requests.csv",
    "training.csv",
    "units.csv",
    "users.csv",
}

GOVERNANCE_FILES = {
    "data_dictionary.csv",
    "feature_dictionary.csv",
    "ml_training.csv",
    "model_a_canonical_dataset.csv",
    "split_manifest.csv",
    "target_audit.csv",
}

ALLOWED_ROLES = {"PERSONNEL", "WELFARE_OFFICER", "COMMANDER", "ADMIN"}


def _category(path: Path) -> str:
    if path.name in RAW_FILES:
        return "raw"
    if path.name in GOVERNANCE_FILES:
        return "governance"
    return "derived_demo"


def _csv_row_count(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ValueError(f"{path}: CSV is empty") from exc
        if not header or any(not column.strip() for column in header):
            raise ValueError(f"{path}: CSV header contains an empty column")
        width = len(header)
        count = 0
        for line_number, row in enumerate(reader, start=2):
            if len(row) != width:
                raise ValueError(
                    f"{path}:{line_number}: expected {width} columns, found {len(row)}"
                )
            count += 1
        return count


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inventory() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted(SEED_DIRECTORY.glob("*.csv"), key=lambda item: item.name):
        if path == MANIFEST_PATH:
            continue
        relative = path.relative_to(REPOSITORY_ROOT).as_posix()
        rows.append(
            {
                "path": relative,
                "category": _category(path),
                "rows": str(_csv_row_count(path)),
                "sha256": _sha256(path),
                **METADATA,
            }
        )
    return rows


def write_manifest() -> None:
    rows = inventory()
    with MANIFEST_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _validate_roles(errors: list[str]) -> None:
    users_path = SEED_DIRECTORY / "users.csv"
    with users_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    roles = {row.get("role", "") for row in rows}
    unexpected = roles - ALLOWED_ROLES
    missing = ALLOWED_ROLES - roles
    if unexpected:
        errors.append(f"users.csv contains unsupported roles: {sorted(unexpected)}")
    if missing:
        errors.append(f"users.csv is missing required role fixtures: {sorted(missing)}")


def validate_manifest() -> list[str]:
    errors: list[str] = []
    try:
        expected = inventory()
    except ValueError as exc:
        return [str(exc)]

    with MANIFEST_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != FIELDS:
            errors.append(
                f"manifest header mismatch: expected {list(FIELDS)}, found {reader.fieldnames}"
            )
        actual = list(reader)

    expected_by_path = {row["path"]: row for row in expected}
    actual_by_path: dict[str, dict[str, str]] = {}
    for row in actual:
        path = row.get("path", "")
        if path in actual_by_path:
            errors.append(f"duplicate manifest path: {path}")
        actual_by_path[path] = row

    missing = sorted(set(expected_by_path) - set(actual_by_path))
    extra = sorted(set(actual_by_path) - set(expected_by_path))
    if missing:
        errors.append(f"manifest is missing files: {missing}")
    if extra:
        errors.append(f"manifest references absent files: {extra}")

    for path in sorted(set(expected_by_path) & set(actual_by_path)):
        if actual_by_path[path] != expected_by_path[path]:
            differing = [
                field for field in FIELDS
                if actual_by_path[path].get(field) != expected_by_path[path].get(field)
            ]
            errors.append(f"manifest metadata mismatch for {path}: {differing}")

    private_exports = {"wellbeing_private.csv", "wellbeing_consent.csv"}
    leaked = sorted(path.name for path in SEED_DIRECTORY.glob("*.csv") if path.name in private_exports)
    if leaked:
        errors.append(f"private wellbeing exports must not be published: {leaked}")

    _validate_roles(errors)
    return errors


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="regenerate manifest.csv before validation")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.write:
        write_manifest()
    errors = validate_manifest()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"PASS: {len(inventory())} seed CSV files match {MANIFEST_PATH.relative_to(REPOSITORY_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
