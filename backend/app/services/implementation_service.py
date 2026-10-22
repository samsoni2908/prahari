"""Record an external roster action after a governed Commander approval."""

from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
import uuid

from fastapi import HTTPException
from sqlalchemy import select, text

from app.models import AuditEvent, Outcome, ScenarioImplementation
from app.planning.adapter import PlanningSourceAdapter, compute_planning_context_hash
from app.planning.validator import validate_plan_with_evidence
from app.repositories.audit_repository import AuditRepository
from app.repositories.scenario_repository import ScenarioRepository
from app.security.scope import require_unit
from app.services.scenario_service import format_scenario_response


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _assignment_pairs(values):
    if not isinstance(values, list) or not values:
        raise HTTPException(422, "Actual assignments are required")
    pairs = set()
    normalized = []
    for item in values:
        if not isinstance(item, dict):
            raise HTTPException(422, "Invalid actual assignment")
        try:
            shift_id = uuid.UUID(str(item["shift_id"]))
            personnel_id = uuid.UUID(str(item["personnel_id"]))
        except (KeyError, ValueError, TypeError):
            raise HTTPException(422, "Shift and personnel identities are required")
        pair = (shift_id, personnel_id)
        if pair in pairs:
            raise HTTPException(422, "Duplicate actual assignment")
        pairs.add(pair)
        normalized.append({"shift_id": str(shift_id), "personnel_id": str(personnel_id)})
    normalized.sort(key=lambda entry: (entry["shift_id"], entry["personnel_id"]))
    return pairs, normalized


