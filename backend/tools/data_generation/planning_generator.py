"""Deterministic synthetic planning generator for Stage-4A planning sources.

Dataset: SYNTHETIC_DEMO_PLANNING_V1
Generator Version: v1.0-stage4a
Seed: 26186
Source Revision: SYNTHETIC_DEMO_PLANNING_V1
Unit: U02 (1st Battalion, e09b8af8-d4b9-c3c1-bc35-89ed1a295ca2)
Cutoff: 2026-05-14 00:00:00 UTC
Planning Horizon: 14 days [2026-05-14 00:00:00 UTC, 2026-05-28 00:00:00 UTC)
"""

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

PLANNING_NAMESPACE = uuid.UUID("d2618600-4a00-4000-8000-000000000001")
DATASET_VERSION = "SYNTHETIC_DEMO_PLANNING_V1"
GENERATOR_VERSION = "v1.0-stage4a"
SOURCE_REVISION = "SYNTHETIC_DEMO_PLANNING_V1"
FIXED_SEED = 26186

DEMO_UNIT_ID = uuid.UUID("e09b8af8-d4b9-c3c1-bc35-89ed1a295ca2")
DEMO_CUTOFF = datetime(2026, 5, 14, 0, 0, 0, tzinfo=timezone.utc)
PLANNING_HORIZON_DAYS = 14
WINDOW_START = DEMO_CUTOFF
WINDOW_END = DEMO_CUTOFF + timedelta(days=PLANNING_HORIZON_DAYS)

# Key skill UUIDs from physical database (verified active)
SKILL_WEAPONS_HANDLING = uuid.UUID("0c7264d7-ee1f-aecd-c56d-67898f24f00b")     # SK04
SKILL_COMMUNICATIONS = uuid.UUID("080d2537-f7fc-5495-1b74-1e7c625c5cc7")       # SK03
SKILL_FIRST_AID = uuid.UUID("216e4f00-8438-c98a-d4ba-832cd21ed70f")            # SK01
SKILL_PHYSICAL_TRAINING = uuid.UUID("79be1683-ac97-96d7-906c-13550f55a2ec")    # SK17


def generate_shift_id(unit_id: uuid.UUID, day_idx: int, shift_type: str) -> uuid.UUID:
    """Generate deterministic UUID5 for a shift requirement."""
    name = f"shift:{unit_id}:{day_idx}:{shift_type}:{DATASET_VERSION}"
    return uuid.uuid5(PLANNING_NAMESPACE, name)


def generate_assignment_id(shift_id: uuid.UUID, personnel_id: uuid.UUID) -> uuid.UUID:
    """Generate deterministic UUID5 for a roster assignment."""
    name = f"assignment:{shift_id}:{personnel_id}:{DATASET_VERSION}"
    return uuid.uuid5(PLANNING_NAMESPACE, name)


def generate_availability_id(personnel_id: uuid.UUID, start_at: datetime, state: str) -> uuid.UUID:
    """Generate deterministic UUID5 for an availability interval."""
    name = f"avail:{personnel_id}:{start_at.isoformat()}:{state}:{DATASET_VERSION}"
    return uuid.uuid5(PLANNING_NAMESPACE, name)


