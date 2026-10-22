"""Repository-level checks for the public synthetic seed inventory."""

from tools.data_generation.seed_manifest import ALLOWED_ROLES, SEED_DIRECTORY, validate_manifest

import csv


def test_seed_manifest_matches_every_published_csv() -> None:
    assert validate_manifest() == []


def test_seed_users_contain_exactly_four_supported_roles() -> None:
    with (SEED_DIRECTORY / "users.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        roles = {row["role"] for row in csv.DictReader(handle)}
    assert roles == ALLOWED_ROLES