class ImplementationService:
    def __init__(self, session):
        self.session = session
        self.scenarios = ScenarioRepository(session)
        self.audit = AuditRepository(session)

    async def _receipt(self, scenario_id, actor_id, key_hash):
        return (await self.session.execute(select(AuditEvent).where(
            AuditEvent.resource_id == scenario_id,
            AuditEvent.actor_user_id == actor_id,
            AuditEvent.action.in_(("SCENARIO_IMPLEMENTED", "SCENARIO_NOT_IMPLEMENTED")),
            AuditEvent.metadata_json["idempotency_key_hash"].astext == key_hash,
            AuditEvent.result == "SUCCESS",
        ).order_by(AuditEvent.created_at.desc()).limit(1))).scalar_one_or_none()

    async def record(
        self, scenario_id, approval_id, result, expected_revision,
        idempotency_key, effective_at=None, actual_assignments=None,
        external_reference=None, reason_code=None, synthetic_replay_clock=None,
        confirm_approved_assignments=False,
    ):
        actor = self.session.info.get("actor") or {}
        if actor.get("role") != "COMMANDER":
            raise HTTPException(403, "Commander authority required")
        unit_id = require_unit(actor)
        actor_id = uuid.UUID(actor["user_id"])
        if result not in ("IMPLEMENTED", "NOT_IMPLEMENTED"):
            raise HTTPException(422, "Invalid implementation result")
        if not expected_revision or not idempotency_key or not idempotency_key.strip():
            raise HTTPException(422, "Expected revision and Idempotency-Key are required")
        if len(idempotency_key) > 200:
            raise HTTPException(422, "Invalid Idempotency-Key")

        payload = {
            "scenario_id": str(scenario_id), "approval_id": str(approval_id),
            "result": result, "expected_revision": expected_revision,
            "effective_at": effective_at.isoformat() if effective_at else None,
            "assignments": actual_assignments, "external_reference": external_reference,
            "reason_code": reason_code,
            "synthetic_replay_clock": synthetic_replay_clock.isoformat() if synthetic_replay_clock else None,
            "confirm_approved_assignments": confirm_approved_assignments,
        }
        request_hash = _digest(payload)
        key_hash = hashlib.sha256((str(actor_id) + ":" + idempotency_key.strip()).encode()).hexdigest()
        lock_id = int.from_bytes(hashlib.sha256(("IMPLEMENT:" + str(scenario_id) + ":" + key_hash).encode()).digest()[:8], "big", signed=True)
        await self.session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_id})

        scenario = await self.scenarios.lock_scenario(scenario_id)
        if scenario is None or scenario.unit_id != unit_id:
            raise HTTPException(404, "Scenario not found")
        receipt = await self._receipt(scenario_id, actor_id, key_hash)
        if receipt:
            metadata = receipt.metadata_json or {}
            if metadata.get("request_hash") != request_hash:
                raise HTTPException(409, "Idempotency key already used with different payload")
            return {
                "scenario_id": str(scenario_id), "result": metadata["status"],
                "implementation_id": metadata.get("implementation_id"),
                "recorded_at": receipt.created_at.isoformat(), "replay_safe": True,
            }
        if scenario.status != "APPROVED":
            raise HTTPException(409, "Current APPROVED scenario required")
        approval = await self.scenarios.get_approval(approval_id, scenario_id)
        latest = await self.scenarios.latest_approval(scenario_id)
        if not approval or approval.decision != "ACCEPT" or not latest or latest.id != approval.id:
            raise HTTPException(409, "Matching immutable ACCEPT approval required")
        revision = format_scenario_response(scenario, [], approval.id)["expected_revision"]
        if expected_revision != revision:
            raise HTTPException(409, "STALE_REVISION")

        ctx = (scenario.current_snapshot_json or {}).get("context", {})
        window = ctx.get("planning_window") or {}
        try:
            cutoff = datetime.fromisoformat(window["start_at"])
            window_end = datetime.fromisoformat(window["end_at"])
        except (KeyError, ValueError, TypeError):
            raise HTTPException(409, "Governed planning window missing")
        if cutoff.tzinfo is None or window_end.tzinfo is None or window_end - cutoff != timedelta(days=14):
            raise HTTPException(409, "Invalid governed planning window")
        now = datetime.now(timezone.utc)
        implementation_id = None
        if result == "IMPLEMENTED":
            snapshot = await PlanningSourceAdapter.load_snapshot_async(self.session, unit_id, cutoff)
            if (not snapshot.is_valid or snapshot.source_hash != ctx.get("source_hash")
                    or snapshot.policy_hash != ctx.get("policy_hash")
                    or snapshot.coverage_manifest.get("zero_unknown_gaps") is not True
                    or compute_planning_context_hash(snapshot) != ctx.get("source_context_hash")):
                raise HTTPException(409, "SOURCE_CHANGED")
            proposed = (scenario.proposed_snapshot_json or {}).get("assignments")
            proposed_pairs, _ = _assignment_pairs(proposed)
            if confirm_approved_assignments:
                if actual_assignments is not None:
                    raise HTTPException(422, "Confirmation mode cannot include actual_assignments")
                actual_assignments = [
                    {"shift_id": item["shift_id"], "personnel_id": item["personnel_id"]}
                    for item in proposed or []
                ]
            validation = validate_plan_with_evidence(
                shifts=snapshot.shift_requirements, assignments=proposed,
                availability=snapshot.availability_intervals,
                person_skills=snapshot.person_skills,
                unit_personnel=snapshot.personnel_ids,
                personnel_pseudo_map={p["id"]: p["pseudo_id"] for p in snapshot.personnel},
                approved_leaves=snapshot.approved_leaves, trainings=snapshot.trainings,
                deployments=snapshot.deployments, prior_duties=snapshot.prior_duties,
                window_start=cutoff, window_end=window_end,
                locked_baseline_assignments={
                    (uuid.UUID(str(a["shift_id"])), uuid.UUID(str(a["personnel_id"])))
                    for a in snapshot.current_assignments if a.get("is_locked")
                },
            )
            if not validation["all_hard_constraints_satisfied"]:
                raise HTTPException(409, "CONSTRAINTS_NO_LONGER_SATISFIED")
            if not external_reference or not external_reference.strip() or len(external_reference) > 120:
                raise HTTPException(422, "Bounded external operational reference required")
            if reason_code is not None:
                raise HTTPException(422, "Reason code is for NOT_IMPLEMENTED")
            actual_pairs, normalized = _assignment_pairs(actual_assignments)
            if actual_pairs != proposed_pairs:
                raise HTTPException(409, "ACTUAL_DIFFERS_FROM_APPROVED: New reviewed scenario required")
            if effective_at is None or effective_at.tzinfo is None:
                raise HTTPException(422, "Actual UTC effective time required")
            effective_at = effective_at.astimezone(timezone.utc)
            if not cutoff <= effective_at < window_end:
                raise HTTPException(409, "Effective time outside approved horizon")
            if synthetic_replay_clock:
                if synthetic_replay_clock.tzinfo is None:
                    raise HTTPException(422, "UTC synthetic replay clock required")
                replay_clock = synthetic_replay_clock.astimezone(timezone.utc)
                if (ctx.get("coverage") or {}).get("dataset_version") != "SYNTHETIC_DEMO_PLANNING_V1":
                    raise HTTPException(403, "Synthetic replay requires certified synthetic planning source")
                if not cutoff <= replay_clock < window_end or effective_at > replay_clock:
                    raise HTTPException(422, "Invalid synthetic replay clock")
            elif effective_at > now or window_end < now - timedelta(days=1):
                raise HTTPException(409, "Historical synthetic action requires visible replay clock")
            previous = await self.scenarios.implementation_for_approval(approval.id)
            if previous:
                raise HTTPException(409, "Implementation already recorded")
            record = ScenarioImplementation(
                id=uuid.uuid4(), scenario_id=scenario_id, approval_id=approval.id,
                status="IMPLEMENTED", implemented_by_user_id=actor_id,
                effective_at=effective_at,
                actual_assignments_json={
                    "schema_version": "1.0", "assignments": normalized,
                    "external_reference": external_reference.strip(),
                    "source_hash": snapshot.source_hash, "policy_hash": snapshot.policy_hash,
                    "commander_confirmed_as_approved": confirm_approved_assignments,
                    "synthetic_replay": synthetic_replay_clock is not None,
                    "replay_clock": synthetic_replay_clock.astimezone(timezone.utc).isoformat() if synthetic_replay_clock else None,
                },
                created_at=now, updated_at=now,
            )
            await self.scenarios.save_implementation(record)
            changes = await self.scenarios.get_changes(scenario_id)
            affected = set()
            for change in changes:
                affected.add(str(change.personnel_id))
                for value in (change.from_value, change.to_value):
                    if isinstance(value, dict):
                        for name in ("replaced_personnel_id", "assigned_personnel_id", "personnel_id"):
                            if value.get(name):
                                affected.add(str(uuid.UUID(str(value[name]))))
            if not affected:
                affected = {entry["personnel_id"] for entry in normalized}
            pending = Outcome(
                id=uuid.uuid5(uuid.NAMESPACE_URL, "prahari:verify-v1:" + str(record.id)),
                scenario_id=scenario_id, implementation_id=record.id,
                recorded_by_user_id=actor_id, observation_date=effective_at.date(),
                observed_metrics_json={
                    "schema_version": "VERIFY_V1", "workflow_status": "PENDING",
                    "availability_status": "NOT_COMPUTED",
                    "implementation_id": str(record.id),
                    "before_window": {
                        "start_at": (effective_at - timedelta(days=14)).isoformat(),
                        "end_at": effective_at.isoformat(),
                    },
                    "after_window": {
                        "start_at": effective_at.isoformat(),
                        "end_at": (effective_at + timedelta(days=14)).isoformat(),
                    },
                    "frozen_affected_personnel_ids": sorted(affected),
                    "source_hash": snapshot.source_hash,
                    "source_context_hash": compute_planning_context_hash(snapshot),
                    "policy_hash": snapshot.policy_hash,
                    "synthetic_replay": synthetic_replay_clock is not None,
                },
                wsi_change=None, operational_event_observed=None, notes=None,
                created_at=now,
            )
            await self.scenarios.record_outcome(pending)
            scenario.status = "IMPLEMENTED"
            implementation_id = str(record.id)
        else:
            if effective_at is not None or actual_assignments is not None or external_reference is not None or synthetic_replay_clock is not None or confirm_approved_assignments:
                raise HTTPException(422, "NOT_IMPLEMENTED cannot include actual action fields")
            if not reason_code or not re.fullmatch(r"[A-Z][A-Z0-9_]{2,39}", reason_code):
                raise HTTPException(422, "Bounded operational reason_code required")
            scenario.status = "NOT_IMPLEMENTED"

        action = "SCENARIO_IMPLEMENTED" if result == "IMPLEMENTED" else "SCENARIO_NOT_IMPLEMENTED"
        await self.audit.log_event(
            actor_user_id=actor_id, actor_role="COMMANDER", action=action,
            resource_type="roster_scenarios", resource_id=scenario_id, result="SUCCESS",
            metadata={
                "status": result, "scenario_id": str(scenario_id),
                "approval_id": str(approval.id), "implementation_id": implementation_id,
                "expected_revision": expected_revision, "source_hash": ctx.get("source_hash"),
                "policy_hash": ctx.get("policy_hash"), "idempotency_key_hash": key_hash,
                "request_hash": request_hash, "reason_code": reason_code,
                "commander_confirmed_as_approved": confirm_approved_assignments,
                "replay_clock": synthetic_replay_clock.astimezone(timezone.utc).isoformat() if synthetic_replay_clock else None,
            },
        )
        return {
            "scenario_id": str(scenario_id), "result": result,
            "implementation_id": implementation_id, "recorded_at": now.isoformat(),
            "replay_safe": False,
        }
