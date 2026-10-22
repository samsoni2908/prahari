"""Deterministic expected_revision token calculation for RosterScenarios.

Computes version-tagged SHA-256 revision tokens binding:
- scenario UUID, unit ID, creator ID
- scenario_version, parent_id
- planning window
- normalized current planning inputs
- current assignments
- proposed assignments
- source hash, policy hash
- before metrics, after metrics
- constraint evidence
- optimizer/execution evidence
- created_at
- current workflow status
- latest immutable decision ID

Canonicalization requirements:
- deterministic sorted JSON
- stable ordering
- UTC-normalized timestamps
- explicit nulls
- finite numeric values only
- no raw arbitrary JSON serialization

Ensures optimistic concurrency control and prevents lost updates / stale decisions.
"""

from datetime import datetime, timezone
import hashlib
import json
import math
from typing import Any, Dict, List, Optional
import uuid


def canonical_normalize(val: Any) -> Any:
    """Normalize data structures into deterministic, sorted canonical representation."""
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        if not math.isfinite(val):
            raise ValueError(f"Non-finite float value in canonical digest: {val}")
        return round(val, 6)
    if isinstance(val, uuid.UUID):
        return str(val).lower()
    if isinstance(val, datetime):
        if val.tzinfo is None:
            val = val.replace(tzinfo=timezone.utc)
        else:
            val = val.astimezone(timezone.utc)
        return val.isoformat()
    if isinstance(val, dict):
        return {str(k): canonical_normalize(v) for k, v in sorted(val.items())}
    if isinstance(val, (list, tuple, set)):
        norm_list = [canonical_normalize(item) for item in val]
        # For list of dicts with known sort keys, sort stably
        if norm_list and isinstance(norm_list[0], dict):
            def dict_sort_key(d: Any) -> str:
                if not isinstance(d, dict):
                    return str(d)
                return ":".join(str(d.get(k, "")) for k in ("id", "shift_id", "personnel_id", "constraint_id", "start_at"))
            try:
                norm_list = sorted(norm_list, key=dict_sort_key)
            except Exception:
                pass
        return norm_list
    return str(val)


def compute_expected_revision(
    scenario_id: uuid.UUID,
    unit_id: uuid.UUID,
    creator_user_id: uuid.UUID,
    scenario_version: int = 1,
    parent_id: Optional[uuid.UUID] = None,
    planning_window: Optional[Dict[str, Any]] = None,
    source_hash: str = "",
    policy_hash: str = "",
    status: str = "FEASIBLE",
    current_snapshot_json: Any = None,
    proposed_snapshot_json: Any = None,
    before_metrics_json: Any = None,
    after_metrics_json: Any = None,
    constraint_results_json: Any = None,
    optimizer_method: Optional[str] = "DETERMINISTIC_LEXICOGRAPHICAL_SWAP_V1",
    created_at: Optional[datetime] = None,
    latest_approval_id: Optional[uuid.UUID] = None,
) -> str:
    """Compute deterministic server-derived expected_revision token over protected scenario content."""
    current_snap = current_snapshot_json if isinstance(current_snapshot_json, dict) else {}
    proposed_snap = proposed_snapshot_json if isinstance(proposed_snapshot_json, dict) else {}

    inputs = current_snap.get("inputs") if isinstance(current_snap, dict) else None
    current_assignments = current_snap.get("assignments") if isinstance(current_snap, dict) else current_snapshot_json
    proposed_assignments = proposed_snap.get("assignments") if isinstance(proposed_snap, dict) else proposed_snapshot_json

    protected_content = {
        "scenario_id": str(scenario_id).lower(),
        "unit_id": str(unit_id).lower(),
        "creator_user_id": str(creator_user_id).lower(),
        "scenario_version": scenario_version,
        "parent_id": str(parent_id).lower() if parent_id else None,
        "planning_window": planning_window,
        "normalized_inputs": inputs,
        "current_assignments": current_assignments,
        "proposed_assignments": proposed_assignments,
        "source_hash": source_hash,
        "policy_hash": policy_hash,
        "before_metrics": before_metrics_json,
        "after_metrics": after_metrics_json,
        "constraint_evidence": constraint_results_json,
        "optimizer_method": optimizer_method or "DETERMINISTIC_LEXICOGRAPHICAL_SWAP_V1",
        "created_at": created_at,
        "status": status,
        "latest_decision_id": str(latest_approval_id).lower() if latest_approval_id else None,
    }

    normalized = canonical_normalize(protected_content)
    serialized = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
    token_digest = hashlib.sha256(serialized).hexdigest()
    return f"rev-sha256-{token_digest}"