def generate_synthetic_shift_requirements(
    unit_id: uuid.UUID = DEMO_UNIT_ID,
    window_start: datetime = WINDOW_START,
    num_days: int = PLANNING_HORIZON_DAYS,
    source_revision: str = SOURCE_REVISION,
) -> List[Dict[str, Any]]:
    """Generate 14-day shift requirements for the demo unit (2 shifts per day)."""
    shifts: List[Dict[str, Any]] = []

    for day_idx in range(num_days):
        day_date = window_start + timedelta(days=day_idx)

        # 1. Day Shift (08:00 - 16:00, 8h, 5 personnel)
        day_start = day_date + timedelta(hours=8)
        day_end = day_date + timedelta(hours=16)
        day_shift_id = generate_shift_id(unit_id, day_idx, "DAY")
        day_skills = [
            {"skill_id": str(SKILL_WEAPONS_HANDLING), "min_proficiency": 2, "count": 1},
            {"skill_id": str(SKILL_COMMUNICATIONS), "min_proficiency": 1, "count": 1},
            {"skill_id": str(SKILL_FIRST_AID), "min_proficiency": 1, "count": 1},
        ]
        shifts.append({
            "id": day_shift_id,
            "unit_id": unit_id,
            "start_at": day_start,
            "end_at": day_end,
            "required_count": 5,
            "required_skills_json": day_skills,
            "is_locked": day_idx < 2,  # First 2 days are locked published commitments
            "source_revision": source_revision,
        })

        # 2. Night Shift (20:00 - 04:00 next day, 8h, 4 personnel)
        night_start = day_date + timedelta(hours=20)
        night_end = day_date + timedelta(days=1, hours=4)
        night_shift_id = generate_shift_id(unit_id, day_idx, "NIGHT")
        night_skills = [
            {"skill_id": str(SKILL_WEAPONS_HANDLING), "min_proficiency": 2, "count": 1},
            {"skill_id": str(SKILL_PHYSICAL_TRAINING), "min_proficiency": 1, "count": 1},
        ]
        shifts.append({
            "id": night_shift_id,
            "unit_id": unit_id,
            "start_at": night_start,
            "end_at": night_end,
            "required_count": 4,
            "required_skills_json": night_skills,
            "is_locked": day_idx < 2,
            "source_revision": source_revision,
        })

    return shifts


