"""Coverage-certified adapter to the locked builder; no inference or persistence."""
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from app.ml.features_hr import FEATURE_SET_B, compute_operational_features_at_cutoff

POLICY = "SOURCE_COVERAGE_POLICY_V1_SYNTHETIC_DEMO"
FAMILIES = frozenset({"duties","rest_records","leave_records","deployments","training","staffing","personnel","posting_history","person_skills","skills","boundary_context","peer_context"})


def row_key(row):
    return str(row["id"]) if "id" in row else str(row["personnel_id"])+":"+str(row["skill_id"])


def source_hash(data):
    # Only repository-allowlisted operational columns; deterministic ordering.
    canonical = {k: sorted(v, key=row_key) for k,v in sorted(data.items())}
    return hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",",":"), default=str, allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class FeatureResult:
    status: str
    personnel_id: str
    unit_id: str
    cutoff: date
    feature_set_version: str
    feature_names: tuple
    feature_vector: Optional[tuple]
    coverage: tuple
    reason_codes: tuple
    source_hash: Optional[str]

    def as_features(self):
        if self.status != "VALID" or self.feature_names != tuple(FEATURE_SET_B) or len(self.feature_vector or ()) != 15:
            raise ValueError("INVALID_FEATURE_CONTRACT")
        if not all(math.isfinite(v) for v in self.feature_vector):
            raise ValueError("NONFINITE_FEATURE")
        return dict(zip(self.feature_names, self.feature_vector))


