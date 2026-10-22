"""Planning Source Adapter for BALANCE and Scenario Evaluation.

Reads authoritative planning sources from the database, validates coverage
and provenance, recomputes the canonical length-prefixed SHA-256 source hash,
and produces a strict typed planning snapshot.

BOUNDARIES:
- Strictly operational planning data only.
- ZERO private wellbeing or Model-C data access.
- Validates that source hash reproduces expected digest.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AvailabilityInterval,
    Deployment,
    Duty,
    LeaveRecord,
    PersonSkill,
    Personnel,
    PolicyConfig,
    RosterAssignment,
    ShiftRequirement,
    Skill,
    Training,
    Unit,
)
from app.planning.source_hash import compute_canonical_source_hash, compute_row_digest, canonicalize_value


PLANNING_HORIZON_DAYS = 14
EXPECTED_DEMO_SOURCE_HASH = "98248f3ddab2e4b7801ea5f10f797fa115f1398ddba5c4867e56132bb20515aa"


@dataclass
class PlanningSnapshot:
    """Strict typed planning snapshot for BALANCE optimizer and scenario evaluation."""
    schema_version: str
    unit_id: uuid.UUID
    unit_code: str
    unit_name: str
    cutoff: datetime
    planning_window: Dict[str, Any]
    source_revision: str
    source_hash: str
    policy_version: str
    policy_hash: str
    coverage_manifest: Dict[str, Any]
    shift_requirements: List[Dict[str, Any]]
    current_assignments: List[Dict[str, Any]]
    availability_intervals: List[Dict[str, Any]]
    personnel: List[Dict[str, Any]]
    personnel_ids: Set[uuid.UUID]
    skills: Dict[uuid.UUID, Dict[str, Any]]
    person_skills: Dict[uuid.UUID, Dict[uuid.UUID, int]]
    approved_leaves: List[Dict[str, Any]]
    trainings: List[Dict[str, Any]]
    deployments: List[Dict[str, Any]]
    prior_duties: List[Dict[str, Any]]
    is_valid: bool
    status: str  # "VALID" | "INPUT_UNAVAILABLE" | "DATA_STALE"
    error_message: Optional[str] = None


def compute_policy_hash(policies: Dict[str, Any]) -> str:
    """Compute deterministic SHA-256 hash of active balance policies."""
    serialized = json.dumps(policies, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def compute_planning_context_hash(snapshot: PlanningSnapshot) -> str:
    """Bind the non-roster operational evidence used by BALANCE.

    The canonical Stage-4 planning-source hash remains unchanged. This second
    digest detects changed eligibility, skills, leave, training, deployment or
    boundary duties even when the three published planning tables are stable.
    """
    evidence = {
        "personnel": snapshot.personnel,
        "person_skills": {
            str(person): {str(skill): level for skill, level in sorted(skills.items(), key=lambda item: str(item[0]))}
            for person, skills in sorted(snapshot.person_skills.items(), key=lambda item: str(item[0]))
        },
        "approved_leaves": snapshot.approved_leaves,
        "trainings": snapshot.trainings,
        "deployments": snapshot.deployments,
        "prior_duties": snapshot.prior_duties,
        "coverage_manifest": snapshot.coverage_manifest,
    }
    normalized = canonicalize_value(evidence)
    for key in ("personnel", "approved_leaves", "trainings", "deployments", "prior_duties"):
        normalized[key].sort(key=lambda row: str(row.get("id", row.get("pseudo_id", ""))))
    return hashlib.sha256(json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class PlanningSourceAdapter:
    """Adapter reading and validating planning sources from synchronous or asynchronous DB sessions."""

    @staticmethod
    def load_snapshot_sync(
        session: Session,
        unit_id: uuid.UUID,
        cutoff: datetime,
    ) -> PlanningSnapshot:
        """Synchronously load and certify planning sources for a unit and cutoff."""
        if cutoff.tzinfo is None:
            cutoff = cutoff.replace(tzinfo=timezone.utc)
        else:
            cutoff = cutoff.astimezone(timezone.utc)

        window_start = cutoff
        window_end = cutoff + timedelta(days=PLANNING_HORIZON_DAYS)

        # 1. Unit existence
        unit = session.scalar(select(Unit).where(Unit.id == unit_id))
        if not unit:
            return PlanningSnapshot(
                schema_version="1.0",
                unit_id=unit_id,
                unit_code="",
                unit_name="",
                cutoff=cutoff,
                planning_window={"start_at": window_start.isoformat(), "end_at": window_end.isoformat(), "days": PLANNING_HORIZON_DAYS},
                source_revision="",
                source_hash="",
                policy_version="",
                policy_hash="",
                coverage_manifest={},
                shift_requirements=[],
                current_assignments=[],
                availability_intervals=[],
                personnel=[],
                personnel_ids=set(),
                skills={},
                person_skills={},
                approved_leaves=[],
                trainings=[],
                deployments=[],
                prior_duties=[],
                is_valid=False,
                status="INPUT_UNAVAILABLE",
                error_message=f"Unit {unit_id} not found",
            )

        # 2. Active unit personnel
        p_stmt = (
            select(Personnel)
            .where(Personnel.unit_id == unit_id, Personnel.status == "ACTIVE")
            .order_by(Personnel.pseudo_id)
        )
        personnel_rows = list(session.scalars(p_stmt).all())
        if not personnel_rows:
            return PlanningSnapshot(
                schema_version="1.0",
                unit_id=unit_id,
                unit_code=unit.unit_code,
                unit_name=unit.unit_name,
                cutoff=cutoff,
                planning_window={"start_at": window_start.isoformat(), "end_at": window_end.isoformat(), "days": PLANNING_HORIZON_DAYS},
                source_revision="",
                source_hash="",
                policy_version="",
                policy_hash="",
                coverage_manifest={},
                shift_requirements=[],
                current_assignments=[],
                availability_intervals=[],
                personnel=[],
                personnel_ids=set(),
                skills={},
                person_skills={},
                approved_leaves=[],
                trainings=[],
                deployments=[],
                prior_duties=[],
                is_valid=False,
                status="INPUT_UNAVAILABLE",
                error_message="No active personnel found for unit",
            )

        personnel_dicts = [
            {"id": p.id, "pseudo_id": p.pseudo_id, "rank_or_grade": p.rank_or_grade, "role_title": p.role_title}
            for p in personnel_rows
        ]
        p_ids = {p.id for p in personnel_rows}

        # 3. Read shift requirements in planning window [window_start, window_end)
        s_stmt = (
            select(ShiftRequirement)
            .where(ShiftRequirement.unit_id == unit_id)
            .where(ShiftRequirement.start_at >= window_start)
            .where(ShiftRequirement.start_at < window_end)
            .order_by(ShiftRequirement.start_at, ShiftRequirement.id)
        )
        shift_rows = list(session.scalars(s_stmt).all())
        if not shift_rows:
            return PlanningSnapshot(
                schema_version="1.0",
                unit_id=unit_id,
                unit_code=unit.unit_code,
                unit_name=unit.unit_name,
                cutoff=cutoff,
                planning_window={"start_at": window_start.isoformat(), "end_at": window_end.isoformat(), "days": PLANNING_HORIZON_DAYS},
                source_revision="",
                source_hash="",
                policy_version="",
                policy_hash="",
                coverage_manifest={},
                shift_requirements=[],
                current_assignments=[],
                availability_intervals=[],
                personnel=personnel_dicts,
                personnel_ids=p_ids,
                skills={},
                person_skills={},
                approved_leaves=[],
                trainings=[],
                deployments=[],
                prior_duties=[],
                is_valid=False,
                status="INPUT_UNAVAILABLE",
                error_message="No shift requirements found for planning horizon",
            )

        shifts = [
            {
                "id": s.id,
                "unit_id": s.unit_id,
                "start_at": s.start_at,
                "end_at": s.end_at,
                "required_count": s.required_count,
                "required_skills_json": s.required_skills_json,
                "is_locked": s.is_locked,
                "source_revision": s.source_revision,
            }
            for s in shift_rows
        ]
        s_ids = [s["id"] for s in shifts]

        # 4. Read roster assignments for shifts
        a_stmt = (
            select(RosterAssignment)
            .where(RosterAssignment.shift_id.in_(s_ids))
            .order_by(RosterAssignment.shift_id, RosterAssignment.personnel_id)
        )
        assign_rows = list(session.scalars(a_stmt).all())
        assignments = [
            {
                "id": a.id,
                "shift_id": a.shift_id,
                "personnel_id": a.personnel_id,
                "is_locked": a.is_locked,
                "source_revision": a.source_revision,
            }
            for a in assign_rows
        ]

        # 5. Read availability intervals overlapping [window_start, window_end)
        av_stmt = (
            select(AvailabilityInterval)
            .where(AvailabilityInterval.personnel_id.in_(p_ids))
            .where(AvailabilityInterval.start_at < window_end)
            .where(AvailabilityInterval.end_at > window_start)
            .order_by(AvailabilityInterval.personnel_id, AvailabilityInterval.start_at, AvailabilityInterval.id)
        )
        avail_rows = list(session.scalars(av_stmt).all())
        availability = [
            {
                "id": itv.id,
                "personnel_id": itv.personnel_id,
                "start_at": itv.start_at,
                "end_at": itv.end_at,
                "state": itv.state,
                "reason_code": itv.reason_code,
                "source_revision": itv.source_revision,
            }
            for itv in avail_rows
        ]

        # 6. Recompute Canonical Planning Source Hash from actual DB rows
        recomputed_source_hash = compute_canonical_source_hash(shifts, assignments, availability)

        # 7. Policies and Coverage Manifest from policy_config
        manifest_key = f"planning.coverage.{unit_id}.{cutoff.date().isoformat()}"
        manifest_row = session.scalar(select(PolicyConfig).where(PolicyConfig.policy_key == manifest_key))
        manifest = manifest_row.policy_value_json if manifest_row else {}

        hard_policy_row = session.scalar(select(PolicyConfig).where(PolicyConfig.policy_key == "balance.policy.BALANCE_SYNTHETIC_DEMO_POLICY_V1"))
        soft_policy_row = session.scalar(select(PolicyConfig).where(PolicyConfig.policy_key == "balance.policy.BALANCE_SOFT_OBJECTIVE_POLICY_V1"))
        cov_policy_row = session.scalar(select(PolicyConfig).where(PolicyConfig.policy_key == "balance.policy.SOURCE_COVERAGE_POLICY_V1_SYNTHETIC_DEMO"))

        active_policies = {
            "hard": hard_policy_row.policy_value_json if hard_policy_row else {},
            "soft": soft_policy_row.policy_value_json if soft_policy_row else {},
            "coverage": cov_policy_row.policy_value_json if cov_policy_row else {},
        }
        policy_hash = compute_policy_hash(active_policies)
        policy_version = hard_policy_row.version if hard_policy_row else "UNKNOWN_POLICY"

        # Check coverage certification and manifest hash match
        if manifest:
            expected_hash = manifest.get("source_hash")
            if expected_hash and expected_hash != recomputed_source_hash:
                return PlanningSnapshot(
                    schema_version="1.0",
                    unit_id=unit_id,
                    unit_code=unit.unit_code,
                    unit_name=unit.unit_name,
                    cutoff=cutoff,
                    planning_window={"start_at": window_start.isoformat(), "end_at": window_end.isoformat(), "days": PLANNING_HORIZON_DAYS},
                    source_revision=shifts[0]["source_revision"] if shifts else "",
                    source_hash=recomputed_source_hash,
                    policy_version=policy_version,
                    policy_hash=policy_hash,
                    coverage_manifest=manifest,
                    shift_requirements=shifts,
                    current_assignments=assignments,
                    availability_intervals=availability,
                    personnel=personnel_dicts,
                    personnel_ids=p_ids,
                    skills={},
                    person_skills={},
                    approved_leaves=[],
                    trainings=[],
                    deployments=[],
                    prior_duties=[],
                    is_valid=False,
                    status="DATA_STALE",
                    error_message=f"Source hash mismatch: recomputed {recomputed_source_hash} != manifest {expected_hash}",
                )

        # 8. Skills and PersonSkills
        skills_stmt = select(Skill).where(Skill.is_active == True)
        skills_dict = {s.id: {"id": s.id, "skill_code": s.skill_code, "name": s.skill_name} for s in session.scalars(skills_stmt).all()}

        ps_stmt = (
            select(PersonSkill)
            .where(PersonSkill.personnel_id.in_(p_ids))
            .where((PersonSkill.valid_until.is_(None)) | (PersonSkill.valid_until >= cutoff.date()))
        )
        person_skills: Dict[uuid.UUID, Dict[uuid.UUID, int]] = {}
        for ps in session.scalars(ps_stmt).all():
            person_skills.setdefault(ps.personnel_id, {})[ps.skill_id] = ps.proficiency_level

        # 9. Leaves, Trainings, Deployments
        leave_stmt = (
            select(LeaveRecord)
            .where(LeaveRecord.personnel_id.in_(p_ids))
            .where(LeaveRecord.status == "APPROVED")
            .where(LeaveRecord.start_date < window_end.date())
            .where(LeaveRecord.end_date >= cutoff.date())
        )
        leaves = [
            {"id": l.id, "personnel_id": l.personnel_id, "start_date": l.start_date, "end_date": l.end_date, "status": l.status, "leave_type": l.leave_type}
            for l in session.scalars(leave_stmt).all()
        ]

        tr_stmt = (
            select(Training)
            .where(Training.personnel_id.in_(p_ids))
            .where(Training.start_date < window_end.date())
            .where(Training.end_date >= cutoff.date())
        )
        trainings = [
            {"id": t.id, "personnel_id": t.personnel_id, "start_date": t.start_date, "end_date": t.end_date, "status": t.status, "training_name": t.training_name}
            for t in session.scalars(tr_stmt).all()
        ]

        dep_stmt = (
            select(Deployment)
            .where(Deployment.personnel_id.in_(p_ids))
            .where(Deployment.start_date < window_end.date())
            .where((Deployment.end_date.is_(None)) | (Deployment.end_date >= cutoff.date()))
        )
        deployments = [
            {"id": d.id, "personnel_id": d.personnel_id, "start_date": d.start_date, "end_date": d.end_date, "deployment_type": d.deployment_type}
            for d in session.scalars(dep_stmt).all()
        ]

        # 10. Prior duties in [cutoff - 7d, cutoff) for boundary checks
        prior_start = cutoff - timedelta(days=7)
        duty_stmt = (
            select(Duty)
            .where(Duty.personnel_id.in_(p_ids))
            .where(Duty.start_at < cutoff)
            .where(Duty.end_at > prior_start)
            .order_by(Duty.start_at)
        )
        prior_duties = [
            {"id": dt.id, "personnel_id": dt.personnel_id, "start_at": dt.start_at, "end_at": dt.end_at}
            for dt in session.scalars(duty_stmt).all()
        ]

        source_rev = shifts[0]["source_revision"] if shifts else "SYNTHETIC_DEMO_PLANNING_V1"

        return PlanningSnapshot(
            schema_version="1.0",
            unit_id=unit_id,
            unit_code=unit.unit_code,
            unit_name=unit.unit_name,
            cutoff=cutoff,
            planning_window={"start_at": window_start.isoformat(), "end_at": window_end.isoformat(), "days": PLANNING_HORIZON_DAYS},
            source_revision=source_rev,
            source_hash=recomputed_source_hash,
            policy_version=policy_version,
            policy_hash=policy_hash,
            coverage_manifest=manifest,
            shift_requirements=shifts,
            current_assignments=assignments,
            availability_intervals=availability,
            personnel=personnel_dicts,
            personnel_ids=p_ids,
            skills=skills_dict,
            person_skills=person_skills,
            approved_leaves=leaves,
            trainings=trainings,
            deployments=deployments,
            prior_duties=prior_duties,
            is_valid=True,
            status="VALID",
            error_message=None,
        )

    @staticmethod
    async def load_snapshot_async(
        session: AsyncSession,
        unit_id: uuid.UUID,
        cutoff: datetime,
    ) -> PlanningSnapshot:
        """Asynchronously load and certify planning sources by running the synchronous extractor via run_sync."""
        return await session.run_sync(
            lambda sync_session: PlanningSourceAdapter.load_snapshot_sync(sync_session, unit_id, cutoff)
        )
