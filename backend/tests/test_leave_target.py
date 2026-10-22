"""Tests for Model-A Target Semantics & Task 12 Target Generation.

TASK 12 TESTS:
1. positive event inside horizon -> POSITIVE
2. positive event outside horizon -> NEGATIVE
3. routine planned leave -> NEGATIVE
4. boundary dates -> event on T (0/NEGATIVE), event on T+1 (1/POSITIVE), event on T+30 (1/POSITIVE), event on T+31 (0/NEGATIVE)
5. multiple leave events -> mixed records correctly aggregated
6. no event -> confirmed active service with 0 leave events -> NEGATIVE

ADDITIONAL GOVERNANCE TESTS:
- All 7 lifecycle fields NULL (historical rows) -> TARGET_UNAVAILABLE
- Missing initiator on disruption -> TARGET_UNAVAILABLE
- Missing timestamp on disruption -> TARGET_UNAVAILABLE
- Missing prior-approval evidence -> TARGET_UNAVAILABLE
- Personnel-initiated cancellation -> NEGATIVE
- SPECIAL_LEAVE alone without classification -> TARGET_UNAVAILABLE
- Truncated horizon past max_data_date -> TARGET_UNAVAILABLE
- Synthetic cohort generator determinism and manifest compliance
"""

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest

from tools.training.synthetic_leave_manifest import (
    SYNTHETIC_LEAVE_MANIFEST_V1,
    generate_synthetic_leave_cohort,
)
from app.ml.targets import (
    HORIZON_DAYS,
    TARGET_VERSION,
    LeaveTargetState,
    classify_single_leave_record,
    compute_leave_anomaly_target,
    generate_leave_anomaly_target,
    target_to_binary,
)
from app.models.leave_record import LeaveRecord


# =====================================================================
# TASK 12 CANONICAL TESTS
# =====================================================================

def test_task12_positive_event_inside_horizon():
    """TASK 12 TEST 1: Positive event occurring strictly inside (T, T + 30d]."""
    cutoff = date(2026, 6, 1)

    # Condition A: Unplanned leave starting on T+15
    unplanned_record = {
        "planning_classification": "UNPLANNED",
        "actual_start_date": date(2026, 6, 16),
        "actual_end_date": date(2026, 6, 22),
    }
    state_a, ver_a = generate_leave_anomaly_target([unplanned_record], cutoff_date=cutoff)
    assert state_a == LeaveTargetState.POSITIVE
    assert target_to_binary(state_a) == 1
    assert ver_a == TARGET_VERSION

    # Condition B: Service disruption occurring on T+10
    disrupted_record = {
        "planning_classification": "PLANNED",
        "approved_at": datetime(2026, 5, 20, 9, 0, tzinfo=timezone.utc),
        "disruption_initiator": "SERVICE",
        "disruption_type": "RECALLED",
        "disrupted_at": datetime(2026, 6, 11, 8, 30, tzinfo=timezone.utc),
    }
    state_b, ver_b = generate_leave_anomaly_target([disrupted_record], cutoff_date=cutoff)
    assert state_b == LeaveTargetState.POSITIVE
    assert target_to_binary(state_b) == 1


def test_task12_positive_event_outside_horizon():
    """TASK 12 TEST 2: Positive event occurring strictly outside (T, T + 30d]."""
    cutoff = date(2026, 6, 1)

    # Event occurring in the past (t <= T) -> does NOT trigger future horizon
    past_record = {
        "planning_classification": "UNPLANNED",
        "actual_start_date": date(2026, 5, 20),
        "actual_end_date": date(2026, 5, 25),
    }
    state_past, _ = generate_leave_anomaly_target([past_record], cutoff_date=cutoff)
    assert state_past == LeaveTargetState.NEGATIVE
    assert target_to_binary(state_past) == 0

    # Event occurring beyond the 30-day horizon (T + 35d)
    future_record = {
        "planning_classification": "UNPLANNED",
        "actual_start_date": date(2026, 7, 6),
        "actual_end_date": date(2026, 7, 12),
    }
    state_future, _ = generate_leave_anomaly_target([future_record], cutoff_date=cutoff)
    assert state_future == LeaveTargetState.NEGATIVE
    assert target_to_binary(state_future) == 0