class OperationalFeatureAdapter:
    def __init__(self, repository):
        self.repository = repository

    def build(self, personnel_id, unit_id, cutoff):
        result_hash = None
        def result(status, reason, vector=None):
            return FeatureResult(status,str(personnel_id),str(unit_id),cutoff,"v2.1-SetB-15ops",
                                 tuple(FEATURE_SET_B),vector,(POLICY,cutoff.isoformat()),(reason,),result_hash)
        manifest = self.repository.manifest(unit_id, cutoff)
        if manifest is None:
            return result("NOT_COMPUTED", "COVERAGE_MANIFEST_MISSING")
        if manifest.get("policy") != POLICY or manifest.get("cutoff") != cutoff.isoformat():
            return result("DATA_STALE", "COVERAGE_CUTOFF_MISMATCH")
        if set(manifest.get("families",())) != FAMILIES or manifest.get("unknown_gaps") != 0:
            return result("INSUFFICIENT_HISTORY","SOURCE_COVERAGE_INCOMPLETE")
        data = self.repository.sources(unit_id, cutoff)
        try:
            result_hash = source_hash(data)
        except (ValueError, TypeError):
            return result("COMPUTATION_ERROR","NONFINITE_SOURCE")
        if manifest.get("source_hash") != result_hash:
            return result("DATA_STALE","SOURCE_CHANGED")
        midnight = datetime.combine(cutoff,datetime.min.time(),timezone.utc)
        for name, rows in data.items():
            for row in rows:
                known = manifest.get("known_at",{}).get(name+"."+row_key(row))
                try:
                    seen = datetime.fromisoformat(known)
                    if seen.tzinfo is None or seen > midnight:
                        return result("INSUFFICIENT_HISTORY","SOURCE_NOT_KNOWN_AT_CUTOFF")
                    completed = None
                    if name == "duties":
                        completed = row["end_at"]
                    elif name == "rest_records":
                        completed = datetime.combine(row["record_date"]+timedelta(days=1),datetime.min.time(),timezone.utc)
                    elif name in ("deployments", "training") and row["end_date"] is not None:
                        completed = datetime.combine(row["end_date"]+timedelta(days=1),datetime.min.time(),timezone.utc)
                    if completed is not None and seen < completed:
                        return result("INSUFFICIENT_HISTORY","COMPLETION_NOT_KNOWN")
                except (ValueError,TypeError):
                    return result("INSUFFICIENT_HISTORY","KNOWN_AT_EVIDENCE_MISSING")
        person = next((p for p in data["personnel"] if p["id"] == personnel_id),None)
        if person is None:
            return result("NOT_COMPUTED","MEMBERSHIP_UNAVAILABLE")
        peers = [p for p in data["personnel"] if p["rank_or_grade"] == person["rank_or_grade"] and p["role_title"] == person["role_title"]]
        if len(peers) < 5:
            return result("PEER_COHORT_INSUFFICIENT","PEER_COHORT_INSUFFICIENT")
        days = {(cutoff-timedelta(days=i)).isoformat() for i in range(1,58)}
        for peer in peers:
            if not days.issubset(set(manifest.get("complete_days",{}).get(str(peer["id"]),()))):
                return result("INSUFFICIENT_HISTORY","UNKNOWN_OPERATIONAL_DAY")
            postings = [r for r in data["posting_history"] if r["personnel_id"] == peer["id"] and r["unit_id"] == unit_id and r["posting_start_date"] <= cutoff-timedelta(days=57) and (r["posting_end_date"] is None or r["posting_end_date"] >= cutoff)]
            if len(postings) != 1:
                return result("INSUFFICIENT_HISTORY","EFFECTIVE_MEMBERSHIP_UNPROVEN")
            duty_days = {r["duty_date"] for r in data["duties"] if r["personnel_id"] == peer["id"]}
            if not any(cutoff-timedelta(days=57) <= date.fromisoformat(day) < cutoff-timedelta(days=30) and date.fromisoformat(day) not in duty_days for day in days):
                return result("INSUFFICIENT_HISTORY","STREAK_BOUNDARY_UNPROVEN")
        for peer in [person]:
            rest = [r for r in data["rest_records"] if r["personnel_id"] == peer["id"] and cutoff-timedelta(days=30) <= r["record_date"] < cutoff]
            if len(rest) != 30 or len({r["record_date"] for r in rest}) != 30:
                return result("REST_DATA_MISSING","REST_WINDOW_INCOMPLETE")
            for row in rest:
                if row["data_quality_status"] != "VALID" or any(row[v] is None or not math.isfinite(float(row[v])) or float(row[v]) < 0 for v in ("rest_hours","rest_gap_hours")) or float(row["rest_hours"]) > 24:
                    return result("COMPUTATION_ERROR","INVALID_REST_SOURCE")
        for peer in peers:
            shifts = sorted([r for r in data["duties"] if r["personnel_id"] == peer["id"]],key=lambda r:r["start_at"])
            for i,row in enumerate(shifts):
                hours = float(row["hours"])
                if row["end_at"].date() != row["start_at"].date() and row["end_at"].time() != datetime.min.time():
                    return result("NOT_COMPUTED","UNSUPPORTED_DUTY_DAY_BOUNDARY")
                if not math.isfinite(hours) or hours < 0 or row["end_at"] > midnight or row["start_at"].date() != row["duty_date"] or abs((row["end_at"]-row["start_at"]).total_seconds()/3600-hours) > 0.01 or (i and shifts[i-1]["end_at"] > row["start_at"]):
                    return result("COMPUTATION_ERROR","INVALID_DUTY_SOURCE")
        for row in data["staffing"]:
            if row["required_strength"] <= 0 or row["available_strength"] < 0:
                return result("COMPUTATION_ERROR","INVALID_STAFFING")
        if not data["staffing"]:
            return result("INSUFFICIENT_HISTORY","STAFFING_MISSING")
        # Actual completed date-only records only; never treat planned ends as actual.
        for name in ("deployments","training"):
            for row in data[name]:
                actual = manifest.get("completed_intervals", {}).get(name+"."+row_key(row), {})
                if actual.get("start_date") != row["start_date"].isoformat() or row["end_date"] is None or actual.get("end_date") != row["end_date"].isoformat() or actual.get("confirmed_actual") is not True:
                    return result("INSUFFICIENT_HISTORY","ACTUAL_INTERVAL_UNPROVEN")
                if row["end_date"] is None or row["end_date"] >= cutoff or row["end_date"] < row["start_date"]:
                    return result("INSUFFICIENT_HISTORY","UNCONFIRMED_INTERVAL")
                if name == "training" and row["status"] not in ("COMPLETED",):
                    return result("INSUFFICIENT_HISTORY","UNCONFIRMED_TRAINING")
        normalized = [{**r,"date":r["duty_date"]} for r in data["duties"]]
        cohort = [sum(float(r["hours"]) for r in normalized if r["personnel_id"] == p["id"] and cutoff-timedelta(days=30) <= r["duty_date"] < cutoff) for p in peers]
        features = compute_operational_features_at_cutoff(cutoff,str(personnel_id),str(unit_id),
            duties=normalized,rest_records=data["rest_records"],deployments=data["deployments"],
            training=data["training"],staffing=data["staffing"],peer_cohort_duties_30d=cohort)
        if tuple(features) != tuple(FEATURE_SET_B) or len(features) != 15:
            return result("COMPUTATION_ERROR","FEATURE_CONTRACT_MISMATCH")
        if any(features[k] is None for k in FEATURE_SET_B):
            return result("INSUFFICIENT_HISTORY","FEATURE_INPUT_UNAVAILABLE")
        vector = tuple(float(features[k]) for k in FEATURE_SET_B)
        if not all(math.isfinite(v) for v in vector):
            return result("COMPUTATION_ERROR","NONFINITE_FEATURE")
        return result("VALID","COVERAGE_CERTIFIED",vector)
