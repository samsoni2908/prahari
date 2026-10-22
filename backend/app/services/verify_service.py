"""Measured operational follow-up for a confirmed external implementation."""

from datetime import datetime, timedelta, timezone
import hashlib
import json
import uuid

from fastapi import HTTPException
from sqlalchemy import select, text

from app.ml.targets import LeaveTargetState, classify_single_leave_record
from app.models import (
    AuditEvent, Duty, LeaveRecord, Outcome, Personnel, PolicyConfig,
    RestRecord, RosterScenario, ScenarioImplementation, ShiftRequirement, Staffing, WsiSnapshot,
)
from app.planning.source_hash import canonicalize_value
from app.repositories.audit_repository import AuditRepository
from app.services.notification_service import NotificationService
from app.security.scope import require_unit


WARNING = (
    "Observed operational indicators changed after implementation; this comparison "
    "does not establish that the intervention caused the change."
)
FAMILIES = ("duties", "rest_records", "staffing", "shift_requirements")


def _utc(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _hash_rows(rows):
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: str(item.id)):
        data = {column.name: getattr(row, column.name) for column in row.__table__.columns}
        encoded = json.dumps(canonicalize_value(data), sort_keys=True, separators=(",", ":")).encode()
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
    return digest.hexdigest()


def _full_day(day, start, end):
    begin = datetime.combine(day, datetime.min.time(), timezone.utc)
    return start <= begin and begin + timedelta(days=1) <= end


def _complete_days(start, end):
    day = start.date()
    count = 0
    while datetime.combine(day, datetime.min.time(), timezone.utc) < end:
        if _full_day(day, start, end):
            count += 1
        day += timedelta(days=1)
    return count


def _observed_constraints(duties, start, end):
    by_person = {}
    for duty in duties:
        by_person.setdefault(duty.personnel_id, []).append((_utc(duty.start_at), _utc(duty.end_at)))
    counts = {"overlap": 0, "rest_under_8h": 0, "rolling_7d_over_60h": 0, "consecutive_over_6d": 0}
    for intervals in by_person.values():
        intervals.sort()
        for index, (begin, finish) in enumerate(intervals):
            if not start <= begin < end:
                continue
            if index and begin < intervals[index - 1][1]:
                counts["overlap"] += 1
            elif index and (begin - intervals[index - 1][1]).total_seconds() < 8 * 3600:
                counts["rest_under_8h"] += 1
            last_7d = finish - timedelta(days=7)
            rolling = sum(
                max(0.0, (min(finish_i, finish) - max(begin_i, last_7d)).total_seconds() / 3600)
                for begin_i, finish_i in intervals
            )
            if rolling > 60:
                counts["rolling_7d_over_60h"] += 1
            run = {date_i.date() for date_i, _ in intervals if date_i <= begin}
            if all(begin.date() - timedelta(days=offset) in run for offset in range(7)):
                counts["consecutive_over_6d"] += 1
    return counts


def _adherence_summary(approved_changes, observable_count, observed_count):
    if not approved_changes:
        return {"status": "NOT_APPLICABLE", "numerator": 0, "denominator": 0, "ratio": None}
    return {
        "status": "VALID" if observable_count else "NOT_COMPUTED",
        "numerator": observed_count, "denominator": observable_count,
        "ratio": round(observed_count / observable_count, 4) if observable_count else None,
    }


def _revision(outcome):
    data = {
        "id": str(outcome.id), "scenario_id": str(outcome.scenario_id),
        "implementation_id": str(outcome.implementation_id),
        "observed_metrics": outcome.observed_metrics_json,
    }
    payload = json.dumps(canonicalize_value(data), sort_keys=True, separators=(",", ":")).encode()
    return "rev-sha256-" + hashlib.sha256(payload).hexdigest()


