"""Service orchestrating planning source validation, idempotency, and transactional persistence."""

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set
import uuid

from sqlalchemy import delete, insert, select, text
from sqlalchemy.orm import Session

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
    User,
)
from app.planning.source_hash import compute_canonical_source_hash, compute_row_digest
from tools.data_generation.planning_generator import (
    DATASET_VERSION,
    DEMO_CUTOFF,
    DEMO_UNIT_ID,
    GENERATOR_VERSION,
    PLANNING_HORIZON_DAYS,
    SOURCE_REVISION,
    WINDOW_END,
    WINDOW_START,
    generate_synthetic_availability_intervals,
    generate_synthetic_published_assignments,
    generate_synthetic_shift_requirements,
)
from app.planning.validator import (
    PlanningValidationError,
    validate_availability_interval,
    validate_personnel_availability_coverage,
    validate_published_baseline_plan,
    validate_roster_assignment,
    validate_shift_requirement,
)


class PlanningSourceService:
    """Service handling validation, hashing, and loading of planning sources."""

    def __init__(self, db: Session):
        self.db = db

    def load_unit_context(self, unit_id: uuid.UUID, cutoff: datetime) -> Dict[str, Any]:
        """Fetch all necessary context from database for unit U02."""
        # 1. Active personnel
        personnel_stmt = (
            select(Personnel)
            .where(Personnel.unit_id == unit_id, Personnel.status == "ACTIVE")
            .order_by(Personnel.pseudo_id)
        )
        personnel = list(self.db.scalars(personnel_stmt).all())
        personnel_dicts = [
            {"id": p.id, "pseudo_id": p.pseudo_id, "personnel_code": p.personnel_code, "full_name": p.full_name}
            for p in personnel
        ]
        p_ids = {p.id for p in personnel}

        # 2. Skills
        skills_stmt = select(Skill).where(Skill.is_active == True)
        skills = {s.id: {"id": s.id, "skill_code": s.skill_code, "name": s.skill_name} for s in self.db.scalars(skills_stmt).all()}

        # 3. Person Skills
        ps_stmt = (
            select(PersonSkill)
            .where(PersonSkill.personnel_id.in_(p_ids))
            .where((PersonSkill.valid_until.is_(None)) | (PersonSkill.valid_until >= cutoff.date()))
        )
        person_skills: Dict[uuid.UUID, Dict[uuid.UUID, int]] = {}
        for ps in self.db.scalars(ps_stmt).all():
            person_skills.setdefault(ps.personnel_id, {})[ps.skill_id] = ps.proficiency_level

        # 4. Leave records overlapping 14d window
        window_end = cutoff + timedelta(days=PLANNING_HORIZON_DAYS)
        leave_stmt = (
            select(LeaveRecord)
            .where(LeaveRecord.personnel_id.in_(p_ids))
            .where(LeaveRecord.status == "APPROVED")
            .where(LeaveRecord.start_date < window_end.date())
            .where(LeaveRecord.end_date >= cutoff.date())
        )
        leaves = [
            {
                "id": l.id,
                "personnel_id": l.personnel_id,
                "start_date": l.start_date,
                "end_date": l.end_date,
                "status": l.status,
                "leave_type": l.leave_type,
            }
            for l in self.db.scalars(leave_stmt).all()
        ]

        # 5. Training overlapping 14d window
        tr_stmt = (
            select(Training)
            .where(Training.personnel_id.in_(p_ids))
            .where(Training.start_date < window_end.date())
            .where(Training.end_date >= cutoff.date())
        )
        trainings = [
            {
                "id": t.id,
                "personnel_id": t.personnel_id,
                "start_date": t.start_date,
                "end_date": t.end_date,
                "status": t.status,
                "training_name": t.training_name,
            }
            for t in self.db.scalars(tr_stmt).all()
        ]

        # 6. Deployments overlapping 14d window
        dep_stmt = (
            select(Deployment)
            .where(Deployment.personnel_id.in_(p_ids))
            .where(Deployment.start_date < window_end.date())
            .where((Deployment.end_date.is_(None)) | (Deployment.end_date >= cutoff.date()))
        )
        deployments = [
            {
                "id": d.id,
                "personnel_id": d.personnel_id,
                "start_date": d.start_date,
                "end_date": d.end_date,
                "deployment_type": d.deployment_type,
            }
            for d in self.db.scalars(dep_stmt).all()
        ]

        # 7. Prior duties in 7 days before cutoff [cutoff - 7d, cutoff)
        boundary_start = cutoff - timedelta(days=7)
        duty_stmt = (
            select(Duty)
            .where(Duty.personnel_id.in_(p_ids))
            .where(Duty.start_at >= boundary_start)
            .where(Duty.start_at < cutoff)
            .order_by(Duty.start_at)
        )
        prior_duties = [
            {
                "id": dt.id,
                "personnel_id": dt.personnel_id,
                "start_at": dt.start_at,
                "end_at": dt.end_at,
            }
            for dt in self.db.scalars(duty_stmt).all()
        ]

        return {
            "personnel": personnel_dicts,
            "personnel_ids": p_ids,
            "active_skills": skills,
            "person_skills": person_skills,
            "leaves": leaves,
            "trainings": trainings,
            "deployments": deployments,
            "prior_duties": prior_duties,
        }

    def import_synthetic_planning_data(
        self,
        unit_id: uuid.UUID = DEMO_UNIT_ID,
        cutoff: datetime = DEMO_CUTOFF,
        admin_user_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """Generate, validate, and import SYNTHETIC_DEMO_PLANNING_V1 transactionally."""
        ctx = self.load_unit_context(unit_id, cutoff)
        window_start = cutoff
        window_end = cutoff + timedelta(days=PLANNING_HORIZON_DAYS)

        # 1. Generate planning data
        shifts = generate_synthetic_shift_requirements(unit_id, window_start, PLANNING_HORIZON_DAYS, SOURCE_REVISION)
        availability = generate_synthetic_availability_intervals(
            ctx["personnel"], ctx["leaves"], ctx["trainings"], ctx["deployments"],
            window_start, window_end, SOURCE_REVISION
        )
        assignments = generate_synthetic_published_assignments(
            shifts, ctx["personnel"], ctx["person_skills"], availability, ctx["prior_duties"], SOURCE_REVISION
        )

        # 2. Validate shifts
        for s in shifts:
            validate_shift_requirement(s, ctx["active_skills"])

        # 3. Validate assignments
        valid_shift_ids = {s["id"] for s in shifts}
        for a in assignments:
            validate_roster_assignment(a, valid_shift_ids, ctx["personnel_ids"])

        # 4. Validate availability intervals
        for itv in availability:
            validate_availability_interval(itv)

        # 5. Validate complete availability coverage per person
        person_itvs: Dict[uuid.UUID, List[Dict[str, Any]]] = {}
        for itv in availability:
            person_itvs.setdefault(itv["personnel_id"], []).append(itv)
        for pid in ctx["personnel_ids"]:
            validate_personnel_availability_coverage(pid, person_itvs.get(pid, []), window_start, window_end)

        # 6. Validate published baseline plan against all 12 hard constraints
        constraint_report = validate_published_baseline_plan(
            shifts=shifts,
            assignments=assignments,
            availability=availability,
            person_skills=ctx["person_skills"],
            unit_personnel=ctx["personnel_ids"],
            approved_leaves=ctx["leaves"],
            trainings=ctx["trainings"],
            deployments=ctx["deployments"],
            prior_duties=ctx["prior_duties"],
            window_start=window_start,
            window_end=window_end,
        )

        # 7. Compute deterministic canonical source hash
        source_hash = compute_canonical_source_hash(shifts, assignments, availability)

        # 8. Check existing database rows for idempotency / conflict
        existing_shift_ids = set(self.db.scalars(select(ShiftRequirement.id).where(ShiftRequirement.id.in_(valid_shift_ids))).all())
        existing_assign_ids = set(self.db.scalars(select(RosterAssignment.id).where(RosterAssignment.id.in_({a["id"] for a in assignments}))).all())
        existing_avail_ids = set(self.db.scalars(select(AvailabilityInterval.id).where(AvailabilityInterval.id.in_({itv["id"] for itv in availability}))).all())

        if existing_shift_ids or existing_assign_ids or existing_avail_ids:
            # Check for conflict: verify if existing rows match exactly
            # Recompute source hash from DB to check exact match
            db_hash = self.compute_db_source_hash(unit_id, window_start, window_end)
            if db_hash == source_hash:
                # Safe replay
                return {
                    "status": "REPLAY_SAFE",
                    "dataset_version": DATASET_VERSION,
                    "generator_version": GENERATOR_VERSION,
                    "source_revision": SOURCE_REVISION,
                    "source_hash": source_hash,
                    "shifts_count": len(shifts),
                    "assignments_count": len(assignments),
                    "availability_count": len(availability),
                    "constraint_report": constraint_report,
                }
            else:
                raise PlanningValidationError("CONFLICT: Planning source with same IDs exists with different content")

        # 9. Perform transactional inserts
        for s in shifts:
            self.db.add(ShiftRequirement(**s))
        self.db.flush()

        for a in assignments:
            self.db.add(RosterAssignment(**a))
        self.db.flush()

        for itv in availability:
            self.db.add(AvailabilityInterval(**itv))
        self.db.flush()

        # 10. Admin user for policy activation
        if not admin_user_id:
            admin_user_id = self.db.scalar(select(User.id).where(User.role == "ADMIN", User.is_active == True))

        # 11. Create / update required policy_config representations
        now = datetime.now(timezone.utc)

        # A. BALANCE_SYNTHETIC_DEMO_POLICY_V1
        hard_policy = {
            "policy_name": "BALANCE_SYNTHETIC_DEMO_POLICY_V1",
            "planning_horizon_days": PLANNING_HORIZON_DAYS,
            "min_inter_duty_rest_hours": 8.0,
            "max_rolling_duty_hours": 60.0,
            "rolling_window_days": 7,
            "max_consecutive_duty_days": 6,
            "mandatory_constraints": [
                "demand_coverage",
                "required_skills",
                "operational_eligibility",
                "availability",
                "leave_restriction",
                "training_restriction",
                "deployment_restriction",
                "no_overlapping_assignments",
                "locked_assignments",
                "min_inter_duty_rest",
                "max_rolling_duty_hours",
                "max_consecutive_duty_days",
            ],
        }
        self._upsert_policy(
            key="balance.policy.BALANCE_SYNTHETIC_DEMO_POLICY_V1",
            value=hard_policy,
            version="BALANCE_SYNTHETIC_DEMO_POLICY_V1",
            admin_user_id=admin_user_id,
            now=now,
        )

        # B. BALANCE_SOFT_OBJECTIVE_POLICY_V1
        soft_policy = {
            "policy_name": "BALANCE_SOFT_OBJECTIVE_POLICY_V1",
            "objective_order": [
                {"rank": 1, "objective": "recovery_opportunity"},
                {"rank": 2, "objective": "workload_night_duty_distribution"},
                {"rank": 3, "objective": "assignment_disruption"},
            ],
            "combined_score": None,
            "weights": None,
        }
        self._upsert_policy(
            key="balance.policy.BALANCE_SOFT_OBJECTIVE_POLICY_V1",
            value=soft_policy,
            version="BALANCE_SOFT_OBJECTIVE_POLICY_V1",
            admin_user_id=admin_user_id,
            now=now,
        )

        # C. SOURCE_COVERAGE_POLICY_V1_SYNTHETIC_DEMO
        coverage_policy = {
            "policy_name": "SOURCE_COVERAGE_POLICY_V1_SYNTHETIC_DEMO",
            "horizon_days": PLANNING_HORIZON_DAYS,
            "unit_id": str(unit_id),
            "cutoff": cutoff.isoformat(),
            "zero_unknown_gaps": True,
            "source_hash": source_hash,
        }
        self._upsert_policy(
            key="balance.policy.SOURCE_COVERAGE_POLICY_V1_SYNTHETIC_DEMO",
            value=coverage_policy,
            version="SOURCE_COVERAGE_POLICY_V1_SYNTHETIC_DEMO",
            admin_user_id=admin_user_id,
            now=now,
        )

        # D. Planning Coverage Manifest
        manifest = {
            "unit_id": str(unit_id),
            "cutoff": cutoff.isoformat(),
            "planning_window": {
                "start": window_start.isoformat(),
                "end": window_end.isoformat(),
                "days": PLANNING_HORIZON_DAYS,
            },
            "policy_version": "SOURCE_COVERAGE_POLICY_V1_SYNTHETIC_DEMO",
            "dataset_version": DATASET_VERSION,
            "generator_version": GENERATOR_VERSION,
            "source_revision": SOURCE_REVISION,
            "shift_requirements_count": len(shifts),
            "roster_assignments_count": len(assignments),
            "availability_intervals_count": len(availability),
            "skills_validity_evidence": {
                "active_skills_checked": len(ctx["active_skills"]),
                "personnel_with_skills": len(ctx["person_skills"]),
            },
            "unit_membership_evidence": {
                "active_unit_personnel": len(ctx["personnel_ids"]),
            },
            "leave_restriction_evidence": {
                "approved_leaves_count": len(ctx["leaves"]),
            },
            "training_restriction_evidence": {
                "trainings_count": len(ctx["trainings"]),
            },
            "deployment_restriction_evidence": {
                "deployments_count": len(ctx["deployments"]),
            },
            "boundary_history_evidence": {
                "prior_7d_duties_count": len(ctx["prior_duties"]),
            },
            "zero_unknown_gaps": True,
            "source_hash": source_hash,
            "constraint_report": constraint_report,
        }
        self._upsert_policy(
            key=f"planning.coverage.{unit_id}.{cutoff.date().isoformat()}",
            value=manifest,
            version="SOURCE_COVERAGE_POLICY_V1_SYNTHETIC_DEMO",
            admin_user_id=admin_user_id,
            now=now,
        )

        self.db.commit()

        return {
            "status": "INSERTED",
            "dataset_version": DATASET_VERSION,
            "generator_version": GENERATOR_VERSION,
            "source_revision": SOURCE_REVISION,
            "source_hash": source_hash,
            "shifts_count": len(shifts),
            "assignments_count": len(assignments),
            "availability_count": len(availability),
            "manifest": manifest,
            "constraint_report": constraint_report,
        }

    def _upsert_policy(
        self,
        key: str,
        value: Any,
        version: str,
        admin_user_id: Optional[uuid.UUID],
        now: datetime,
    ) -> None:
        """Upsert a policy row in policy_config."""
        existing = self.db.scalar(select(PolicyConfig).where(PolicyConfig.policy_key == key))
        if existing:
            existing.policy_value_json = value
            existing.version = version
            existing.effective_from = now
            existing.updated_by_user_id = admin_user_id
        else:
            self.db.add(PolicyConfig(
                id=uuid.uuid4(),
                policy_key=key,
                policy_value_json=value,
                version=version,
                effective_from=now,
                updated_by_user_id=admin_user_id,
                created_at=now,
            ))
        self.db.flush()

    def compute_db_source_hash(
        self,
        unit_id: uuid.UUID,
        window_start: datetime,
        window_end: datetime,
    ) -> str:
        """Compute canonical source hash from actual database rows."""
        # Query shifts
        shift_stmt = (
            select(ShiftRequirement)
            .where(ShiftRequirement.unit_id == unit_id)
            .where(ShiftRequirement.start_at >= window_start)
            .where(ShiftRequirement.start_at < window_end)
            .order_by(ShiftRequirement.start_at, ShiftRequirement.id)
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
            for s in self.db.scalars(shift_stmt).all()
        ]
        s_ids = [s["id"] for s in shifts]

        # Query assignments
        assign_stmt = (
            select(RosterAssignment)
            .where(RosterAssignment.shift_id.in_(s_ids))
            .order_by(RosterAssignment.shift_id, RosterAssignment.personnel_id)
        )
        assignments = [
            {
                "id": a.id,
                "shift_id": a.shift_id,
                "personnel_id": a.personnel_id,
                "is_locked": a.is_locked,
                "source_revision": a.source_revision,
            }
            for a in self.db.scalars(assign_stmt).all()
        ]

        # Query availability intervals for unit personnel
        p_ids = list(self.db.scalars(
            select(Personnel.id).where(Personnel.unit_id == unit_id, Personnel.status == "ACTIVE")
        ).all())

        avail_stmt = (
            select(AvailabilityInterval)
            .where(AvailabilityInterval.personnel_id.in_(p_ids))
            .where(AvailabilityInterval.start_at < window_end)
            .where(AvailabilityInterval.end_at > window_start)
            .order_by(AvailabilityInterval.personnel_id, AvailabilityInterval.start_at, AvailabilityInterval.id)
        )
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
            for itv in self.db.scalars(avail_stmt).all()
        ]

        return compute_canonical_source_hash(shifts, assignments, availability)
