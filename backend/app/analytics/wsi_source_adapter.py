"""Seven-factor normalization of manifest-certified operational source windows.

No database, HTTP, private data, policy defaults or prediction coupling. The
repository supplies the same allowlisted sources used by operational inference,
plus actual completed leave history. Certification is independent of Model A's
frozen feature requirements.
"""
import math
from datetime import datetime, timedelta, timezone
from app.analytics.operational_feature_adapter import POLICY, source_hash, row_key
from app.analytics.wsi import compute_wsi_detailed

REFERENCES = {"D": "wsi.d.reference_hours", "R": "wsi.r.reference_hours",
    "C": "wsi.c.reference_days", "L": "wsi.l.reference_days", "H": "wsi.h.reference_intensity"}


class WsiSourceAdapter:
    def __init__(self, repository):
        self.repository = repository

    def build(self, personnel_id, unit_id, cutoff):
        result = {"status": "NOT_COMPUTED", "value": None, "reason_codes": [],
            "as_of": cutoff.isoformat(), "source_timestamp": None, "source_hash": None,
            "policy_version": None, "coverage": {"required_days": 30, "observed_days": 0},
            "components": {}, "freshness": "UNAVAILABLE"}

        def unavailable(status, reason):
            result.update(status=status, reason_codes=[reason])
            return result

        manifest = self.repository.wsi_manifest(unit_id, cutoff)
        if not manifest:
            return unavailable("NOT_COMPUTED", "COVERAGE_MANIFEST_MISSING")
        if manifest.get("policy") != POLICY or manifest.get("cutoff") != cutoff.isoformat():
            return unavailable("DATA_STALE", "COVERAGE_CUTOFF_MISMATCH")
        required = {"personnel", "posting_history", "duties", "rest_records", "leave_records", "deployments", "staffing"}
        if not required.issubset(set(manifest.get("families", []))) or manifest.get("unknown_gaps") != 0:
            return unavailable("INSUFFICIENT_HISTORY", "SOURCE_COVERAGE_INCOMPLETE")
        policy = self.repository.wsi_policy(cutoff)
        if not policy:
            return unavailable("NOT_COMPUTED", "NORMALIZATION_POLICY_MISSING")
        result["policy_version"] = policy.get("version")
        data = self.repository.wsi_sources(unit_id, cutoff)
        try:
            digest = source_hash(data)
            result["source_hash"] = digest
            if manifest.get("source_hash") != digest:
                return unavailable("DATA_STALE", "SOURCE_CHANGED")
            midnight = datetime.combine(cutoff, datetime.min.time(), timezone.utc)
            policy_start = datetime.fromisoformat(policy["effective_from"])
            policy_end = datetime.fromisoformat(policy["effective_until"]) if policy.get("effective_until") else None
            policy_known = datetime.fromisoformat(policy["known_at"])
            if (not result["policy_version"] or any(t.tzinfo is None for t in (policy_start, policy_known))
                    or policy_known > midnight or policy_start > midnight
                    or (policy_end and (policy_end.tzinfo is None or midnight >= policy_end))):
                return unavailable("NOT_COMPUTED", "POLICY_NOT_EFFECTIVE_AT_CUTOFF")
            values = policy["values"]
            refs = {}
            for component, key in REFERENCES.items():
                reference = float(values[key])
                if isinstance(values[key], bool) or not math.isfinite(reference) or reference <= 0:
                    raise ValueError()
                if (component == "R" and reference > 24) or (component == "H" and reference > 5):
                    raise ValueError()
                refs[component] = reference
            known_times = []
            for name, rows in data.items():
                for row in rows:
                    known = datetime.fromisoformat(manifest["known_at"][name + "." + row_key(row)])
                    if known.tzinfo is None or known > midnight:
                        return unavailable("INSUFFICIENT_HISTORY", "SOURCE_NOT_KNOWN_AT_CUTOFF")
                    known_times.append(known)
            result["source_timestamp"] = max(known_times).isoformat() if known_times else None
            people = [row for row in data["personnel"] if row["id"] == personnel_id and row["unit_id"] == unit_id and row["status"] == "ACTIVE"]
            start = cutoff - timedelta(days=30)
            postings = [row for row in data["posting_history"] if row["personnel_id"] == personnel_id
                and row["unit_id"] == unit_id and row["posting_start_date"] <= start
                and (row["posting_end_date"] is None or row["posting_end_date"] >= cutoff)]
            if len(people) != 1 or len(postings) != 1:
                return unavailable("INSUFFICIENT_HISTORY", "EFFECTIVE_MEMBERSHIP_UNPROVEN")
            required_days = {cutoff - timedelta(days=index) for index in range(1, 31)}
            complete_days = set(manifest.get("complete_days", {}).get(str(personnel_id), []))
            observed = sum(day.isoformat() in complete_days for day in required_days)
            result["coverage"]["observed_days"] = observed
            if observed != 30:
                return unavailable("INSUFFICIENT_HISTORY", "UNKNOWN_OPERATIONAL_DAY")
            duty = sorted([r for r in data["duties"] if r["personnel_id"] == personnel_id
                and start <= r["duty_date"] < cutoff], key=lambda r: r["start_at"])
            for index, row in enumerate(duty):
                hours = float(row["hours"])
                known = datetime.fromisoformat(manifest["known_at"]["duties." + row_key(row)])
                if (not math.isfinite(hours) or hours < 0 or row["start_at"].tzinfo is None
                        or row["end_at"].tzinfo is None or row["end_at"] > midnight or known < row["end_at"]
                        or row["start_at"].date() != row["duty_date"]
                        or abs((row["end_at"] - row["start_at"]).total_seconds() / 3600 - hours) > .01
                        or not isinstance(row["is_night"], bool)
                        or (index and duty[index-1]["end_at"] > row["start_at"])):
                    raise ValueError()
                # Date-run semantics need completed daily duty records, not silently split shifts.
                if row["end_at"].date() != row["duty_date"] and row["end_at"].time() != datetime.min.time():
                    return unavailable("NOT_COMPUTED", "UNSUPPORTED_DUTY_DAY_BOUNDARY")
            raw = {"D": sum(float(r["hours"]) for r in duty if r["duty_date"] >= cutoff - timedelta(days=7))}
            dates = {r["duty_date"] for r in duty if r["duty_date"] >= cutoff - timedelta(days=14)}
            run = longest = 0
            for index in range(14, 0, -1):
                run = run + 1 if cutoff - timedelta(days=index) in dates else 0
                longest = max(longest, run)
            raw["C"] = longest
            raw["N"] = sum(r["is_night"] for r in duty) / len(duty) if duty else 0.0
            week = {cutoff - timedelta(days=i) for i in range(1, 8)}
            rest = [r for r in data["rest_records"] if r["personnel_id"] == personnel_id and r["record_date"] in week]
            if len(rest) != 7 or {r["record_date"] for r in rest} != week:
                return unavailable("REST_DATA_MISSING", "REST_WINDOW_INCOMPLETE")
            for row in rest:
                hours = float(row["rest_hours"])
                known = datetime.fromisoformat(manifest["known_at"]["rest_records." + row_key(row)])
                if row["data_quality_status"] != "VALID":
                    return unavailable("REST_DATA_MISSING", "REST_SOURCE_NOT_VALID")
                if not math.isfinite(hours) or not 0 <= hours <= 24 or known < datetime.combine(row["record_date"] + timedelta(days=1), datetime.min.time(), timezone.utc):
                    raise ValueError()
            raw["R"] = sum(max(0, refs["R"] - float(r["rest_hours"])) for r in rest) / 7
            leaves = [r for r in data["leave_records"] if r["personnel_id"] == personnel_id
                and r.get("actual_end_date") is not None and r["actual_end_date"] < cutoff]
            if not leaves or manifest.get("leave_completion_history_complete", {}).get(str(personnel_id)) is not True:
                return unavailable("NOT_COMPUTED", "ACTUAL_LEAVE_COMPLETION_UNAVAILABLE")
            for row in leaves:
                if row.get("actual_start_date") is None or row["actual_start_date"] > row["actual_end_date"]:
                    raise ValueError()
                known = datetime.fromisoformat(manifest["known_at"]["leave_records." + row_key(row)])
                if known < datetime.combine(row["actual_end_date"] + timedelta(days=1), datetime.min.time(), timezone.utc):
                    return unavailable("INSUFFICIENT_HISTORY", "COMPLETION_NOT_KNOWN")
            raw["L"] = (cutoff - max(r["actual_end_date"] for r in leaves)).days
            deployment_by_day = {}
            for row in data["deployments"]:
                if row["personnel_id"] != personnel_id:
                    continue
                actual = manifest.get("completed_intervals", {}).get("deployments." + row_key(row), {})
                if (actual.get("confirmed_actual") is not True or row["end_date"] is None
                        or actual.get("start_date") != row["start_date"].isoformat()
                        or actual.get("end_date") != row["end_date"].isoformat()):
                    return unavailable("INSUFFICIENT_HISTORY", "ACTUAL_INTERVAL_UNPROVEN")
                intensity = float(row["intensity_level"])
                if not math.isfinite(intensity) or not 1 <= intensity <= 5 or row["end_date"] < row["start_date"] or row["end_date"] >= cutoff:
                    raise ValueError()
                known = datetime.fromisoformat(manifest["known_at"]["deployments." + row_key(row)])
                if known < datetime.combine(row["end_date"] + timedelta(days=1), datetime.min.time(), timezone.utc):
                    return unavailable("INSUFFICIENT_HISTORY", "COMPLETION_NOT_KNOWN")
                for day in required_days:
                    if row["start_date"] <= day <= row["end_date"]:
                        if day in deployment_by_day:
                            raise ValueError()
                        deployment_by_day[day] = intensity
            raw["H"] = sum(deployment_by_day.values()) / 30
            staffing = [r for r in data["staffing"] if r["unit_id"] == unit_id and r["record_date"] in week]
            if len(staffing) != 7 or {r["record_date"] for r in staffing} != week:
                return unavailable("INSUFFICIENT_HISTORY", "STAFFING_WINDOW_INCOMPLETE")
            pressures = []
            for row in staffing:
                available, required_strength = float(row["available_strength"]), float(row["required_strength"])
                if not all(math.isfinite(v) and v >= 0 for v in (available, required_strength)):
                    raise ValueError()
                if required_strength > 0:
                    pressures.append(max(0, 1 - available / required_strength))
            if not pressures:
                return unavailable("NOT_COMPUTED", "STAFFING_POSITIVE_DEMAND_UNAVAILABLE")
            raw["S"] = sum(pressures) / len(pressures)
            normalized = {key: 100 * min(1, max(0, value / refs[key])) if key in refs else 100 * value for key, value in raw.items()}
            calculated = compute_wsi_detailed(normalized, policy_version=policy["version"])
            result.update(status=calculated["status"], value=calculated["score"],
                components=calculated["components"], freshness="CURRENT_AT_CUTOFF", reason_codes=[])
            result["raw_measures"] = raw
            result["unrounded_value"] = calculated["unrounded_score"]
            result["excluded_zero_demand_days"] = 7 - len(pressures)
            result["peer_vector"] = [sum(float(r["hours"]) for r in duty), raw["N"],
                sum(float(r["rest_hours"]) for r in rest) / 7, len(deployment_by_day), raw["S"]]
            return result
        except KeyError:
            return unavailable("NOT_COMPUTED", "REQUIRED_SOURCE_OR_POLICY_FIELD_MISSING")
        except (ValueError, TypeError, OverflowError):
            return unavailable("COMPUTATION_ERROR", "INVALID_SOURCE_OR_POLICY")
