"""Model-A Target Definition and Extraction.

Canonical Target Definition:
Y_A in (T, T + horizon_days] evaluates to one of three explicit states:
- POSITIVE (1): Confirmed operational leave anomaly in horizon.
- NEGATIVE (0): Confirmed true negative with complete lifecycle evidence.
- TARGET_UNAVAILABLE: Incomplete/legacy/unlabelled lifecycle data.
  EXCLUDED from supervised training and evaluation.

Conditions for POSITIVE:
A) Unplanned Leave Outbreak:
   - planning_classification == 'UNPLANNED'
   - actual_start_date IS NOT NULL
   - T < actual_start_date <= T + horizon_days
OR
B) Service-Initiated Disruption:
   - prior approval is established (approved_at IS NOT NULL and approved_at <= disrupted_at)
   - disruption_initiator == 'SERVICE'
   - disruption_type IN ('CANCELLED', 'DEFERRED', 'RECALLED', 'SHORTENED')
   - disrupted_at IS NOT NULL
   - T < disrupted_at.date() <= T + horizon_days

Conditions for NEGATIVE:
- Established planned lifecycle with complete evidence completed without qualifying disruption, OR
- Personnel-initiated cancellation/deferral with complete lifecycle evidence.

Conditions for TARGET_UNAVAILABLE:
- All 7 lifecycle fields NULL (historical retained rows).
- Missing initiator on disruption.
- Missing disruption timestamp (disrupted_at).
- Disruption lacking prior approval evidence (approved_at is None or approved_at > disrupted_at).
- Incomplete planned lifecycle evidence.
- No lifecycle evidence.
"""

from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Iterable, Optional, Sequence, Tuple, Union

TARGET_HR = "target_leave_anomaly_30d"
TARGET_WELLBEING = "target_wellbeing_decline"

SERVICE_DISRUPTION_TYPES = frozenset({"CANCELLED", "DEFERRED", "RECALLED", "SHORTENED"})


class LeaveTargetState(str, Enum):
    """Explicit three-state classification for Model-A leave anomaly target."""
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    TARGET_UNAVAILABLE = "TARGET_UNAVAILABLE"


TARGET_POSITIVE = LeaveTargetState.POSITIVE.value
TARGET_NEGATIVE = LeaveTargetState.NEGATIVE.value
TARGET_UNAVAILABLE = LeaveTargetState.TARGET_UNAVAILABLE.value


def target_to_binary(target_state: Union[LeaveTargetState, str, None]) -> Optional[int]:
    """Converts verified target state to binary integer {0, 1} or None.

    Returns:
        1 for POSITIVE
        0 for NEGATIVE
        None for TARGET_UNAVAILABLE (excluded from supervised training)
    """
    if target_state == LeaveTargetState.POSITIVE or target_state == "POSITIVE":
        return 1
    if target_state == LeaveTargetState.NEGATIVE or target_state == "NEGATIVE":
        return 0
    return None


def classify_single_leave_record(
    record: Any,
    cutoff_date: date,
    horizon_days: int = 30,
) -> LeaveTargetState:
    """Evaluates lifecycle evidence for a single leave record relative to (T, T + horizon_days]."""
    if isinstance(record, dict):
        leave_type = record.get("leave_type")
        planning_class = record.get("planning_classification")
        approved_at = record.get("approved_at")
        actual_start = record.get("actual_start_date")
        actual_end = record.get("actual_end_date")
        disruption_type = record.get("disruption_type")
        disruption_initiator = record.get("disruption_initiator")
        disrupted_at = record.get("disrupted_at")
    else:
        leave_type = getattr(record, "leave_type", None)
        planning_class = getattr(record, "planning_classification", None)
        approved_at = getattr(record, "approved_at", None)
        actual_start = getattr(record, "actual_start_date", None)
        actual_end = getattr(record, "actual_end_date", None)
        disruption_type = getattr(record, "disruption_type", None)
        disruption_initiator = getattr(record, "disruption_initiator", None)
        disrupted_at = getattr(record, "disrupted_at", None)

    # 1. Historical / unpopulated row: strictly TARGET_UNAVAILABLE (Rule 1)
    if (
        planning_class is None
        and approved_at is None
        and actual_start is None
        and actual_end is None
        and disruption_type is None
        and disruption_initiator is None
        and disrupted_at is None
    ):
        return LeaveTargetState.TARGET_UNAVAILABLE

    horizon_end = cutoff_date + timedelta(days=horizon_days)

    actual_start_d = actual_start.date() if isinstance(actual_start, datetime) else actual_start
    actual_end_d = actual_end.date() if isinstance(actual_end, datetime) else actual_end
    disrupted_d = disrupted_at.date() if isinstance(disrupted_at, datetime) else disrupted_at

    has_disruption = (
        disruption_type is not None
        or disruption_initiator is not None
        or disrupted_at is not None
    )

    # 2. Check Condition A: Unplanned leave inside horizon
    if planning_class == "UNPLANNED":
        if actual_start_d is not None:
            if cutoff_date < actual_start_d <= horizon_end:
                return LeaveTargetState.POSITIVE
            else:
                # Started outside horizon (historical t <= T or future t > T+30d)
                # Does not trigger positive for this horizon window.
                # If lifecycle is otherwise complete without disruption, not positive.
                return LeaveTargetState.NEGATIVE
        else:
            # Unplanned leave without actual start date cannot be confirmed
            return LeaveTargetState.TARGET_UNAVAILABLE

    # 3. Check Disruption Details
    if has_disruption:
        # Rule 7: Missing initiator on disruption -> TARGET_UNAVAILABLE
        if disruption_initiator is None:
            return LeaveTargetState.TARGET_UNAVAILABLE

        # Rule 7: Missing disrupted_at on disruption -> TARGET_UNAVAILABLE
        if disrupted_at is None or disrupted_d is None:
            return LeaveTargetState.TARGET_UNAVAILABLE

        is_in_horizon = (cutoff_date < disrupted_d <= horizon_end)

        if is_in_horizon:
            if disruption_initiator == "SERVICE":
                if disruption_type in SERVICE_DISRUPTION_TYPES:
                    # Rule 3B: Prior approval must be established and predate disruption
                    if approved_at is not None and approved_at <= disrupted_at:
                        return LeaveTargetState.POSITIVE
                    else:
                        # Missing or invalid prior-approval evidence (Rule 7)
                        return LeaveTargetState.TARGET_UNAVAILABLE
                else:
                    return LeaveTargetState.TARGET_UNAVAILABLE
            elif disruption_initiator == "PERSONNEL":
                # Rule 4: Personnel-initiated cancellation inside horizon is confirmed negative
                return LeaveTargetState.NEGATIVE
            else:
                return LeaveTargetState.TARGET_UNAVAILABLE
        else:
            # Disruption occurred outside horizon (e.g. t <= T or t > T+30d)
            # Not an active disruption in this horizon.
            if disruption_initiator in ("SERVICE", "PERSONNEL"):
                return LeaveTargetState.NEGATIVE
            return LeaveTargetState.TARGET_UNAVAILABLE

    # 4. Check Condition C: Normal planned leave without disruption
    if planning_class == "PLANNED":
        if (
            approved_at is not None
            and actual_start_d is not None
            and actual_end_d is not None
            and actual_end_d >= actual_start_d
            and not has_disruption
        ):
            return LeaveTargetState.NEGATIVE
        else:
            # Incomplete planned lifecycle evidence
            return LeaveTargetState.TARGET_UNAVAILABLE

    # 5. Rule 5: SPECIAL_LEAVE alone must never determine target
    # If planning_class is missing, it is unclassified
    return LeaveTargetState.TARGET_UNAVAILABLE


