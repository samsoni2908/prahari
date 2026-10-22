"""Scenario Service for BALANCE What-If Roster Generation, Decision & Auditing.

Governed Stage-4B Service implementing:
- Strict typed planning source loading via PlanningSourceAdapter.
- Deterministic BALANCE optimization via DeterministicBalanceOptimizer.
- Server-derived optimistic concurrency control via expected_revision.
- Re-validation of source freshness and hard constraints before ACCEPT.
- Canonical state transitions: DRAFT -> FEASIBLE / INFEASIBLE / INPUT_UNAVAILABLE -> APPROVED / REJECTED / SUPERSEDED.
- Immutable decision audit trail and idempotency key handling.
- Strict Commander/Welfare pseudonymous privacy projection (no names, no personnel_code, zero private wellbeing).

BOUNDARIES:
- ACCEPT does NOT mutate live planning sources (shift_requirements, roster_assignments, availability_intervals, duties).
- ACCEPTANCE IS NOT IMPLEMENTATION.
"""

from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from typing import Any, Dict, List, Optional, Set
import uuid

from fastapi import HTTPException
from sqlalchemy import select, text

from app.models import (
    Approval,
    Outcome,
    RosterScenario,
    ScenarioChange,
    ScenarioImplementation,
)
from app.planning.adapter import PlanningSourceAdapter, PlanningSnapshot, compute_planning_context_hash
from app.planning.comparison import compute_scenario_comparison
from app.planning.optimizer import DeterministicBalanceOptimizer
from app.planning.revision import compute_expected_revision
from app.planning.validator import validate_plan_with_evidence
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.personnel_repository import PersonnelRepository
from app.repositories.scenario_repository import ScenarioRepository
from app.repositories.unit_repository import UnitRepository
from app.security.scope import require_unit


DEFAULT_CUTOFF = datetime(2026, 5, 14, 0, 0, 0, tzinfo=timezone.utc)
FORBIDDEN_REASON_TERMS = {
    "depression", "ptsd", "anxiety", "burnout", "mental health",
    "suicide", "psychological", "clinical", "unfit", "weak",
    "disorder", "diagnosis", "medical condition",
}


def format_scenario_response(
    scenario: RosterScenario,
    changes: List[ScenarioChange],
    latest_approval_id: Optional[uuid.UUID] = None,
) -> Dict[str, Any]:
    """Format scenario with pseudonymous projection and deterministic expected_revision."""
    ctx = scenario.current_snapshot_json.get("context", {}) if scenario.current_snapshot_json else {}
    window = ctx.get("planning_window", {})
    scenario_version = ctx.get("scenario_version", 1)
    parent_id = ctx.get("parent_id")
    source_hash = ctx.get("source_hash", "")
    policy_hash = ctx.get("policy_hash", "")
    policy_version = ctx.get("policy_version", "")

    expected_rev = compute_expected_revision(
        scenario_id=scenario.id,
        unit_id=scenario.unit_id,
        creator_user_id=scenario.created_by_user_id,
        scenario_version=scenario_version,
        parent_id=uuid.UUID(str(parent_id)) if parent_id else None,
        planning_window=window,
        source_hash=source_hash,
        policy_hash=policy_hash,
        status=scenario.status,
        current_snapshot_json=scenario.current_snapshot_json,
        proposed_snapshot_json=scenario.proposed_snapshot_json,
        before_metrics_json=scenario.before_metrics_json,
        after_metrics_json=scenario.after_metrics_json,
        constraint_results_json=scenario.constraint_results_json,
        optimizer_method=scenario.optimizer_method,
        created_at=scenario.created_at,
        latest_approval_id=latest_approval_id,
    )

    formatted_changes = []
    for c in changes:
        from_val = c.from_value or {}
        to_val = c.to_value or {}
        pseudo = to_val.get("assigned_pseudo_id") or from_val.get("replaced_pseudo_id") or str(c.personnel_id)[:8]
        sanitized_from = {k: v for k, v in from_val.items() if not k.endswith("personnel_id")}
        sanitized_to = {k: v for k, v in to_val.items() if not k.endswith("personnel_id")}
        formatted_changes.append({
            "id": str(c.id),
            "personnel_pseudo_id": pseudo,
            "change_type": c.change_type,
            "from_value": sanitized_from,
            "to_value": sanitized_to,
            "reason": c.reason,
        })

    return {
        "id": str(scenario.id),
        "expected_revision": expected_rev,
        "latest_approval_id": str(latest_approval_id) if latest_approval_id else None,
        "scenario_version": scenario_version,
        "parent_id": str(parent_id) if parent_id else None,
        "unit_id": str(scenario.unit_id),
        "scenario_name": scenario.scenario_name,
        "status": scenario.status,
        "window_start": window.get("start_at"),
        "window_end": window.get("end_at"),
        "source_hash": source_hash,
        "policy_version": policy_version,
        "optimizer_method": scenario.optimizer_method,
        "before_metrics": scenario.before_metrics_json,
        "after_metrics": scenario.after_metrics_json,
        "constraint_results": scenario.constraint_results_json,
        "changes": formatted_changes,
        "created_at": scenario.created_at.isoformat() if scenario.created_at else None,
    }


