"""Canonical deterministic source hashing for planning objects.

Canonicalization rules:
- UUIDs normalized to lowercase hex strings.
- Timestamps converted to UTC ISO 8601 strings.
- Numeric values formatted consistently (integers, floats with no trailing artifacts).
- Strings stripped of outer whitespace.
- Dictionaries ordered by keys recursively.
- Lists preserve deterministic ordering.
- SHA-256 with length-prefix framing.
"""

from datetime import date, datetime, timezone
import hashlib
import json
from typing import Any, Dict, List
import uuid


def canonicalize_value(val: Any) -> Any:
    """Recursively canonicalize data structures for hashing."""
    if val is None:
        return None
    if isinstance(val, uuid.UUID):
        return str(val).lower()
    if isinstance(val, datetime):
        if val.tzinfo is None:
            val = val.replace(tzinfo=timezone.utc)
        else:
            val = val.astimezone(timezone.utc)
        return val.isoformat()
    if isinstance(val, date):
        return val.isoformat()
    if isinstance(val, (int, float, bool)):
        return val
    if isinstance(val, str):
        return val.strip()
    if isinstance(val, dict):
        return {k: canonicalize_value(v) for k, v in sorted(val.items())}
    if isinstance(val, (list, tuple, set)):
        return [canonicalize_value(item) for item in val]
    return str(val)


def compute_row_digest(row_dict: Dict[str, Any]) -> str:
    """Compute SHA-256 digest of a single canonicalized row with length-prefix framing."""
    canonical = canonicalize_value(row_dict)
    encoded = json.dumps(canonical, separators=(",", ":"), sort_keys=True).encode("utf-8")
    hasher = hashlib.sha256()
    hasher.update(len(encoded).to_bytes(8, "big"))
    hasher.update(encoded)
    return hasher.hexdigest()


def compute_canonical_source_hash(
    shift_requirements: List[Dict[str, Any]],
    roster_assignments: List[Dict[str, Any]],
    availability_intervals: List[Dict[str, Any]],
) -> str:
    """Compute deterministic SHA-256 source hash over all planning source rows.

    Rows are sorted by deterministic primary keys / natural keys before digesting.
    """
    hasher = hashlib.sha256()

    # 1. Shift requirements sorted by (unit_id, start_at, id)
    sorted_shifts = sorted(
        shift_requirements,
        key=lambda r: (str(r.get("unit_id", "")), str(r.get("start_at", "")), str(r.get("id", ""))),
    )
    for shift in sorted_shifts:
        row_hash = compute_row_digest(shift).encode("utf-8")
        hasher.update(b"SR:")
        hasher.update(len(row_hash).to_bytes(4, "big"))
        hasher.update(row_hash)

    # 2. Roster assignments sorted by (shift_id, personnel_id)
    sorted_assigns = sorted(
        roster_assignments,
        key=lambda r: (str(r.get("shift_id", "")), str(r.get("personnel_id", ""))),
    )
    for assign in sorted_assigns:
        row_hash = compute_row_digest(assign).encode("utf-8")
        hasher.update(b"RA:")
        hasher.update(len(row_hash).to_bytes(4, "big"))
        hasher.update(row_hash)

    # 3. Availability intervals sorted by (personnel_id, start_at, id)
    sorted_avails = sorted(
        availability_intervals,
        key=lambda r: (str(r.get("personnel_id", "")), str(r.get("start_at", "")), str(r.get("id", ""))),
    )
    for avail in sorted_avails:
        row_hash = compute_row_digest(avail).encode("utf-8")
        hasher.update(b"AI:")
        hasher.update(len(row_hash).to_bytes(4, "big"))
        hasher.update(row_hash)

    return hasher.hexdigest()