TARGET_VERSION = "model-a-target-v3.0-canonical"
HORIZON_DAYS = 30


def compute_leave_anomaly_target(
    leave_records: Iterable[Any],
    cutoff_date: date,
    horizon_days: int = HORIZON_DAYS,
    active_service: bool = False,
) -> LeaveTargetState:
    """Computes explicit 3-state leave anomaly target in (cutoff_date, cutoff_date + horizon_days].

    Args:
        leave_records: Iterable of LeaveRecord models, dicts, or objects.
        cutoff_date: Observation cutoff date T.
        horizon_days: Target prediction window length in days (default 30).
        active_service: Whether personnel is on active duty with confirmed zero leave anomalies.

    Returns:
        LeaveTargetState.POSITIVE, LeaveTargetState.NEGATIVE, or LeaveTargetState.TARGET_UNAVAILABLE.
    """
    records = list(leave_records)
    if not records:
        return LeaveTargetState.NEGATIVE if active_service else LeaveTargetState.TARGET_UNAVAILABLE

    states = [
        classify_single_leave_record(r, cutoff_date, horizon_days)
        for r in records
    ]

    # If ANY record is POSITIVE in the horizon, the personnel experienced an anomaly
    if any(s == LeaveTargetState.POSITIVE for s in states):
        return LeaveTargetState.POSITIVE

    # If ANY record has unavailable/incomplete lifecycle evidence, cannot establish true negative
    if any(s == LeaveTargetState.TARGET_UNAVAILABLE for s in states):
        return LeaveTargetState.TARGET_UNAVAILABLE

    # If ALL records have complete evidence confirming negative
    if all(s == LeaveTargetState.NEGATIVE for s in states):
        return LeaveTargetState.NEGATIVE

    return LeaveTargetState.TARGET_UNAVAILABLE


def generate_leave_anomaly_target(
    leave_records: Iterable[Any],
    cutoff_date: date,
    horizon_days: int = HORIZON_DAYS,
    active_service: bool = True,
    max_data_date: Optional[date] = None,
) -> Tuple[LeaveTargetState, str]:
    """Generates canonical versioned target for prediction timestamp T.

    Args:
        leave_records: Leave records for personnel.
        cutoff_date: Prediction cutoff timestamp T.
        horizon_days: Evaluation window (default 30 days).
        active_service: Whether personnel has verified active duty in the period.
        max_data_date: Optional end of observational data. If horizon exceeds max_data_date,
                       future window is truncated and returns TARGET_UNAVAILABLE.

    Returns:
        Tuple of (LeaveTargetState, target_version_string).
    """
    if max_data_date is not None and cutoff_date + timedelta(days=horizon_days) > max_data_date:
        return (LeaveTargetState.TARGET_UNAVAILABLE, TARGET_VERSION)

    state = compute_leave_anomaly_target(
        leave_records=leave_records,
        cutoff_date=cutoff_date,
        horizon_days=horizon_days,
        active_service=active_service,
    )
    return (state, TARGET_VERSION)


__all__ = [
    "TARGET_HR",
    "TARGET_WELLBEING",
    "TARGET_VERSION",
    "HORIZON_DAYS",
    "SERVICE_DISRUPTION_TYPES",
    "LeaveTargetState",
    "TARGET_POSITIVE",
    "TARGET_NEGATIVE",
    "TARGET_UNAVAILABLE",
    "target_to_binary",
    "classify_single_leave_record",
    "compute_leave_anomaly_target",
    "generate_leave_anomaly_target",
]