class ScenarioService:
    def __init__(
        self,
        scenario_repo: ScenarioRepository,
        unit_repo: UnitRepository,
        analytics_repo: AnalyticsRepository,
        personnel_repo: PersonnelRepository,
        audit_repo: AuditRepository,
    ):
        self.scenario_repo = scenario_repo
        self.unit_repo = unit_repo
        self.analytics_repo = analytics_repo
        self.personnel_repo = personnel_repo
        self.audit_repo = audit_repo

    async def create_what_if_scenario(
        self,
        unit_id: uuid.UUID,
        created_by_user_id: uuid.UUID,
        scenario_name: Optional[str] = None,
        cutoff: Optional[datetime] = None,
        idempotency_key: Optional[str] = None,
        target_reduction_percent: float = 15.0,
        is_welfare_draft: bool = False,
    ) -> Dict[str, Any]:
        """Create and evaluate a governed What-If balance scenario."""
        unit = await self.unit_repo.get_by_id(unit_id)
        if not unit:
            raise HTTPException(404, f"Unit {unit_id} not found")

        eval_cutoff = cutoff or DEFAULT_CUTOFF
        if eval_cutoff.tzinfo is None:
            eval_cutoff = eval_cutoff.replace(tzinfo=timezone.utc)

        # 1. Idempotency Key Handling via Transaction Lock & Audit Receipts
        key_hash = None
        req_hash = None
        if idempotency_key:
            key_hash = hashlib.sha256(idempotency_key.strip().encode("utf-8")).hexdigest()
            payload_str = f"{unit_id}:{scenario_name}:{eval_cutoff.isoformat()}:{is_welfare_draft}:{target_reduction_percent}"
            req_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

            # Transaction-scoped advisory lock prevents race conditions
            lock_id = int.from_bytes(hashlib.sha256(f"CREATE:{key_hash}".encode("utf-8")).digest()[:8], byteorder="big", signed=True)
            await self.scenario_repo.session.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": lock_id})

            # Check audit receipt first (authoritative store)
            receipt = await self.audit_repo.find_create_receipt_by_idempotency_hash(unit_id, key_hash)
            if receipt:
                m = receipt.metadata_json or {}
                if m.get("request_hash") == req_hash:
                    existing = await self.scenario_repo.get_by_id(receipt.resource_id)
                    if existing:
                        changes = await self.scenario_repo.get_changes(existing.id)
                        approval = await self.scenario_repo.latest_approval(existing.id)
                        res = format_scenario_response(existing, changes, approval.id if approval else None)
                        res["replay_safe"] = True
                        return res
                else:
                    raise HTTPException(409, "Idempotency key already used for a different request payload")

        # 2. Load planning snapshot
        snapshot = await PlanningSourceAdapter.load_snapshot_async(
            self.scenario_repo.session,
            unit_id=unit_id,
            cutoff=eval_cutoff,
        )

        name = scenario_name or (
            f"Welfare Workload Recommendation — {unit.unit_name}" if is_welfare_draft
            else f"Workload Balance — {unit.unit_name}"
        )

        scenario_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        if not snapshot.is_valid:
            # Truthful INPUT_UNAVAILABLE state
            scenario = RosterScenario(
                id=scenario_id,
                unit_id=unit_id,
                created_by_user_id=created_by_user_id,
                scenario_name=name,
                status="INPUT_UNAVAILABLE",
                current_snapshot_json={
                    "schema_version": "1.0",
                    "context": {
                        "scenario_version": 1,
                        "parent_id": None,
                        "planning_window": snapshot.planning_window,
                        "source_hash": snapshot.source_hash,
                        "source_context_hash": compute_planning_context_hash(snapshot),
                        "policy_version": snapshot.policy_version,
                        "policy_hash": snapshot.policy_hash,
                        "coverage": snapshot.coverage_manifest,
                        "idempotency_key_hash": key_hash,
                        "request_hash": req_hash,
                    },
                    "inputs": {},
                    "assignments": [],
                },
                proposed_snapshot_json={"schema_version": "1.0", "assignments": []},
                before_metrics_json=None,
                after_metrics_json=None,
                constraint_results_json={"status": "INPUT_UNAVAILABLE", "error": snapshot.error_message},
                optimizer_method="NOT_COMPUTED",
                created_at=now,
            )
            saved = await self.scenario_repo.create_scenario(scenario)
            await self.audit_repo.log_event(
                actor_user_id=created_by_user_id,
                actor_role="WELFARE_OFFICER" if is_welfare_draft else "COMMANDER",
                action="SCENARIO_CREATED_UNAVAILABLE",
                resource_type="roster_scenarios",
                resource_id=saved.id,
                result="FAILURE",
                metadata={
                    "source_hash": snapshot.source_hash or "INVALID",
                    "status": "INPUT_UNAVAILABLE",
                    "actor_role": "WELFARE_OFFICER" if is_welfare_draft else "COMMANDER",
                    "idempotency_key_hash": key_hash,
                    "request_hash": req_hash,
                    "unit_id": str(unit_id),
                },
            )
            return format_scenario_response(saved, [])

        # 3. Run Deterministic BALANCE Optimizer
        opt = DeterministicBalanceOptimizer()
        opt_res = opt.optimize(snapshot)

        current_snapshot = {
            "schema_version": "1.0",
            "context": {
                "scenario_version": 1,
                "parent_id": None,
                "planning_window": snapshot.planning_window,
                "source_hash": snapshot.source_hash,
                "source_context_hash": compute_planning_context_hash(snapshot),
                "policy_version": snapshot.policy_version,
                "policy_hash": snapshot.policy_hash,
                "coverage": snapshot.coverage_manifest,
                "idempotency_key_hash": key_hash,
                "request_hash": req_hash,
            },
            "inputs": {
                "shift_requirements_count": len(snapshot.shift_requirements),
                "assignments_count": len(snapshot.current_assignments),
                "availability_intervals_count": len(snapshot.availability_intervals),
            },
            "assignments": [
                {
                    "id": str(a["id"]),
                    "shift_id": str(a["shift_id"]),
                    "personnel_id": str(a["personnel_id"]),
                    "is_locked": bool(a.get("is_locked", False)),
                    "source_revision": str(a.get("source_revision", "")),
                }
                for a in snapshot.current_assignments
            ],
        }

        proposed_snapshot = {
            "schema_version": "1.0",
            "assignments": opt_res["proposed_assignments"],
        }

        scenario_status = "DRAFT" if is_welfare_draft and opt_res["status"] == "FEASIBLE" else opt_res["status"]
        scenario = RosterScenario(
            id=scenario_id,
            unit_id=unit_id,
            created_by_user_id=created_by_user_id,
            scenario_name=name,
            status=scenario_status,  # FEASIBLE | DRAFT | INFEASIBLE
            current_snapshot_json=current_snapshot,
            proposed_snapshot_json=proposed_snapshot,
            before_metrics_json=opt_res["before_metrics"],
            after_metrics_json=opt_res["after_metrics"],
            constraint_results_json=opt_res["constraint_results"],
            optimizer_method=opt_res["optimizer_method"],
            created_at=now,
        )
        saved = await self.scenario_repo.create_scenario(scenario)

        # 4. Save ScenarioChanges
        changes_to_save: List[ScenarioChange] = []
        for c in opt_res["changes"]:
            ch = ScenarioChange(
                id=uuid.uuid4(),
                scenario_id=saved.id,
                personnel_id=uuid.UUID(c["personnel_id"]),
                change_type=c["change_type"],
                from_value=c["from_value"],
                to_value=c["to_value"],
                reason=c["reason"],
                created_at=now,
            )
            saved_ch = await self.scenario_repo.add_change(ch)
            changes_to_save.append(saved_ch)

        # 5. Audit receipt
        actor_role = "WELFARE_OFFICER" if is_welfare_draft else "COMMANDER"
        action = "DRAFT_SCENARIO_CREATED" if is_welfare_draft else "SCENARIO_CREATED"
        await self.audit_repo.log_event(
            actor_user_id=created_by_user_id,
            actor_role=actor_role,
            action=action,
            resource_type="roster_scenarios",
            resource_id=saved.id,
            result="SUCCESS",
            metadata={
                "scenario_id": str(saved.id),
                "scenario_version": 1,
                "source_hash": snapshot.source_hash,
                "policy_hash": snapshot.policy_hash,
                "status": saved.status,
                "actor_role": actor_role,
                "idempotency_key_hash": key_hash,
                "request_hash": req_hash,
                "unit_id": str(unit_id),
            },
        )

        return format_scenario_response(saved, changes_to_save)

    async def list_scenarios(self, unit_id: uuid.UUID) -> List[Dict[str, Any]]:
        """List scenarios for a unit with pseudonymous summary."""
        scenarios = await self.scenario_repo.list_by_unit(unit_id)
        results = []
        for s in scenarios:
            changes = await self.scenario_repo.get_changes(s.id)
            approval = await self.scenario_repo.latest_approval(s.id)
            results.append(format_scenario_response(s, changes, approval.id if approval else None))
        return results

    async def get_scenario(self, scenario_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Retrieve single scenario detail with pseudonymous projection."""
        s = await self.scenario_repo.get_by_id(scenario_id)
        if not s:
            return None
        changes = await self.scenario_repo.get_changes(scenario_id)
        approval = await self.scenario_repo.latest_approval(scenario_id)
        return format_scenario_response(s, changes, approval.id if approval else None)

    async def get_comparison(self, scenario_id: uuid.UUID) -> Dict[str, Any]:
        """Retrieve current vs proposed comparative analysis."""
        s = await self.scenario_repo.get_by_id(scenario_id)
        if not s:
            raise HTTPException(404, "Scenario not found")
        changes = await self.scenario_repo.get_changes(scenario_id)
        changes_dicts = [
            {"change_type": c.change_type, "personnel_id": c.personnel_id, "from_value": c.from_value, "to_value": c.to_value}
            for c in changes
        ]
        return compute_scenario_comparison(
            before_metrics=s.before_metrics_json or {},
            after_metrics=s.after_metrics_json or {},
            changes=changes_dicts,
        )

    async def record_decision(
        self,
        scenario_id: uuid.UUID,
        user_id: uuid.UUID,
        decision: str,
        reason: str,
        expected_revision: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        target_reduction_percent: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Record human decision (ACCEPT / MODIFY / REJECT) with strict governance."""
        decision_upper = decision.upper().strip()
        if decision_upper not in ("ACCEPT", "MODIFY", "REJECT"):
            raise HTTPException(422, "Decision must be one of: ACCEPT, MODIFY, REJECT")
        actor = self.scenario_repo.session.info.get("actor", {})
        if actor.get("role") != "COMMANDER" or actor.get("user_id") != str(user_id):
            raise HTTPException(403, "Only authorized COMMANDER may decide roster scenarios")

        require_unit(actor)
        if decision_upper == "MODIFY" and target_reduction_percent is None:
            raise HTTPException(422, "MODIFY requires a target reduction for the revised proposal")
        if target_reduction_percent is not None and not 0 <= target_reduction_percent <= 100:
            raise HTTPException(422, "Target reduction must be between 0 and 100 percent")

        # Operational reason validation
        clean_reason = reason.strip()
        if len(clean_reason) < 5 or len(clean_reason) > 500:
            raise HTTPException(422, "Decision reason must be between 5 and 500 characters")

        lower_reason = clean_reason.lower()
        for term in FORBIDDEN_REASON_TERMS:
            if term in lower_reason:
                raise HTTPException(422, f"Reason must be operational only. Forbidden non-operational term: '{term}'")

        # Row lock scenario FOR UPDATE
        scenario = await self.scenario_repo.lock_scenario(scenario_id)
        if not scenario:
            raise HTTPException(404, "Scenario not found")

        # Verify unit scope
        if str(scenario.unit_id) != actor.get("unit_id"):
            raise HTTPException(403, "Commander cannot decide scenarios for other units")

        # 1. Idempotency Handling via Audit Receipts & Transaction Lock
        key_hash = None
        req_hash = None
        if idempotency_key:
            key_hash = hashlib.sha256(idempotency_key.strip().encode("utf-8")).hexdigest()
            payload_str = f"{scenario_id}:{decision_upper}:{clean_reason}:{expected_revision}:{target_reduction_percent}"
            req_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

            lock_id = int.from_bytes(hashlib.sha256(f"DECIDE:{key_hash}".encode("utf-8")).digest()[:8], byteorder="big", signed=True)
            await self.scenario_repo.session.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": lock_id})

            receipt = await self.audit_repo.find_decision_receipt_by_idempotency_hash(scenario_id, key_hash)
            if receipt:
                m = receipt.metadata_json or {}
                if m.get("request_hash") == req_hash:
                    # Safe idempotent replay from audit receipt
                    approval = await self.scenario_repo.latest_approval(scenario_id)
                    child_id = m.get("child_scenario_id")
                    child_scen = await self.scenario_repo.get_by_id(uuid.UUID(child_id)) if child_id else None
                    child_changes = await self.scenario_repo.get_changes(child_scen.id) if child_scen else []
                    return {
                        "scenario_id": str(scenario_id),
                        "approval_id": m.get("approval_id") or (str(approval.id) if approval else None),
                        "decision": m.get("decision") or (approval.decision if approval else decision_upper),
                        "status": m.get("status") or (scenario.status if scenario else "APPROVED"),
                        "reason": clean_reason,
                        "decided_at": (approval.decided_at if approval else datetime.now(timezone.utc)).isoformat(),
                        "replay_safe": True,
                        **({"child_scenario": format_scenario_response(child_scen, child_changes)} if child_scen else {}),
                    }
                else:
                    raise HTTPException(409, "Idempotency key already used for a different decision payload")

        # Check existing decision / approval
        previous = await self.scenario_repo.latest_approval(scenario_id)
        if previous:
            if previous.actor_user_id == user_id and previous.decision == decision_upper and previous.reason == clean_reason:
                # Safe idempotent retry
                return {
                    "scenario_id": str(scenario_id),
                    "approval_id": str(previous.id),
                    "decision": previous.decision,
                    "status": scenario.status,
                    "reason": previous.reason,
                    "decided_at": previous.decided_at.isoformat(),
                    "replay_safe": True,
                }
            raise HTTPException(409, "Scenario decision is already recorded with a terminal decision")

        if scenario.status in ("SUPERSEDED", "APPROVED", "REJECTED"):
            raise HTTPException(409, f"Cannot decide scenario in terminal status: {scenario.status}")

        # Check expected_revision
        changes = await self.scenario_repo.get_changes(scenario_id)
        current_rev = format_scenario_response(scenario, changes)["expected_revision"]
        if expected_revision and expected_revision.strip() != current_rev:
            await self.audit_repo.log_event(
                actor_user_id=user_id,
                actor_role="COMMANDER",
                action="STALE_REVISION_DENIAL",
                resource_type="roster_scenarios",
                resource_id=scenario_id,
                result="FAILURE",
                reason="Provided expected_revision does not match current server revision",
                metadata={"expected_revision": expected_revision, "status": "DENIED"},
            )
            raise HTTPException(409, "STALE_REVISION: Scenario has changed or revision token is stale")

        now = datetime.now(timezone.utc)

        # === 1. ACCEPT ===
        if decision_upper == "ACCEPT":
            if scenario.status != "FEASIBLE":
                raise HTTPException(409, f"ACCEPT is allowed ONLY when scenario.status == FEASIBLE. Current status: '{scenario.status}'")

            # FRESHNESS REVALIDATION: re-read DB planning sources
            ctx = (scenario.current_snapshot_json or {}).get("context", {})
            stored_source_hash = ctx.get("source_hash", "")
            stored_policy_hash = ctx.get("policy_hash", "")
            window = ctx.get("planning_window", {})
            cutoff = datetime.fromisoformat(window["start_at"]) if window.get("start_at") else DEFAULT_CUTOFF

            fresh_snap = await PlanningSourceAdapter.load_snapshot_async(
                self.scenario_repo.session,
                unit_id=scenario.unit_id,
                cutoff=cutoff,
            )

            # Check if planning source or policy changed
            if (not fresh_snap.is_valid or fresh_snap.source_hash != stored_source_hash
                    or fresh_snap.policy_hash != stored_policy_hash
                    or fresh_snap.coverage_manifest.get("zero_unknown_gaps") is not True
                    or compute_planning_context_hash(fresh_snap) != ctx.get("source_context_hash")):
                await self.audit_repo.log_event(
                    actor_user_id=user_id,
                    actor_role="COMMANDER",
                    action="SOURCE_CHANGED_DENIAL",
                    resource_type="roster_scenarios",
                    resource_id=scenario_id,
                    result="FAILURE",
                    reason="Planning source or policy changed since scenario creation",
                    metadata={"source_hash": fresh_snap.source_hash, "status": "SOURCE_CHANGED"},
                )
                raise HTTPException(409, "SOURCE_CHANGED: Planning sources or policies changed since scenario was created")

            # Re-validate proposed plan against fresh source evidence
            proposed_assignments = (scenario.proposed_snapshot_json or {}).get("assignments", [])
            fresh_val = validate_plan_with_evidence(
                shifts=fresh_snap.shift_requirements,
                assignments=proposed_assignments,
                availability=fresh_snap.availability_intervals,
                person_skills=fresh_snap.person_skills,
                unit_personnel=fresh_snap.personnel_ids,
                personnel_pseudo_map={p["id"]: p["pseudo_id"] for p in fresh_snap.personnel},
                approved_leaves=fresh_snap.approved_leaves,
                trainings=fresh_snap.trainings,
                deployments=fresh_snap.deployments,
                prior_duties=fresh_snap.prior_duties,
                window_start=cutoff,
                window_end=cutoff + timedelta(days=14),
            )

            if not fresh_val["all_hard_constraints_satisfied"]:
                raise HTTPException(409, "CONSTRAINTS_NO_LONGER_SATISFIED: Proposed plan no longer satisfies hard constraints")

            # Create immutable ACCEPT approval
            approval = Approval(
                id=uuid.uuid4(),
                scenario_id=scenario_id,
                actor_user_id=user_id,
                decision="ACCEPT",
                reason=clean_reason,
                decided_at=now,
            )
            await self.scenario_repo.record_approval(approval)

            # Update scenario status to APPROVED (IMPLEMENTATION_PENDING)
            scenario.status = "APPROVED"

            # CRITICAL: ACCEPT does NOT update published roster_assignments or shift_requirements!
            await self.audit_repo.log_event(
                actor_user_id=user_id,
                actor_role="COMMANDER",
                action="SCENARIO_APPROVED",
                resource_type="roster_scenarios",
                resource_id=scenario_id,
                result="SUCCESS",
                metadata={
                    "scenario_id": str(scenario_id),
                    "approval_id": str(approval.id),
                    "decision": "ACCEPT",
                    "status": "APPROVED",
                    "source_hash": fresh_snap.source_hash,
                    "policy_hash": fresh_snap.policy_hash,
                    "expected_revision": current_rev,
                    "idempotency_key_hash": key_hash,
                    "request_hash": req_hash,
                },
            )

            return {
                "scenario_id": str(scenario_id),
                "approval_id": str(approval.id),
                "decision": "ACCEPT",
                "status": "APPROVED",
                "reason": clean_reason,
                "decided_at": approval.decided_at.isoformat(),
            }

        # === 2. REJECT ===
        elif decision_upper == "REJECT":
            if scenario.status == "DRAFT":
                raise HTTPException(409, "REJECT is allowed ONLY on evaluated nonterminal scenarios. Current status is unevaluated 'DRAFT'")
            if scenario.status not in ("FEASIBLE", "INFEASIBLE", "INPUT_UNAVAILABLE"):
                raise HTTPException(409, f"REJECT is allowed ONLY on evaluated nonterminal scenarios (FEASIBLE, INFEASIBLE, INPUT_UNAVAILABLE). Current status: '{scenario.status}'")

            approval = Approval(
                id=uuid.uuid4(),
                scenario_id=scenario_id,
                actor_user_id=user_id,
                decision="REJECT",
                reason=clean_reason,
                decided_at=now,
            )
            await self.scenario_repo.record_approval(approval)
            scenario.status = "REJECTED"

            await self.audit_repo.log_event(
                actor_user_id=user_id,
                actor_role="COMMANDER",
                action="SCENARIO_REJECTED",
                resource_type="roster_scenarios",
                resource_id=scenario_id,
                result="SUCCESS",
                metadata={
                    "scenario_id": str(scenario_id),
                    "approval_id": str(approval.id),
                    "decision": "REJECT",
                    "status": "REJECTED",
                    "expected_revision": current_rev,
                    "idempotency_key_hash": key_hash,
                    "request_hash": req_hash,
                },
            )

            return {
                "scenario_id": str(scenario_id),
                "approval_id": str(approval.id),
                "decision": "REJECT",
                "status": "REJECTED",
                "reason": clean_reason,
                "decided_at": approval.decided_at.isoformat(),
            }

        # === 3. MODIFY ===
        elif decision_upper == "MODIFY":
            if scenario.status == "DRAFT":
                raise HTTPException(409, "MODIFY is allowed ONLY on evaluated nonterminal scenarios. Current status is unevaluated 'DRAFT'")
            if scenario.status not in ("FEASIBLE", "INFEASIBLE", "INPUT_UNAVAILABLE"):
                raise HTTPException(409, f"MODIFY is allowed ONLY on evaluated nonterminal scenarios (FEASIBLE, INFEASIBLE, INPUT_UNAVAILABLE). Current status: '{scenario.status}'")

            # Record MODIFY approval on parent
            approval = Approval(
                id=uuid.uuid4(),
                scenario_id=scenario_id,
                actor_user_id=user_id,
                decision="MODIFY",
                reason=clean_reason,
                decided_at=now,
            )
            await self.scenario_repo.record_approval(approval)
            scenario.status = "SUPERSEDED"

            # Create immutable child scenario
            ctx = (scenario.current_snapshot_json or {}).get("context", {})
            parent_version = ctx.get("scenario_version", 1)
            window = ctx.get("planning_window", {})
            cutoff = datetime.fromisoformat(window["start_at"]) if window.get("start_at") else DEFAULT_CUTOFF

            child_res = await self.create_what_if_scenario(
                unit_id=scenario.unit_id,
                created_by_user_id=user_id,
                scenario_name=f"{scenario.scenario_name} (Rev {parent_version + 1})",
                cutoff=cutoff,
                target_reduction_percent=target_reduction_percent,
            )

            # Update child scenario parent linkage
            child_id = uuid.UUID(child_res["id"])
            child_obj = await self.scenario_repo.lock_scenario(child_id)
            if child_obj and child_obj.current_snapshot_json:
                child_ctx = child_obj.current_snapshot_json.get("context", {})
                child_ctx["scenario_version"] = parent_version + 1
                child_ctx["parent_id"] = str(scenario.id)
                child_obj.current_snapshot_json["context"] = child_ctx

            await self.audit_repo.log_event(
                actor_user_id=user_id,
                actor_role="COMMANDER",
                action="SCENARIO_SUPERSEDED",
                resource_type="roster_scenarios",
                resource_id=scenario_id,
                result="SUCCESS",
                metadata={
                    "scenario_id": str(scenario_id),
                    "approval_id": str(approval.id),
                    "decision": "MODIFY",
                    "status": "SUPERSEDED",
                    "child_scenario_id": str(child_id),
                    "child_version": parent_version + 1,
                    "expected_revision": current_rev,
                    "idempotency_key_hash": key_hash,
                    "request_hash": req_hash,
                },
            )

            child_changes = await self.scenario_repo.get_changes(child_id)
            return {
                "parent_scenario_id": str(scenario_id),
                "parent_status": "SUPERSEDED",
                "approval_id": str(approval.id),
                "decision": "MODIFY",
                "reason": clean_reason,
                "child_scenario": format_scenario_response(child_obj, child_changes),
            }

    async def record_outcome(
        self,
        scenario_id: uuid.UUID,
        user_id: uuid.UUID,
        observed_wsi_change: float,
        operational_event_observed: bool,
        notes: Optional[str] = None,
        implementation_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """Preserved stub for future verification stages."""
        if not await self.scenario_repo.get_by_id(scenario_id):
            raise HTTPException(404, "Scenario not found")
        implementation = await self.scenario_repo.get_implementation(implementation_id, scenario_id) if implementation_id else None
        if not implementation or implementation.scenario_id != scenario_id:
            raise HTTPException(404, "Implementation not found")
        if implementation.status != "IMPLEMENTED":
            raise HTTPException(409, "Confirmed implementation required")
        outcome = Outcome(
            scenario_id=scenario_id,
            implementation_id=implementation.id,
            recorded_by_user_id=user_id,
            observation_date=date.today(),
            observed_metrics_json={"observed_wsi_change": observed_wsi_change, "verification_status": "NOT_COMPUTED", "source": "HUMAN_REPORTED"},
            wsi_change=observed_wsi_change,
            operational_event_observed=operational_event_observed,
            notes=notes,
        )
        saved = await self.scenario_repo.record_outcome(outcome)
        return {
            "id": str(saved.id),
            "scenario_id": str(saved.scenario_id),
            "implementation_id": str(saved.implementation_id),
            "verification_status": "NOT_COMPUTED",
            "wsi_change": float(saved.wsi_change) if saved.wsi_change is not None else None,
            "operational_event_observed": saved.operational_event_observed,
            "notes": saved.notes,
            "created_at": saved.created_at.isoformat(),
        }

    async def record_implementation(self, scenario_id, approval_id, status, effective_at=None, assignments=None):
        """Preserved stub for future verification stages."""
        actor = self.scenario_repo.session.info.get("actor", {})
        if actor.get("role") != "COMMANDER":
            raise HTTPException(403, "Operation not permitted")
        require_unit(actor)
        scenario = await self.scenario_repo.lock_scenario(scenario_id)
        if not scenario:
            raise HTTPException(404, "Scenario not found")
        approval = await self.scenario_repo.get_approval(approval_id, scenario_id)
        if not approval:
            raise HTTPException(404, "Approval not found")
        if approval.decision != "ACCEPT" or scenario.status != "APPROVED":
            raise HTTPException(409, "Accepted scenario decision required")
        if status not in ("IMPLEMENTATION_PENDING", "IMPLEMENTED", "NOT_IMPLEMENTED"):
            raise HTTPException(422, "Invalid implementation status")
        record = await self.scenario_repo.implementation_for_approval(approval_id)
        if not record:
            record = ScenarioImplementation(scenario_id=scenario_id, approval_id=approval_id)
        record.status = status
        record.effective_at = effective_at
        record.implemented_by_user_id = uuid.UUID(actor["user_id"]) if status == "IMPLEMENTED" else None
        record.actual_assignments_json = assignments
        record.updated_at = datetime.now(timezone.utc)
        await self.scenario_repo.save_implementation(record)
        return {"id": str(record.id), "scenario_id": str(record.scenario_id), "approval_id": str(record.approval_id), "status": record.status, "effective_at": record.effective_at}