def test_task12_routine_planned_leave():
    """TASK 12 TEST 3: Routine planned leave executed without disruption inside horizon."""
    cutoff = date(2026, 6, 1)
    planned_record = {
        "planning_classification": "PLANNED",
        "approved_at": datetime(2026, 5, 20, 10, 0, tzinfo=timezone.utc),
        "actual_start_date": date(2026, 6, 5),
        "actual_end_date": date(2026, 6, 15),
        "disruption_type": None,
        "disruption_initiator": None,
        "disrupted_at": None,
    }
    state, ver = generate_leave_anomaly_target([planned_record], cutoff_date=cutoff)
    assert state == LeaveTargetState.NEGATIVE
    assert target_to_binary(state) == 0
    assert ver == TARGET_VERSION


def test_task12_boundary_dates():
    """TASK 12 TEST 4: Boundary date evaluation relative to (T, T + 30d]."""
    cutoff = date(2026, 6, 1)  # T
    # Horizon is (2026-06-01, 2026-07-01]

    # Exactly on cutoff T (2026-06-01) -> Historical event, strictly <= T -> 0
    on_t = {
        "planning_classification": "UNPLANNED",
        "actual_start_date": date(2026, 6, 1),
        "actual_end_date": date(2026, 6, 5),
    }
    assert generate_leave_anomaly_target([on_t], cutoff_date=cutoff)[0] == LeaveTargetState.NEGATIVE

    # T + 1 day (2026-06-02) -> First day of horizon -> 1
    on_t_plus_1 = {
        "planning_classification": "UNPLANNED",
        "actual_start_date": date(2026, 6, 2),
    }
    assert generate_leave_anomaly_target([on_t_plus_1], cutoff_date=cutoff)[0] == LeaveTargetState.POSITIVE

    # Exactly T + 30 days (2026-07-01) -> Last day of horizon -> 1
    on_t_plus_30 = {
        "planning_classification": "UNPLANNED",
        "actual_start_date": date(2026, 7, 1),
    }
    assert generate_leave_anomaly_target([on_t_plus_30], cutoff_date=cutoff)[0] == LeaveTargetState.POSITIVE

    # T + 31 days (2026-07-02) -> Just outside horizon -> 0
    on_t_plus_31 = {
        "planning_classification": "UNPLANNED",
        "actual_start_date": date(2026, 7, 2),
        "actual_end_date": date(2026, 7, 8),
    }
    assert generate_leave_anomaly_target([on_t_plus_31], cutoff_date=cutoff)[0] == LeaveTargetState.NEGATIVE


def test_task12_multiple_leave_events():
    """TASK 12 TEST 5: Multiple leave records in candidate window."""
    cutoff = date(2026, 6, 1)

    routine_event = {
        "planning_classification": "PLANNED",
        "approved_at": datetime(2026, 5, 10, 9, 0, tzinfo=timezone.utc),
        "actual_start_date": date(2026, 5, 20),
        "actual_end_date": date(2026, 5, 28),
    }
    service_disrupted_event = {
        "planning_classification": "PLANNED",
        "approved_at": datetime(2026, 5, 25, 9, 0, tzinfo=timezone.utc),
        "disruption_initiator": "SERVICE",
        "disruption_type": "CANCELLED",
        "disrupted_at": datetime(2026, 6, 10, 11, 0, tzinfo=timezone.utc),
    }

    # Routine + Service disruption -> Overall POSITIVE
    state, _ = generate_leave_anomaly_target([routine_event, service_disrupted_event], cutoff_date=cutoff)
    assert state == LeaveTargetState.POSITIVE
    assert target_to_binary(state) == 1

    # Multiple routine planned leaves -> Overall NEGATIVE
    second_routine = {
        "planning_classification": "PLANNED",
        "approved_at": datetime(2026, 5, 25, 9, 0, tzinfo=timezone.utc),
        "actual_start_date": date(2026, 6, 15),
        "actual_end_date": date(2026, 6, 22),
    }
    state_all_routine, _ = generate_leave_anomaly_target([routine_event, second_routine], cutoff_date=cutoff)
    assert state_all_routine == LeaveTargetState.NEGATIVE
    assert target_to_binary(state_all_routine) == 0


