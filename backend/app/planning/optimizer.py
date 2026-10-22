"""Deterministic BALANCE Workload & Recovery Optimizer.

Algorithm:
1. Load and validate planning snapshot.
2. Validate baseline published plan with authoritative hard-constraint validator.
3. Compute schedule-based operational recovery and workload metrics.
4. Deterministically search for candidate swaps/reassignments that improve soft objectives.
5. Strictly validate every candidate against all 12 hard constraints (whole unit).
6. Lexicographical objective ranking (P1: Recovery -> P2: Night/Workload -> P3: Disruption).
7. Return validated best incumbent with execution status.

SAFETY & BOUNDARIES:
- Purely deterministic; NO random generators; stable ID tie-breaking.
- Locked assignments (Day 0 & Day 1) are IMMOVABLE.
- Whole-unit constraint validation on every candidate.
- NO numeric weighted formulas; NO opaque score.
- Projected WSI: NULL with PROJECTION_NOT_COMPUTED.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
import time
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

from app.planning.adapter import PlanningSnapshot
from app.planning.validator import validate_plan_with_evidence


@dataclass
class ScheduleMetrics:
    """Schedule-derived operational workload and recovery metrics."""
    total_duty_hours: float
    max_duty_hours_per_person: float
    min_duty_hours_per_person: float
    avg_duty_hours_per_person: float
    total_night_duties: int
    max_night_duties_per_person: int
    min_night_duties_per_person: int
    night_duty_variance: float
    max_consecutive_days: int
    min_rest_gap_hours: float
    short_rest_gaps_count: int  # count of rest gaps < 16h
    quick_returns_count: int    # count of rest gaps < 12h
    projected_wsi: Optional[float] = None
    projected_wsi_status: str = "PROJECTION_NOT_COMPUTED"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_duty_hours": round(self.total_duty_hours, 2),
            "max_duty_hours_per_person": round(self.max_duty_hours_per_person, 2),
            "min_duty_hours_per_person": round(self.min_duty_hours_per_person, 2),
            "avg_duty_hours_per_person": round(self.avg_duty_hours_per_person, 2),
            "total_night_duties": self.total_night_duties,
            "max_night_duties_per_person": self.max_night_duties_per_person,
            "min_night_duties_per_person": self.min_night_duties_per_person,
            "night_duty_variance": round(self.night_duty_variance, 4),
            "max_consecutive_days": self.max_consecutive_days,
            "min_rest_gap_hours": round(self.min_rest_gap_hours, 2),
            "short_rest_gaps_count": self.short_rest_gaps_count,
            "quick_returns_count": self.quick_returns_count,
            "projected_wsi": self.projected_wsi,
            "projected_wsi_status": self.projected_wsi_status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScheduleMetrics":
        return cls(
            total_duty_hours=float(data.get("total_duty_hours", 0.0)),
            max_duty_hours_per_person=float(data.get("max_duty_hours_per_person", 0.0)),
            min_duty_hours_per_person=float(data.get("min_duty_hours_per_person", 0.0)),
            avg_duty_hours_per_person=float(data.get("avg_duty_hours_per_person", 0.0)),
            total_night_duties=int(data.get("total_night_duties", 0)),
            max_night_duties_per_person=int(data.get("max_night_duties_per_person", 0)),
            min_night_duties_per_person=int(data.get("min_night_duties_per_person", 0)),
            night_duty_variance=float(data.get("night_duty_variance", 0.0)),
            max_consecutive_days=int(data.get("max_consecutive_days", 0)),
            min_rest_gap_hours=float(data.get("min_rest_gap_hours", 0.0)),
            short_rest_gaps_count=int(data.get("short_rest_gaps_count", 0)),
            quick_returns_count=int(data.get("quick_returns_count", 0)),
            projected_wsi=data.get("projected_wsi"),
            projected_wsi_status=data.get("projected_wsi_status", "PROJECTION_NOT_COMPUTED"),
        )


def compute_schedule_metrics(
    assignments: List[Dict[str, Any]],
    shifts: List[Dict[str, Any]],
    prior_duties: List[Dict[str, Any]],
    unit_personnel: Set[uuid.UUID],
    window_start: datetime,
) -> ScheduleMetrics:
    """Compute schedule-based operational metrics for a set of assignments."""
    shift_map = {uuid.UUID(str(s["id"])): s for s in shifts}
    person_duties: Dict[uuid.UUID, List[Tuple[datetime, datetime, bool]]] = {pid: [] for pid in unit_personnel}

    # Prior duties (marked as not in planning window)
    for pd in prior_duties:
        pid = uuid.UUID(str(pd["personnel_id"]))
        if pid in person_duties:
            s_t = pd["start_at"] if isinstance(pd["start_at"], datetime) else datetime.fromisoformat(pd["start_at"])
            e_t = pd["end_at"] if isinstance(pd["end_at"], datetime) else datetime.fromisoformat(pd["end_at"])
            if s_t.tzinfo is None:
                s_t = s_t.replace(tzinfo=timezone.utc)
            if e_t.tzinfo is None:
                e_t = e_t.replace(tzinfo=timezone.utc)
            person_duties[pid].append((s_t, e_t, False))

    # Assigned duties in planning horizon
    person_night_counts: Dict[uuid.UUID, int] = {pid: 0 for pid in unit_personnel}
    person_hours: Dict[uuid.UUID, float] = {pid: 0.0 for pid in unit_personnel}

    for a in assignments:
        sid = uuid.UUID(str(a["shift_id"]))
        pid = uuid.UUID(str(a["personnel_id"]))
        s_info = shift_map.get(sid)
        if not s_info or pid not in person_duties:
            continue
        s_t = s_info["start_at"] if isinstance(s_info["start_at"], datetime) else datetime.fromisoformat(s_info["start_at"])
        e_t = s_info["end_at"] if isinstance(s_info["end_at"], datetime) else datetime.fromisoformat(s_info["end_at"])
        if s_t.tzinfo is None:
            s_t = s_t.replace(tzinfo=timezone.utc)
        if e_t.tzinfo is None:
            e_t = e_t.replace(tzinfo=timezone.utc)
        person_duties[pid].append((s_t, e_t, True))

        dur_hours = (e_t - s_t).total_seconds() / 3600.0
        person_hours[pid] += dur_hours
        # Night shift indicator: start hour >= 20 or < 6
        if s_t.hour >= 20 or s_t.hour < 6:
            person_night_counts[pid] += 1

    # Aggregate duty hours
    hours_list = list(person_hours.values())
    total_hours = sum(hours_list)
    max_hours = max(hours_list) if hours_list else 0.0
    min_hours = min(hours_list) if hours_list else 0.0
    avg_hours = total_hours / len(hours_list) if hours_list else 0.0

    # Night duties distribution
    night_list = list(person_night_counts.values())
    total_night = sum(night_list)
    max_night = max(night_list) if night_list else 0
    min_night = min(night_list) if night_list else 0
    avg_night = total_night / len(night_list) if night_list else 0.0
    night_var = sum((n - avg_night) ** 2 for n in night_list) / len(night_list) if night_list else 0.0

    # Rest gaps and consecutive streaks
    min_rest = 999.0
    short_rest_count = 0
    quick_returns_count = 0
    max_consec = 0

    w_start = window_start.astimezone(timezone.utc) if window_start.tzinfo else window_start.replace(tzinfo=timezone.utc)

    for pid, d_list in person_duties.items():
        sorted_duties = sorted(d_list, key=lambda x: x[0])
        for i in range(len(sorted_duties) - 1):
            curr_e = sorted_duties[i][1]
            next_s = sorted_duties[i + 1][0]
            # Rest gap evaluation for transitions involving window shifts
            if next_s < w_start:
                continue
            gap = (next_s - curr_e).total_seconds() / 3600.0
            if gap < min_rest:
                min_rest = gap
            if gap < 16.0:
                short_rest_count += 1
            if gap < 12.0:
                quick_returns_count += 1

        # Consecutive days
        dates = sorted({d[0].date() for d in sorted_duties})
        streak = 0
        prev_d: Optional[date] = None
        for d in dates:
            if prev_d is None or d == prev_d + timedelta(days=1):
                streak += 1
            else:
                streak = 1
            if streak > max_consec:
                max_consec = streak
            prev_d = d

    if min_rest == 999.0:
        min_rest = 24.0

    return ScheduleMetrics(
        total_duty_hours=total_hours,
        max_duty_hours_per_person=max_hours,
        min_duty_hours_per_person=min_hours,
        avg_duty_hours_per_person=avg_hours,
        total_night_duties=total_night,
        max_night_duties_per_person=max_night,
        min_night_duties_per_person=min_night,
        night_duty_variance=night_var,
        max_consecutive_days=max_consec,
        min_rest_gap_hours=min_rest,
        short_rest_gaps_count=short_rest_count,
        quick_returns_count=quick_returns_count,
        projected_wsi=None,
        projected_wsi_status="PROJECTION_NOT_COMPUTED",
    )


def get_lexicographic_score(
    metrics: ScheduleMetrics,
    num_changes: int = 0,
    affected_personnel_count: int = 0,
) -> Tuple[Tuple[Any, ...], Tuple[Any, ...], Tuple[Any, ...]]:
    """Form lexicographic evaluation tuple: (Priority 1, Priority 2, Priority 3).

    Lower values in tuples are strictly preferred.
    """
    # Priority 1: Operational Recovery Opportunity
    # Want: fewer consecutive days, fewer short rest gaps (<16h), fewer quick returns (<12h), larger min rest
    p1 = (
        metrics.max_consecutive_days,
        metrics.quick_returns_count,
        metrics.short_rest_gaps_count,
        -round(metrics.min_rest_gap_hours, 2),
    )

    # Priority 2: Workload & Night-Duty Distribution
    # Want: lower max night duties per person, lower night variance, lower peak hours
    p2 = (
        metrics.max_night_duties_per_person,
        round(metrics.night_duty_variance, 4),
        round(metrics.max_duty_hours_per_person, 2),
    )

    # Priority 3: Disruption Minimization
    # Want: fewer assignment movements, fewer affected personnel
    p3 = (
        num_changes,
        affected_personnel_count,
    )

    return (p1, p2, p3)


def is_strictly_better(score_a: Tuple[Any, Any, Any], score_b: Tuple[Any, Any, Any]) -> bool:
    """Compare two candidate scores lexicographically."""
    p1_a, p2_a, p3_a = score_a
    p1_b, p2_b, p3_b = score_b

    if p1_a < p1_b:
        return True
    if p1_a > p1_b:
        return False

    # P1 is tied, evaluate P2
    if p2_a < p2_b:
        return True
    if p2_a > p2_b:
        return False

    # P2 is tied, evaluate P3
    return p3_a < p3_b


class DeterministicBalanceOptimizer:
    """Deterministic BALANCE optimizer implementing whole-unit constraint-governed rebalancing."""

    def __init__(self, time_budget_seconds: float = 4.0, max_iterations: int = 120):
        self.time_budget_seconds = time_budget_seconds
        self.max_iterations = max_iterations

    get_lexicographic_score = staticmethod(get_lexicographic_score)

    def optimize(self, snapshot: PlanningSnapshot) -> Dict[str, Any]:
        """Run deterministic rebalancing against the snapshot.

        Returns optimization result with status, proposed_assignments, changes, metrics, and constraints.
        """
        start_time = time.monotonic()

        if not snapshot.is_valid:
            return {
                "status": "INPUT_UNAVAILABLE",
                "reason_code": "PLANNING_SNAPSHOT_INVALID",
                "optimizer_method": "DETERMINISTIC_BALANCE_V1",
                "before_metrics": None,
                "after_metrics": None,
                "constraint_results": {"status": "INPUT_UNAVAILABLE", "error": snapshot.error_message},
                "changes": [],
                "proposed_snapshot": None,
                "execution": {"status": "FAILED", "reason": snapshot.error_message},
            }

        shifts = snapshot.shift_requirements
        current_assignments = snapshot.current_assignments
        availability = snapshot.availability_intervals
        person_skills = snapshot.person_skills
        unit_personnel = snapshot.personnel_ids
        pseudo_map = {p["id"]: p["pseudo_id"] for p in snapshot.personnel}
        window_start = snapshot.cutoff
        window_end = snapshot.cutoff + timedelta(days=snapshot.planning_window.get("days", 14))

        # 1. Identify locked baseline assignments (Day 0 & Day 1 are locked)
        locked_assignments: Set[Tuple[uuid.UUID, uuid.UUID]] = set()
        for a in current_assignments:
            if a.get("is_locked"):
                locked_assignments.add((uuid.UUID(str(a["shift_id"])), uuid.UUID(str(a["personnel_id"]))))

        # 2. Validate current plan
        baseline_val = validate_plan_with_evidence(
            shifts=shifts,
            assignments=current_assignments,
            availability=availability,
            person_skills=person_skills,
            unit_personnel=unit_personnel,
            personnel_pseudo_map=pseudo_map,
            approved_leaves=snapshot.approved_leaves,
            trainings=snapshot.trainings,
            deployments=snapshot.deployments,
            prior_duties=snapshot.prior_duties,
            window_start=window_start,
            window_end=window_end,
            locked_baseline_assignments=locked_assignments,
        )

        if not baseline_val["all_hard_constraints_satisfied"]:
            return {
                "status": "INFEASIBLE",
                "reason_code": "CURRENT_PLAN_INFEASIBLE",
                "optimizer_method": "DETERMINISTIC_BALANCE_V1",
                "before_metrics": None,
                "after_metrics": None,
                "constraint_results": baseline_val,
                "changes": [],
                "proposed_snapshot": None,
                "execution": {"status": "CURRENT_PLAN_INFEASIBLE", "reasons": baseline_val["failure_reasons"]},
            }

        # 3. Compute baseline metrics and initial score
        baseline_metrics = compute_schedule_metrics(
            assignments=current_assignments,
            shifts=shifts,
            prior_duties=snapshot.prior_duties,
            unit_personnel=unit_personnel,
            window_start=window_start,
        )
        best_score = get_lexicographic_score(baseline_metrics, 0, 0)
        best_assignments = list(current_assignments)
        best_metrics = baseline_metrics
        best_changes: List[Dict[str, Any]] = []

        # 4. Deterministic neighborhood search
        # Identify shifts and assignments that are UNLOCKED
        shift_map = {uuid.UUID(str(s["id"])): s for s in shifts}
        unlocked_shifts = [s for s in shifts if not s.get("is_locked")]
        unlocked_shift_ids = {uuid.UUID(str(s["id"])) for s in unlocked_shifts}

        # Sort personnel by pseudo_id for deterministic order
        sorted_personnel = sorted(snapshot.personnel, key=lambda p: str(p.get("pseudo_id", p["id"])))
        sorted_pids = [uuid.UUID(str(p["id"])) for p in sorted_personnel]

        # Map shift assignments: shift_id -> list of assigned pids
        shift_to_assigned: Dict[uuid.UUID, List[uuid.UUID]] = {sid: [] for sid in shift_map}
        for a in current_assignments:
            sid = uuid.UUID(str(a["shift_id"]))
            pid = uuid.UUID(str(a["personnel_id"]))
            shift_to_assigned[sid].append(pid)

        # Sort shifts deterministically by start_at then ID
        sorted_shifts = sorted(unlocked_shifts, key=lambda s: (s["start_at"], str(s["id"])))

        iterations = 0
        timed_out = False
        improved = True
        pass_count = 0
        max_passes = 10

        # Attempt deterministic pairwise duty swaps between eligible personnel across shifts
        # to level night duties and increase inter-duty rest
        while improved and pass_count < max_passes and not timed_out:
            improved = False
            pass_count += 1

            for i_s, s1 in enumerate(sorted_shifts):
                if timed_out or iterations >= self.max_iterations:
                    break
                s1_id = uuid.UUID(str(s1["id"]))
                s1_assigned = [pid for pid in shift_to_assigned[s1_id] if (s1_id, pid) not in locked_assignments]

                for s2 in sorted_shifts[i_s + 1:]:
                    if timed_out or iterations >= self.max_iterations:
                        break
                    s2_id = uuid.UUID(str(s2["id"]))
                    s2_assigned = [pid for pid in shift_to_assigned[s2_id] if (s2_id, pid) not in locked_assignments]

                    for p1 in s1_assigned:
                        for p2 in s2_assigned:
                            if p1 == p2:
                                continue

                            # Check time budget
                            if time.monotonic() - start_time > self.time_budget_seconds:
                                timed_out = True
                                break

                            iterations += 1
                            if iterations > self.max_iterations:
                                break

                            # Candidate swap: p1 takes s2, p2 takes s1
                            cand_assignments: List[Dict[str, Any]] = []
                            for a in best_assignments:
                                sid = uuid.UUID(str(a["shift_id"]))
                                pid = uuid.UUID(str(a["personnel_id"]))
                                if sid == s1_id and pid == p1:
                                    cand_assignments.append({**a, "personnel_id": p2})
                                elif sid == s2_id and pid == p2:
                                    cand_assignments.append({**a, "personnel_id": p1})
                                else:
                                    cand_assignments.append(a)

                            # Validate candidate against all 12 hard constraints (whole unit)
                            cand_val = validate_plan_with_evidence(
                                shifts=shifts,
                                assignments=cand_assignments,
                                availability=availability,
                                person_skills=person_skills,
                                unit_personnel=unit_personnel,
                                personnel_pseudo_map=pseudo_map,
                                approved_leaves=snapshot.approved_leaves,
                                trainings=snapshot.trainings,
                                deployments=snapshot.deployments,
                                prior_duties=snapshot.prior_duties,
                                window_start=window_start,
                                window_end=window_end,
                                locked_baseline_assignments=locked_assignments,
                            )

                            if cand_val["all_hard_constraints_satisfied"]:
                                cand_metrics = compute_schedule_metrics(
                                    assignments=cand_assignments,
                                    shifts=shifts,
                                    prior_duties=snapshot.prior_duties,
                                    unit_personnel=unit_personnel,
                                    window_start=window_start,
                                )
                                # Number of changes from published baseline
                                diff_count = sum(
                                    1 for c_a, b_a in zip(
                                        sorted(cand_assignments, key=lambda x: (str(x["shift_id"]), str(x["personnel_id"]))),
                                        sorted(current_assignments, key=lambda x: (str(x["shift_id"]), str(x["personnel_id"])))
                                    )
                                    if c_a["personnel_id"] != b_a["personnel_id"]
                                )
                                cand_score = get_lexicographic_score(cand_metrics, diff_count, 2)

                                if is_strictly_better(cand_score, best_score):
                                    best_score = cand_score
                                    best_assignments = cand_assignments
                                    best_metrics = cand_metrics
                                    # Rebuild shift_to_assigned cleanly
                                    shift_to_assigned = {sid: [] for sid in shift_map}
                                    for a in best_assignments:
                                        shift_to_assigned[uuid.UUID(str(a["shift_id"]))].append(uuid.UUID(str(a["personnel_id"])))
                                    improved = True
                                    break
                        if improved or timed_out:
                            break
                    if improved or timed_out:
                        break
                if improved or timed_out:
                    break

        # Compute diffs between baseline assignments and best_assignments
        changes: List[Dict[str, Any]] = []
        baseline_by_shift: Dict[uuid.UUID, Set[uuid.UUID]] = {sid: set() for sid in shift_map}
        for a in current_assignments:
            baseline_by_shift[uuid.UUID(str(a["shift_id"]))].add(uuid.UUID(str(a["personnel_id"])))

        proposed_by_shift: Dict[uuid.UUID, Set[uuid.UUID]] = {sid: set() for sid in shift_map}
        for a in best_assignments:
            proposed_by_shift[uuid.UUID(str(a["shift_id"]))].add(uuid.UUID(str(a["personnel_id"])))

        for sid, s in shift_map.items():
            removed_pids = baseline_by_shift[sid] - proposed_by_shift[sid]
            added_pids = proposed_by_shift[sid] - baseline_by_shift[sid]
            for rem_pid, add_pid in zip(sorted(removed_pids, key=str), sorted(added_pids, key=str)):
                s_start = s["start_at"].isoformat() if isinstance(s["start_at"], datetime) else s["start_at"]
                s_end = s["end_at"].isoformat() if isinstance(s["end_at"], datetime) else s["end_at"]
                changes.append({
                    "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{sid}:{rem_pid}:{add_pid}")),
                    "personnel_id": str(add_pid),
                    "pseudo_id": pseudo_map.get(add_pid, str(add_pid)[:8]),
                    "change_type": "REASSIGN",
                    "from_value": {
                        "shift_id": str(sid),
                        "replaced_personnel_id": str(rem_pid),
                        "replaced_pseudo_id": pseudo_map.get(rem_pid, str(rem_pid)[:8]),
                        "start_at": s_start,
                        "end_at": s_end,
                    },
                    "to_value": {
                        "shift_id": str(sid),
                        "assigned_personnel_id": str(add_pid),
                        "assigned_pseudo_id": pseudo_map.get(add_pid, str(add_pid)[:8]),
                        "start_at": s_start,
                        "end_at": s_end,
                    },
                    "reason": "Operational workload and recovery leveling",
                })

        # Final whole-unit validation of the incumbent
        final_val = validate_plan_with_evidence(
            shifts=shifts,
            assignments=best_assignments,
            availability=availability,
            person_skills=person_skills,
            unit_personnel=unit_personnel,
            personnel_pseudo_map=pseudo_map,
            approved_leaves=snapshot.approved_leaves,
            trainings=snapshot.trainings,
            deployments=snapshot.deployments,
            prior_duties=snapshot.prior_duties,
            window_start=window_start,
            window_end=window_end,
            locked_baseline_assignments=locked_assignments,
        )

        exec_status = "TIME_LIMIT" if timed_out else "COMPLETED"
        elapsed = time.monotonic() - start_time

        return {
            "status": "FEASIBLE" if final_val["all_hard_constraints_satisfied"] else "INFEASIBLE",
            "optimizer_method": "DETERMINISTIC_BALANCE_V1",
            "before_metrics": baseline_metrics.to_dict(),
            "after_metrics": best_metrics.to_dict(),
            "constraint_results": final_val,
            "changes": changes,
            "proposed_assignments": [
                {
                    "id": str(a["id"]),
                    "shift_id": str(a["shift_id"]),
                    "personnel_id": str(a["personnel_id"]),
                    "is_locked": a.get("is_locked", False),
                    "source_revision": a.get("source_revision", "SYNTHETIC_DEMO_PLANNING_V1"),
                }
                for a in best_assignments
            ],
            "execution": {
                "status": exec_status,
                "iterations": iterations,
                "elapsed_seconds": round(elapsed, 4),
                "validated_incumbent": final_val["all_hard_constraints_satisfied"],
            },
        }