def generate_synthetic_availability_intervals(
    personnel_list: List[Dict[str, Any]],
    leaves: List[Dict[str, Any]],
    trainings: List[Dict[str, Any]],
    deployments: List[Dict[str, Any]],
    window_start: datetime = WINDOW_START,
    window_end: datetime = WINDOW_END,
    source_revision: str = SOURCE_REVISION,
) -> List[Dict[str, Any]]:
    """Generate complete, normalized availability intervals for all personnel across the 14 days."""
    intervals: List[Dict[str, Any]] = []

    for person in personnel_list:
        pid = uuid.UUID(str(person["id"]))

        # Collect unavailable blocks for this person
        blocks: List[Tuple[datetime, datetime, str]] = []

        # Leave blocks
        for l in leaves:
            if uuid.UUID(str(l["personnel_id"])) == pid and l["status"] == "APPROVED":
                s = datetime.combine(l["start_date"], datetime.min.time(), tzinfo=timezone.utc)
                e = datetime.combine(l["end_date"] + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
                if s < window_end and e > window_start:
                    clamped_s = max(s, window_start)
                    clamped_e = min(e, window_end)
                    blocks.append((clamped_s, clamped_e, "LEAVE"))

        # Training blocks
        for t in trainings:
            if uuid.UUID(str(t["personnel_id"])) == pid:
                s = datetime.combine(t["start_date"], datetime.min.time(), tzinfo=timezone.utc)
                e = datetime.combine(t["end_date"] + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
                if s < window_end and e > window_start:
                    clamped_s = max(s, window_start)
                    clamped_e = min(e, window_end)
                    blocks.append((clamped_s, clamped_e, "TRAINING"))

        # Deployment blocks
        for d in deployments:
            if uuid.UUID(str(d["personnel_id"])) == pid:
                s = datetime.combine(d["start_date"], datetime.min.time(), tzinfo=timezone.utc)
                e_date = d.get("end_date")
                e = datetime.combine(e_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc) if e_date else window_end
                if s < window_end and e > window_start:
                    clamped_s = max(s, window_start)
                    clamped_e = min(e, window_end)
                    blocks.append((clamped_s, clamped_e, "DEPLOYMENT"))

        # Sort blocks
        blocks.sort(key=lambda x: x[0])

        # Merge overlapping unavailable blocks
        merged_blocks: List[Tuple[datetime, datetime, str]] = []
        for b_start, b_end, reason in blocks:
            if not merged_blocks:
                merged_blocks.append((b_start, b_end, reason))
            else:
                last_s, last_e, last_r = merged_blocks[-1]
                if b_start < last_e:
                    # Overlap: extend end, keep highest priority reason (DEPLOYMENT > TRAINING > LEAVE)
                    new_end = max(last_e, b_end)
                    prio_reason = "DEPLOYMENT" if "DEPLOYMENT" in (last_r, reason) else ("TRAINING" if "TRAINING" in (last_r, reason) else last_r)
                    merged_blocks[-1] = (last_s, new_end, prio_reason)
                else:
                    merged_blocks.append((b_start, b_end, reason))

        # Build contiguous coverage from window_start to window_end
        curr_time = window_start
        for b_start, b_end, reason in merged_blocks:
            if b_start > curr_time:
                # AVAILABLE interval
                itv_id = generate_availability_id(pid, curr_time, "AVAILABLE")
                intervals.append({
                    "id": itv_id,
                    "personnel_id": pid,
                    "start_at": curr_time,
                    "end_at": b_start,
                    "state": "AVAILABLE",
                    "reason_code": None,
                    "source_revision": source_revision,
                })
            # UNAVAILABLE interval
            itv_id = generate_availability_id(pid, b_start, "UNAVAILABLE")
            intervals.append({
                "id": itv_id,
                "personnel_id": pid,
                "start_at": b_start,
                "end_at": b_end,
                "state": "UNAVAILABLE",
                "reason_code": reason,
                "source_revision": source_revision,
            })
            curr_time = b_end

        if curr_time < window_end:
            # Trailing AVAILABLE interval
            itv_id = generate_availability_id(pid, curr_time, "AVAILABLE")
            intervals.append({
                "id": itv_id,
                "personnel_id": pid,
                "start_at": curr_time,
                "end_at": window_end,
                "state": "AVAILABLE",
                "reason_code": None,
                "source_revision": source_revision,
            })

    return intervals


def generate_synthetic_published_assignments(
    shifts: List[Dict[str, Any]],
    personnel_list: List[Dict[str, Any]],
    person_skills: Dict[uuid.UUID, Dict[uuid.UUID, int]],
    availability: List[Dict[str, Any]],
    prior_duties: List[Dict[str, Any]],
    source_revision: str = SOURCE_REVISION,
) -> List[Dict[str, Any]]:
    """Deterministically assign personnel to shifts satisfying all 12 hard constraints."""
    assignments: List[Dict[str, Any]] = []

    # Map UNAVAILABLE intervals per person
    unavail_map: Dict[uuid.UUID, List[Tuple[datetime, datetime]]] = {}
    for itv in availability:
        if itv["state"] == "UNAVAILABLE":
            pid = uuid.UUID(str(itv["personnel_id"]))
            s = itv["start_at"]
            e = itv["end_at"]
            unavail_map.setdefault(pid, []).append((s, e))

    # Track duties per person to enforce rest (8h), max rolling hours (60h/7d), max consecutive days (6)
    person_duties: Dict[uuid.UUID, List[Tuple[datetime, datetime]]] = {
        uuid.UUID(str(p["id"])): [] for p in personnel_list
    }

    # Add prior duties
    for pd in prior_duties:
        pid = uuid.UUID(str(pd["personnel_id"]))
        if pid in person_duties:
            s = pd["start_at"] if isinstance(pd["start_at"], datetime) else datetime.fromisoformat(pd["start_at"])
            e = pd["end_at"] if isinstance(pd["end_at"], datetime) else datetime.fromisoformat(pd["end_at"])
            person_duties[pid].append((s, e))

    # Helper: check feasibility of adding shift for person
    def is_person_feasible(pid: uuid.UUID, shift_start: datetime, shift_end: datetime) -> bool:
        # 1. Availability check
        for u_start, u_end in unavail_map.get(pid, []):
            if shift_start < u_end and shift_end > u_start:
                return False

        # 2. Overlap and min rest (>= 8 hours)
        duties = sorted(person_duties[pid], key=lambda x: x[0])
        for d_start, d_end in duties:
            if shift_start < d_end and shift_end > d_start:
                return False
            # Check rest gap before shift
            if d_end <= shift_start:
                rest_before = (shift_start - d_end).total_seconds() / 3600.0
                if rest_before < 8.0:
                    return False
            # Check rest gap after shift
            if shift_end <= d_start:
                rest_after = (d_start - shift_end).total_seconds() / 3600.0
                if rest_after < 8.0:
                    return False

        # 3. Rolling 7-day max hours (<= 60h)
        cand_duties = duties + [(shift_start, shift_end)]
        cand_duties.sort(key=lambda x: x[0])
        w_chk = shift_start - timedelta(days=6, hours=23)
        while w_chk <= shift_start:
            w_end = w_chk + timedelta(days=7)
            tot_hrs = 0.0
            for ds, de in cand_duties:
                o_start = max(ds, w_chk)
                o_end = min(de, w_end)
                if o_end > o_start:
                    tot_hrs += (o_end - o_start).total_seconds() / 3600.0
            if tot_hrs > 60.0:
                return False
            w_chk += timedelta(hours=6)

        # 4. Max consecutive duty days (<= 6 days)
        duty_dates = {ds.date() for ds, de in cand_duties}
        sorted_dates = sorted(duty_dates)
        streak = 0
        prev_d: Optional[date] = None
        for d in sorted_dates:
            if prev_d is None or d == prev_d + timedelta(days=1):
                streak += 1
            else:
                streak = 1
            if streak > 6:
                return False
            prev_d = d

        return True

    # Deterministic assignment loop
    # Sort shifts by start_at
    sorted_shifts = sorted(shifts, key=lambda s: s["start_at"])

    # List of candidate personnel sorted by pseudo_id for deterministic order
    sorted_personnel = sorted(personnel_list, key=lambda p: str(p.get("pseudo_id", p["id"])))

    for shift in sorted_shifts:
        sid = uuid.UUID(str(shift["id"]))
        s_start = shift["start_at"]
        s_end = shift["end_at"]
        req_count = shift["required_count"]
        req_skills = shift.get("required_skills_json", [])
        is_locked = shift.get("is_locked", False)

        assigned_for_shift: List[uuid.UUID] = []

        # First pass: satisfy required skills
        for sk_req in req_skills:
            sk_id = uuid.UUID(str(sk_req["skill_id"]))
            min_prof = sk_req["min_proficiency"]
            needed_count = sk_req["count"]

            already_qualified = sum(
                1 for p in assigned_for_shift
                if person_skills.get(p, {}).get(sk_id, 0) >= min_prof
            )
            to_add = needed_count - already_qualified

            if to_add > 0:
                skill_candidates = [
                    p for p in sorted_personnel
                    if uuid.UUID(str(p["id"])) not in assigned_for_shift
                    and person_skills.get(uuid.UUID(str(p["id"])), {}).get(sk_id, 0) >= min_prof
                ]
                skill_candidates.sort(key=lambda p: (len(person_duties[uuid.UUID(str(p["id"]))]), str(p.get("pseudo_id", p["id"]))))
                for person in skill_candidates:
                    pid = uuid.UUID(str(person["id"]))
                    if is_person_feasible(pid, s_start, s_end):
                        assigned_for_shift.append(pid)
                        person_duties[pid].append((s_start, s_end))
                        to_add -= 1
                        if to_add == 0:
                            break

        # Second pass: fill remaining slots up to required_count
        while len(assigned_for_shift) < req_count:
            added = False
            # Pick person with least total duties assigned so far (balanced distribution)
            candidates = [
                p for p in sorted_personnel
                if uuid.UUID(str(p["id"])) not in assigned_for_shift
            ]
            candidates.sort(key=lambda p: (len(person_duties[uuid.UUID(str(p["id"]))]), str(p.get("pseudo_id", p["id"]))))

            for person in candidates:
                pid = uuid.UUID(str(person["id"]))
                if is_person_feasible(pid, s_start, s_end):
                    assigned_for_shift.append(pid)
                    person_duties[pid].append((s_start, s_end))
                    added = True
                    break

            if not added:
                raise RuntimeError(
                    f"Unable to feasibly fill shift {sid} on {s_start.isoformat()} (assigned {len(assigned_for_shift)}/{req_count})"
                )

        # Create assignment records
        for pid in assigned_for_shift:
            assign_id = generate_assignment_id(sid, pid)
            assignments.append({
                "id": assign_id,
                "shift_id": sid,
                "personnel_id": pid,
                "is_locked": is_locked,
                "source_revision": source_revision,
            })

    return assignments