def test_task12_no_event():
    """TASK 12 TEST 6: Personnel with active duty and zero leave events in horizon."""
    cutoff = date(2026, 6, 1)

    # When active service is confirmed, zero leave events is confirmed NEGATIVE
    state_active, _ = generate_leave_anomaly_target([], cutoff_date=cutoff, active_service=True)
    assert state_active == LeaveTargetState.NEGATIVE
    assert target_to_binary(state_active) == 0

    # When active service is NOT confirmed, zero records is TARGET_UNAVAILABLE
    state_unconfirmed, _ = generate_leave_anomaly_target([], cutoff_date=cutoff, active_service=False)
    assert state_unconfirmed == LeaveTargetState.TARGET_UNAVAILABLE
    assert target_to_binary(state_unconfirmed) is None


# =====================================================================
# GOVERNANCE & RETRIEVED ROW TESTS
# =====================================================================

def test_retained_historical_rows_all_null_is_target_unavailable():
    """Retained database rows with all 7 fields NULL must evaluate to TARGET_UNAVAILABLE."""
    cutoff = date(2026, 6, 1)
    historical_row = {
        "leave_type": "ANNUAL",
        "start_date": date(2026, 6, 5),
        "end_date": date(2026, 6, 15),
        "days": 10.0,
        "status": "APPROVED",
        "planning_classification": None,
        "approved_at": None,
        "actual_start_date": None,
        "actual_end_date": None,
        "disruption_type": None,
        "disruption_initiator": None,
        "disrupted_at": None,
    }
    state, _ = generate_leave_anomaly_target([historical_row], cutoff_date=cutoff)
    assert state == LeaveTargetState.TARGET_UNAVAILABLE
    assert target_to_binary(state) is None


def test_missing_initiator_on_disruption_is_target_unavailable():
    """Disruption lacking initiator cannot establish whether service-directed."""
    cutoff = date(2026, 6, 1)
    record = {
        "planning_classification": "PLANNED",
        "approved_at": datetime(2026, 5, 20, 10, 0, tzinfo=timezone.utc),
        "disruption_type": "CANCELLED",
        "disruption_initiator": None,
        "disrupted_at": datetime(2026, 6, 10, 8, 30, tzinfo=timezone.utc),
    }
    assert generate_leave_anomaly_target([record], cutoff_date=cutoff)[0] == LeaveTargetState.TARGET_UNAVAILABLE


def test_missing_timestamp_on_disruption_is_target_unavailable():
    """Disruption missing disrupted_at timestamp cannot be bounded."""
    cutoff = date(2026, 6, 1)
    record = {
        "planning_classification": "PLANNED",
        "approved_at": datetime(2026, 5, 20, 10, 0, tzinfo=timezone.utc),
        "disruption_type": "CANCELLED",
        "disruption_initiator": "SERVICE",
        "disrupted_at": None,
    }
    assert generate_leave_anomaly_target([record], cutoff_date=cutoff)[0] == LeaveTargetState.TARGET_UNAVAILABLE


def test_missing_approval_on_service_disruption_is_target_unavailable():
    """Service disruption lacking verified prior approval is unverified."""
    cutoff = date(2026, 6, 1)
    record = {
        "planning_classification": "PLANNED",
        "approved_at": None,
        "disruption_initiator": "SERVICE",
        "disruption_type": "CANCELLED",
        "disrupted_at": datetime(2026, 6, 10, 8, 30, tzinfo=timezone.utc),
    }
    assert generate_leave_anomaly_target([record], cutoff_date=cutoff)[0] == LeaveTargetState.TARGET_UNAVAILABLE


def test_personnel_initiated_cancellation_is_negative():
    """Personnel-initiated cancellation with complete lifecycle is NEGATIVE."""
    cutoff = date(2026, 6, 1)
    record = {
        "planning_classification": "PLANNED",
        "approved_at": datetime(2026, 5, 20, 10, 0, tzinfo=timezone.utc),
        "disruption_initiator": "PERSONNEL",
        "disruption_type": "CANCELLED",
        "disrupted_at": datetime(2026, 6, 5, 10, 0, tzinfo=timezone.utc),
    }
    assert generate_leave_anomaly_target([record], cutoff_date=cutoff)[0] == LeaveTargetState.NEGATIVE