class VerifyService:
    def __init__(self, session):
        self.session = session
        self.audit = AuditRepository(session)

    async def _context(self, scenario_id, lock=False):
        actor = self.session.info.get("actor") or {}
        unit = require_unit(actor)
        if actor.get("role") not in ("COMMANDER", "WELFARE_OFFICER"):
            raise HTTPException(403, "Operational outcome scope required")
        stmt = select(RosterScenario).where(RosterScenario.id == scenario_id)
        if lock:
            stmt = stmt.with_for_update()
        scenario = (await self.session.execute(stmt)).scalar_one_or_none()
        if scenario is None or scenario.unit_id != unit:
            raise HTTPException(404, "Scenario not found")
        impl = (await self.session.execute(select(ScenarioImplementation).where(
            ScenarioImplementation.scenario_id == scenario_id,
            ScenarioImplementation.status == "IMPLEMENTED",
        ))).scalar_one_or_none()
        outcome = None
        if impl:
            stmt = select(Outcome).where(Outcome.implementation_id == impl.id)
            if lock:
                stmt = stmt.with_for_update()
            outcome = (await self.session.execute(stmt)).scalar_one_or_none()
        return actor, scenario, impl, outcome

    @staticmethod
    def _project(outcome):
        data = dict(outcome.observed_metrics_json or {})
        data.pop("frozen_affected_personnel_ids", None)
        if isinstance(data.get("review"), dict):
            data["review"] = {key: value for key, value in data["review"].items() if key != "actor_user_id"}
        return {
            "id": str(outcome.id), "scenario_id": str(outcome.scenario_id),
            "implementation_id": str(outcome.implementation_id),
            "expected_revision": _revision(outcome), **data,
        }

    async def get(self, scenario_id):
        _, scenario, impl, outcome = await self._context(scenario_id)
        if not impl:
            return {
                "scenario_id": str(scenario_id),
                "implementation_status": "IMPLEMENTATION_PENDING" if scenario.status == "APPROVED" else scenario.status,
                "workflow_status": "PENDING" if scenario.status == "APPROVED" else "NOT_APPLICABLE",
                "availability_status": "NOT_COMPUTED",
            }
        if not outcome:
            raise HTTPException(409, "Implementation has no governed outcome record")
        return self._project(outcome)

    async def _window_rows(self, unit_id, people, start, end):
        duties = list((await self.session.execute(select(Duty).where(
            Duty.unit_id == unit_id, Duty.personnel_id.in_(people),
            Duty.start_at < end, Duty.end_at > start,
        ))).scalars())
        rest = list((await self.session.execute(select(RestRecord).where(
            RestRecord.personnel_id.in_(people),
            RestRecord.record_date >= (start - timedelta(days=1)).date(),
            RestRecord.record_date < end.date(),
        ))).scalars())
        rest = [row for row in rest if _full_day(row.record_date, start, end)]
        wsi = list((await self.session.execute(select(WsiSnapshot).where(
            WsiSnapshot.unit_id == unit_id, WsiSnapshot.personnel_id.in_(people),
            WsiSnapshot.snapshot_date >= (start - timedelta(days=1)).date(),
            WsiSnapshot.snapshot_date < end.date(),
        ))).scalars())
        wsi = [row for row in wsi if _full_day(row.snapshot_date, start, end)]
        staffing = list((await self.session.execute(select(Staffing).where(
            Staffing.unit_id == unit_id,
            Staffing.record_date >= (start - timedelta(days=1)).date(),
            Staffing.record_date < end.date(),
        ))).scalars())
        staffing = [row for row in staffing if _full_day(row.record_date, start, end)]
        shifts = list((await self.session.execute(select(ShiftRequirement).where(
            ShiftRequirement.unit_id == unit_id,
            ShiftRequirement.start_at < end, ShiftRequirement.end_at > start,
        ))).scalars())
        return {
            "duties": duties, "rest_records": rest,
            "wsi_snapshots": wsi, "staffing": staffing,
            "shift_requirements": shifts,
        }

    @staticmethod
    def _coverage(manifest, label, rows):
        window = manifest.get(label) or {}
        families = window.get("families") or {}
        evidence = {}
        for family in FAMILIES:
            claim = families.get(family) or {}
            actual = rows[family]
            observed = {"count": len(actual), "hash": _hash_rows(actual)}
            evidence[family] = {
                **observed,
                "certified": claim.get("complete") is True
                and claim.get("count") == observed["count"]
                and claim.get("hash") == observed["hash"],
            }
        return evidence

    @staticmethod
    def _metrics(rows, affected, pseudo, start, end):
        duration_days = (end - start).total_seconds() / 86400
        per_person_hours = {pseudo[p]: 0.0 for p in affected}
        per_person_nights = {pseudo[p]: 0 for p in affected}
        unit_hours = 0.0
        for duty in rows["duties"]:
            hours = max(0.0, (_utc(min(duty.end_at, end)) - _utc(max(duty.start_at, start))).total_seconds() / 3600)
            unit_hours += hours
            if duty.personnel_id in affected:
                per_person_hours[pseudo[duty.personnel_id]] += hours
                if duty.is_night:
                    per_person_nights[pseudo[duty.personnel_id]] += 1
        rest_values = [float(r.rest_hours) for r in rows["rest_records"] if r.personnel_id in affected and r.rest_hours is not None and 0 <= float(r.rest_hours) <= 24 and r.data_quality_status == "OBSERVED"]
        gap_values = [float(r.rest_gap_hours) for r in rows["rest_records"] if r.personnel_id in affected and r.rest_gap_hours is not None and float(r.rest_gap_hours) >= 0 and r.data_quality_status == "OBSERVED"]
        staffing_required = sum(int(r.required_strength) for r in rows["staffing"])
        staffing_available = sum(int(r.available_strength) for r in rows["staffing"])
        complete_shifts = [
            shift for shift in rows["shift_requirements"]
            if start <= _utc(shift.start_at) and _utc(shift.end_at) <= end
        ]
        required_slots = sum(int(shift.required_count) for shift in complete_shifts)
        observed_slots = 0
        for shift in complete_shifts:
            fulfilled = {
                duty.personnel_id for duty in rows["duties"]
                if _utc(duty.start_at) == _utc(shift.start_at)
                and _utc(duty.end_at) == _utc(shift.end_at)
            }
            observed_slots += min(len(fulfilled), int(shift.required_count))
        return {
            "duty_hours": {
                "affected_total": round(sum(per_person_hours.values()), 4),
                "whole_unit_total": round(unit_hours, 4),
                "per_person": {k: round(v, 4) for k, v in sorted(per_person_hours.items())},
                "denominator_people": len(affected), "denominator_person_days": len(affected) * duration_days,
            },
            "night_duties": {
                "affected_total": sum(per_person_nights.values()),
                "per_person": dict(sorted(per_person_nights.items())),
                "denominator_people": len(affected),
            },
            "rest": {
                "mean_rest_hours": round(sum(rest_values) / len(rest_values), 4) if rest_values else None,
                "mean_rest_gap_hours": round(sum(gap_values) / len(gap_values), 4) if gap_values else None,
                "valid_rest_observations": len(rest_values),
                "valid_gap_observations": len(gap_values),
                "source_meaning": "recorded operational rest opportunity, not measured sleep quality",
            },
            "staffing": {
                "available_strength_sum": staffing_available,
                "required_strength_sum": staffing_required,
                "sample_days": len(rows["staffing"]),
                "ratio": round(staffing_available / staffing_required, 4) if staffing_required else None,
                "ratio_status": "VALID" if staffing_required else "NOT_COMPUTED",
            },
            "required_slots": {
                "fulfilled": observed_slots, "required": required_slots,
                "ratio": round(observed_slots / required_slots, 4) if required_slots else None,
                "status": "VALID" if required_slots else "NOT_COMPUTED",
                "source": "observed duty intervals matched to published shift demand",
            },
        }

    async def observe(self, scenario_id, clock=None):
        actor, scenario, impl, outcome = await self._context(scenario_id, lock=True)
        if actor.get("role") != "COMMANDER":
            raise HTTPException(403, "Commander authority required")
        if not impl or not outcome:
            raise HTTPException(409, "Confirmed implementation required")
        u = _utc(impl.effective_at)
        now = datetime.now(timezone.utc)
        if clock:
            if clock.tzinfo is None or not (impl.actual_assignments_json or {}).get("synthetic_replay"):
                raise HTTPException(422, "Certified synthetic replay clock required")
            now = _utc(clock)
        elif (impl.actual_assignments_json or {}).get("synthetic_replay"):
            return {**self._project(outcome), "reason_code": "SYNTHETIC_REPLAY_CLOCK_REQUIRED"}
        if outcome.observed_metrics_json.get("workflow_status") in ("OBSERVED", "REVIEWED"):
            data = dict(outcome.observed_metrics_json)
            if (data.get("leave_followup") or {}).get("status") in ("PENDING", "INSUFFICIENT_HISTORY") and now > u + timedelta(days=30):
                frozen = {uuid.UUID(value) for value in data.get("frozen_affected_personnel_ids", [])}
                data["leave_followup"] = await self._leave_followup(scenario.unit_id, frozen, u, now, impl.id)
                outcome.observed_metrics_json = data
                await self.audit.log_event(
                    actor_user_id=uuid.UUID(actor["user_id"]), actor_role="COMMANDER",
                    action="VERIFY_LEAVE_FOLLOWUP", resource_type="outcomes", resource_id=outcome.id,
                    metadata={"status": data["leave_followup"]["status"], "scenario_id": str(scenario_id)},
                )
            return self._project(outcome)
        before_start, after_end = u - timedelta(days=14), u + timedelta(days=14)
        if now < after_end:
            return {**self._project(outcome), "reason_code": "AFTER_WINDOW_NOT_COMPLETE"}
        policy = (await self.session.execute(select(PolicyConfig).where(
            PolicyConfig.policy_key == "verify.policy.VERIFY_POLICY_V1_SYNTHETIC_DEMO",
        ))).scalar_one_or_none()
        if not policy or policy.version != "VERIFY_POLICY_V1_SYNTHETIC_DEMO" or policy.policy_value_json.get("observation_duration_days") != 14:
            return {**self._project(outcome), "availability_status": "NOT_COMPUTED", "reason_code": "VERIFY_POLICY_UNAVAILABLE"}
        manifest = (await self.session.execute(select(PolicyConfig).where(
            PolicyConfig.policy_key == "verify.coverage." + str(impl.id),
        ))).scalar_one_or_none()
        claim = manifest.policy_value_json if manifest else {}
        if (not manifest or manifest.version != "SOURCE_COVERAGE_POLICY_V1_SYNTHETIC_DEMO"
                or claim.get("implementation_id") != str(impl.id)
                or claim.get("unit_id") != str(scenario.unit_id)
                or claim.get("effective_at") != u.isoformat()
                or claim.get("zero_unknown_gaps") is not True):
            return {**self._project(outcome), "availability_status": "INSUFFICIENT_HISTORY", "reason_code": "VERIFY_COVERAGE_UNAVAILABLE"}

        people = list((await self.session.execute(select(Personnel).where(
            Personnel.unit_id == scenario.unit_id,
        ))).scalars())
        ids = {person.id for person in people}
        frozen = {uuid.UUID(value) for value in outcome.observed_metrics_json.get("frozen_affected_personnel_ids", [])}
        if not frozen or not frozen <= ids:
            return {**self._project(outcome), "availability_status": "INSUFFICIENT_HISTORY", "reason_code": "AFFECTED_GROUP_UNAVAILABLE"}
        pseudo = {person.id: person.pseudo_id for person in people}
        before = await self._window_rows(scenario.unit_id, ids, before_start, u)
        after = await self._window_rows(scenario.unit_id, ids, u, after_end)
        evidence = {
            "before": self._coverage(claim, "before", before),
            "after": self._coverage(claim, "after", after),
        }
        if not all(item["certified"] for window in evidence.values() for item in window.values()):
            return {**self._project(outcome), "availability_status": "INSUFFICIENT_HISTORY", "reason_code": "VERIFY_SOURCE_CHANGED"}
        before_metrics = self._metrics(before, frozen, pseudo, before_start, u)
        after_metrics = self._metrics(after, frozen, pseudo, u, after_end)
        if (not before["rest_records"] or not after["rest_records"]
                or len({row.record_date for row in before["staffing"]}) != _complete_days(before_start, u)
                or len({row.record_date for row in after["staffing"]}) != _complete_days(u, after_end)
                or not before["shift_requirements"] or not after["shift_requirements"]):
            return {**self._project(outcome), "availability_status": "INSUFFICIENT_HISTORY", "reason_code": "MANDATORY_METRIC_MISSING"}
        if any(
            not any(
                row.personnel_id == person_id and row.rest_hours is not None
                and row.rest_gap_hours is not None and row.data_quality_status == "OBSERVED"
                for row in window["rest_records"]
            )
            for person_id in frozen for window in (before, after)
        ):
            return {**self._project(outcome), "availability_status": "INSUFFICIENT_HISTORY", "reason_code": "REST_COVERAGE_MISSING"}
        differences = {
            "affected_duty_hours": round(after_metrics["duty_hours"]["affected_total"] - before_metrics["duty_hours"]["affected_total"], 4),
            "affected_night_duties": after_metrics["night_duties"]["affected_total"] - before_metrics["night_duties"]["affected_total"],
            "mean_rest_hours": (
                round(after_metrics["rest"]["mean_rest_hours"] - before_metrics["rest"]["mean_rest_hours"], 4)
                if before_metrics["rest"]["mean_rest_hours"] is not None and after_metrics["rest"]["mean_rest_hours"] is not None else None
            ),
        }
        # Seven-factor WSI observations are optional, with compatible policy and
        # at least one valid observation for each frozen person in both windows.
        bw = [row for row in before["wsi_snapshots"] if row.personnel_id in frozen]
        aw = [row for row in after["wsi_snapshots"] if row.personnel_id in frozen]
        policies = {row.policy_version for row in bw + aw}
        wsi_claims_valid = all(
            (claim.get(label, {}).get("families", {}).get("wsi_snapshots") or {}).get("complete") is True
            and (claim[label]["families"]["wsi_snapshots"]).get("count") == len(rows["wsi_snapshots"])
            and (claim[label]["families"]["wsi_snapshots"]).get("hash") == _hash_rows(rows["wsi_snapshots"])
            for label, rows in (("before", before), ("after", after))
        )
        if (wsi_claims_valid and len(policies) == 1 and all(any(row.personnel_id == pid for row in bw)
            and any(row.personnel_id == pid for row in aw) for pid in frozen)):
            before_wsi = {pseudo[pid]: sum(float(row.wsi_score) for row in bw if row.personnel_id == pid)
                          / sum(row.personnel_id == pid for row in bw) for pid in frozen}
            after_wsi = {pseudo[pid]: sum(float(row.wsi_score) for row in aw if row.personnel_id == pid)
                         / sum(row.personnel_id == pid for row in aw) for pid in frozen}
            wsi = {
                "status": "VALID", "policy_version": next(iter(policies)),
                "before_mean": round(sum(before_wsi.values()) / len(before_wsi), 4),
                "after_mean": round(sum(after_wsi.values()) / len(after_wsi), 4),
                "before_peak": max(float(row.wsi_score) for row in bw),
                "after_peak": max(float(row.wsi_score) for row in aw),
                "per_person_change": {key: round(after_wsi[key] - before_wsi[key], 4) for key in sorted(before_wsi)},
                "observations": {"before": len(bw), "after": len(aw)},
            }
        else:
            wsi = {"status": "INSUFFICIENT_HISTORY", "value": None, "reason_code": "COMPATIBLE_WSI_COVERAGE_MISSING"}

        observed_constraints = {
            "before": _observed_constraints(before["duties"], before_start, u),
            "after": _observed_constraints(before["duties"] + after["duties"], u, after_end),
        }
        # Adherence compares approved new assignment pairs with observed duty
        # intervals; a zero-change proposal is explicitly NOT_APPLICABLE.
        current = {(str(item["shift_id"]), str(item["personnel_id"])) for item in (scenario.current_snapshot_json or {}).get("assignments", [])}
        proposed = {(str(item["shift_id"]), str(item["personnel_id"])) for item in (scenario.proposed_snapshot_json or {}).get("assignments", [])}
        approved_changes = proposed - current
        if not approved_changes:
            adherence = _adherence_summary(approved_changes, 0, 0)
        else:
            shift_ids = {uuid.UUID(shift) for shift, _ in approved_changes}
            shifts = {str(row.id): row for row in (await self.session.execute(select(ShiftRequirement).where(
                ShiftRequirement.id.in_(shift_ids),
            ))).scalars()}
            observable = [(shift, person) for shift, person in approved_changes
                          if shift in shifts and u <= _utc(shifts[shift].start_at)
                          and _utc(shifts[shift].end_at) <= after_end]
            observed = 0
            for shift, person in observable:
                requirement = shifts.get(shift)
                if requirement and any(
                    str(duty.personnel_id) == person
                    and _utc(duty.start_at) == _utc(requirement.start_at)
                    and _utc(duty.end_at) == _utc(requirement.end_at)
                    for duty in after["duties"]
                ):
                    observed += 1
            adherence = _adherence_summary(approved_changes, len(observable), observed)
        followup = await self._leave_followup(scenario.unit_id, frozen, u, now, impl.id)
        data = dict(outcome.observed_metrics_json)
        data.update({
            "workflow_status": "OBSERVED", "availability_status": "VALID",
            "observed_at": now.isoformat(),
            "policy_version": policy.version,
            "policy_hash": hashlib.sha256(json.dumps(policy.policy_value_json, sort_keys=True).encode()).hexdigest(),
            "coverage_evidence": evidence,
            "coverage_manifest_hash": hashlib.sha256(json.dumps(claim, sort_keys=True).encode()).hexdigest(),
            "calculation_version": "VERIFY_V1",
            "before_metrics": before_metrics, "after_metrics": after_metrics,
            "differences": differences, "wsi": wsi,
            "observed_constraint_violations": observed_constraints,
            "adherence": adherence, "leave_followup": followup,
            "interpretation": WARNING,
        })
        outcome.observed_metrics_json = data
        await self.audit.log_event(
            actor_user_id=uuid.UUID(actor["user_id"]), actor_role="COMMANDER",
            action="VERIFY_OBSERVED", resource_type="outcomes", resource_id=outcome.id,
            metadata={"status": "OBSERVED", "scenario_id": str(scenario_id), "implementation_id": str(impl.id)},
        )
        await NotificationService(self.session).emit(
            "VERIFY_AVAILABLE", uuid.UUID(actor["user_id"]), outcome.id,
            str(outcome.id) + ":OBSERVED",
        )
        return self._project(outcome)

    async def _leave_followup(self, unit_id, affected, u, clock, implementation_id):
        if clock <= u + timedelta(days=30):
            return {"status": "PENDING", "value": None}
        manifest = (await self.session.execute(select(PolicyConfig).where(
            PolicyConfig.policy_key == "verify.leave.coverage." + str(implementation_id),
        ))).scalar_one_or_none()
        if not manifest or manifest.version != "SOURCE_COVERAGE_POLICY_V1_SYNTHETIC_DEMO":
            return {"status": "INSUFFICIENT_HISTORY", "value": None}
        rows = list((await self.session.execute(select(LeaveRecord).where(
            LeaveRecord.personnel_id.in_(affected),
            LeaveRecord.start_date <= (u + timedelta(days=30)).date(),
            LeaveRecord.end_date >= u.date(),
        ))).scalars())
        claim = manifest.policy_value_json or {}
        if claim.get("complete") is not True or claim.get("count") != len(rows) or claim.get("hash") != _hash_rows(rows):
            return {"status": "INSUFFICIENT_HISTORY", "value": None}
        states = [classify_single_leave_record(row, u.date()) for row in rows]
        if LeaveTargetState.TARGET_UNAVAILABLE in states:
            return {"status": "INSUFFICIENT_HISTORY", "value": None}
        return {"status": "COMPLETE", "qualifying_event_observed": LeaveTargetState.POSITIVE in states,
                "eligible_rows": len(rows), "source_hash": _hash_rows(rows)}

    async def review(self, scenario_id, expected_revision, note):
        actor, _, impl, outcome = await self._context(scenario_id, lock=True)
        if actor.get("role") != "COMMANDER":
            raise HTTPException(403, "Commander authority required")
        if not impl or not outcome or outcome.observed_metrics_json.get("workflow_status") != "OBSERVED":
            raise HTTPException(409, "Observed outcome required")
        if expected_revision != _revision(outcome):
            raise HTTPException(409, "STALE_REVISION")
        clean_note = note.strip()
        if not 5 <= len(clean_note) <= 500:
            raise HTTPException(422, "Bounded operational review note required")
        data = dict(outcome.observed_metrics_json)
        data["workflow_status"] = "REVIEWED"
        data["review"] = {
            "actor_user_id": actor["user_id"],
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "note": clean_note,
        }
        outcome.observed_metrics_json = data
        await self.audit.log_event(
            actor_user_id=uuid.UUID(actor["user_id"]), actor_role="COMMANDER",
            action="VERIFY_REVIEWED", resource_type="outcomes", resource_id=outcome.id,
            metadata={"status": "REVIEWED", "scenario_id": str(scenario_id), "implementation_id": str(impl.id)},
        )
        return self._project(outcome)