def test_special_leave_alone_does_not_determine_target():
    """SPECIAL_LEAVE alone without planning_classification is TARGET_UNAVAILABLE."""
    cutoff = date(2026, 6, 1)
    record = {
        "leave_type": "SPECIAL_LEAVE",
        "planning_classification": None,
        "actual_start_date": date(2026, 6, 10),
    }
    assert generate_leave_anomaly_target([record], cutoff_date=cutoff)[0] == LeaveTargetState.TARGET_UNAVAILABLE


def test_horizon_truncation_past_max_data_date():
    """Horizon extending beyond end of observation window is TARGET_UNAVAILABLE."""
    cutoff = date(2026, 8, 15)
    max_date = date(2026, 8, 31)  # Only 16 days remain, cannot observe full 30 days
    state, ver = generate_leave_anomaly_target([], cutoff_date=cutoff, max_data_date=max_date)
    assert state == LeaveTargetState.TARGET_UNAVAILABLE
    assert target_to_binary(state) is None


def test_synthetic_cohort_generator_determinism():
    """Synthetic leave cohort generator produces identical results for identical seeds."""
    pids = [f"PRH-{i:04d}" for i in range(10)]
    start_d = date(2025, 9, 1)
    end_d = date(2026, 8, 31)

    cohort_1 = generate_synthetic_leave_cohort(pids, start_d, end_d, seed=26186)
    cohort_2 = generate_synthetic_leave_cohort(pids, start_d, end_d, seed=26186)
    assert len(cohort_1) == len(cohort_2)
    assert cohort_1 == cohort_2

    # Verify manifest adherence
    assert len(cohort_1) > 0
    planned_count = sum(1 for r in cohort_1 if r["planning_classification"] == "PLANNED")
    unplanned_count = sum(1 for r in cohort_1 if r["planning_classification"] == "UNPLANNED")
    assert planned_count > unplanned_count
    assert planned_count + unplanned_count == len(cohort_1)


def test_coupled_synthetic_cohort_generator_determinism():
    """Coupled synthetic leave cohort generator produces identical results for identical seeds."""
    import pandas as pd
    from tools.training.synthetic_leave_manifest import (
        SYNTHETIC_COUPLING_MANIFEST_V2,
        generate_coupled_synthetic_leave_cohort,
    )

    pids = [f"PRH-{i:04d}" for i in range(5)]
    op_data = []
    for pid in pids:
        for w in range(10):
            op_data.append({
                "pseudo_id": pid,
                "prediction_date": (date(2025, 9, 1) + timedelta(days=w * 7)).isoformat(),
                "duty_hours_30d": 160.0 + (w * 2.0),
                "min_rest_hours_14d": 3.0,
                "consecutive_duty_days": 2.0,
                "night_duty_ratio_30d": 0.25,
                "deployment_days_30d": 1.0,
                "staffing_ratio_7d": 0.80,
                "baseline_z_workload": 0.1,
                "peer_deviation_workload": 0.05,
                "workload_change_14v14": 5.0,
            })
    op_df = pd.DataFrame(op_data)

    c1 = generate_coupled_synthetic_leave_cohort(
        operational_df=op_df,
        start_date=date(2025, 9, 1),
        end_date=date(2026, 8, 31),
        manifest=SYNTHETIC_COUPLING_MANIFEST_V2,
        seed=26186,
    )
    c2 = generate_coupled_synthetic_leave_cohort(
        operational_df=op_df,
        start_date=date(2025, 9, 1),
        end_date=date(2026, 8, 31),
        manifest=SYNTHETIC_COUPLING_MANIFEST_V2,
        seed=26186,
    )

    assert len(c1) == len(c2)
    assert c1 == c2
    assert len(c1) > 0
    # Every generated record must satisfy complete lifecycle evidence
    for rec in c1:
        assert rec["planning_classification"] in ("PLANNED", "UNPLANNED")
        assert rec["start_date"] is not None
        assert rec["end_date"] is not None
