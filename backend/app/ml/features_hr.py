"""
PRAHARI — Model-A Operational Feature Engineering Engine
Canonical Reference: AGENTS.md §8, rules.md, docs/ml.md §6.1

APPROVED 15-FEATURE ORDERED CONTRACT:
1. duty_hours_7d
2. duty_hours_30d
3. night_duty_count_14d
4. night_duty_ratio_30d
5. consecutive_duty_days
6. min_rest_hours_14d
7. avg_rest_hours_30d
8. quick_return_count_30d
9. deployment_days_30d
10. training_days_30d
11. staffing_ratio_7d
12. workload_change_14v14
13. ewma_workload
14. baseline_z_workload
15. peer_deviation_workload

CRITICAL LEAKAGE & CUTOFF RULES:
- All features at cutoff T evaluate ONLY historical data strictly <= T (or < T for trailing daily series).
- Future records (> T) are strictly rejected.
- Missing windows must NEVER be fabricated or silently imputed with zeros.
- Leave features (frequency, variability) are strictly EXCLUDED due to target leakage risk.
"""

from datetime import date, datetime, timedelta
import math
from typing import Any, Dict, List, Optional, Sequence, Set, Union
import numpy as np
import pandas as pd

from app.analytics.baseline import calculate_median_mad, calculate_robust_z_score
from app.analytics.data_quality import validate_rest_gap, validate_rest_hours
from app.analytics.ewma import calculate_ewma

MODEL_A_FEATURE_NAMES: List[str] = [
    "duty_hours_7d",
    "duty_hours_30d",
    "night_duty_count_14d",
    "night_duty_ratio_30d",
    "consecutive_duty_days",
    "min_rest_hours_14d",
    "avg_rest_hours_30d",
    "quick_return_count_30d",
    "deployment_days_30d",
    "training_days_30d",
    "staffing_ratio_7d",
    "workload_change_14v14",
    "ewma_workload",
    "baseline_z_workload",
    "peer_deviation_workload",
]

HISTORICAL_LEAVE_FEATURE_NAMES: List[str] = [
    "leave_frequency_90d",
    "leave_gap_variability_90d",
]

# Task 15 Feature Sets for Circular Dependence A/B Testing:
# Feature Set A: Operational features INCLUDING legitimate historical leave features (17 features)
FEATURE_SET_A: List[str] = MODEL_A_FEATURE_NAMES + HISTORICAL_LEAVE_FEATURE_NAMES

# Feature Set B: Operational features EXCLUDING historical leave features (Canonical Contract: 15 features)
FEATURE_SET_B: List[str] = list(MODEL_A_FEATURE_NAMES)

QUICK_RETURN_THRESHOLD_HOURS: float = 11.0


def _parse_date(val: Any) -> Optional[date]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    try:
        return datetime.fromisoformat(str(val)[:10]).date()
    except Exception:
        return None


def compute_operational_features_at_cutoff(
    as_of: Union[date, datetime],
    personnel_id: str,
    unit_id: str,
    *,
    duties: Sequence[Dict[str, Any]],
    rest_records: Sequence[Dict[str, Any]],
    deployments: Sequence[Dict[str, Any]] = (),
    training: Sequence[Dict[str, Any]] = (),
    staffing: Sequence[Dict[str, Any]] = (),
    peer_cohort_duties_30d: Optional[Sequence[float]] = None,
) -> Dict[str, Optional[float]]:
    """
    Computes the 15 approved Model-A features for a person at cutoff T.
    Guarantees strict cutoff enforcement, person isolation, and truthful missingness.
    """
    cutoff_date = _parse_date(as_of)
    if not cutoff_date:
        raise ValueError(f"Invalid cutoff date: {as_of}")

    # 1. Filter duties: personnel_id == person, record date < cutoff_date
    person_duties = []
    for d in (duties or []):
        if str(d.get("personnel_id", "")) != str(personnel_id):
            continue
        d_date = _parse_date(d.get("date") or d.get("start_at"))
        if d_date is None or d_date >= cutoff_date:
            # Future or on-cutoff shift excluded from pre-cutoff trailing windows
            continue
        person_duties.append({**d, "_date": d_date})

    # Group duties by date for daily aggregations
    duties_by_date: Dict[date, List[Dict[str, Any]]] = {}
    for d in person_duties:
        dt = d["_date"]
        duties_by_date.setdefault(dt, []).append(d)

    # Window definitions
    w7_start = cutoff_date - timedelta(days=7)
    w14_start = cutoff_date - timedelta(days=14)
    w28_start = cutoff_date - timedelta(days=28)
    w30_start = cutoff_date - timedelta(days=30)
    w56_start = cutoff_date - timedelta(days=56)

    # 1. duty_hours_7d
    duties_7d = [d for d in person_duties if w7_start <= d["_date"] < cutoff_date]
    if duties is None or len(duties) == 0:
        duty_hours_7d = None
    else:
        duty_hours_7d = round(sum(float(d.get("hours", 0.0) or 0.0) for d in duties_7d), 2)

    # 2. duty_hours_30d
    duties_30d = [d for d in person_duties if w30_start <= d["_date"] < cutoff_date]
    if duties is None or len(duties) == 0:
        duty_hours_30d = None
    else:
        duty_hours_30d = round(sum(float(d.get("hours", 0.0) or 0.0) for d in duties_30d), 2)

    # 3. night_duty_count_14d
    duties_14d = [d for d in person_duties if w14_start <= d["_date"] < cutoff_date]
    if duties is None or len(duties) == 0:
        night_duty_count_14d = None
    else:
        night_duty_count_14d = float(sum(1 for d in duties_14d if bool(d.get("is_night", False))))

    # 4. night_duty_ratio_30d
    if duties is None or len(duties) == 0 or len(duties_30d) == 0:
        night_duty_ratio_30d = None
    else:
        night_count_30d = sum(1 for d in duties_30d if bool(d.get("is_night", False)))
        night_duty_ratio_30d = round(float(night_count_30d) / float(len(duties_30d)), 4)

    # 5. consecutive_duty_days (streak ending at cutoff_date - 1)
    if duties is None or len(duties) == 0:
        consecutive_duty_days = None
    else:
        streak = 0
        curr = cutoff_date - timedelta(days=1)
        while curr in duties_by_date:
            streak += 1
            curr -= timedelta(days=1)
        consecutive_duty_days = float(streak)

    # Filter rest records: personnel_id == person, record_date < cutoff_date
    person_rest = []
    for r in (rest_records or []):
        if str(r.get("personnel_id", "")) != str(personnel_id):
            continue
        r_date = _parse_date(r.get("record_date") or r.get("date"))
        if r_date is None or r_date >= cutoff_date:
            continue
        person_rest.append({**r, "_date": r_date})

    # Rest records in 14d and 30d windows
    rest_14d = [r for r in person_rest if w14_start <= r["_date"] < cutoff_date]
    rest_30d = [r for r in person_rest if w30_start <= r["_date"] < cutoff_date]

    # Validate rest hours via Data Quality Layer
    valid_rest_hours_14d = []
    for r in rest_14d:
        vres = validate_rest_hours(r.get("rest_hours"))
        if vres.is_valid and vres.value is not None:
            valid_rest_hours_14d.append(vres.value)

    valid_rest_hours_30d = []
    for r in rest_30d:
        vres = validate_rest_hours(r.get("rest_hours"))
        if vres.is_valid and vres.value is not None:
            valid_rest_hours_30d.append(vres.value)

    # 6. min_rest_hours_14d
    if rest_records is None or len(valid_rest_hours_14d) == 0:
        min_rest_hours_14d = None
    else:
        min_rest_hours_14d = round(float(min(valid_rest_hours_14d)), 2)

    # 7. avg_rest_hours_30d
    if rest_records is None or len(valid_rest_hours_30d) == 0:
        avg_rest_hours_30d = None
    else:
        avg_rest_hours_30d = round(float(sum(valid_rest_hours_30d)) / float(len(valid_rest_hours_30d)), 2)

    # 8. quick_return_count_30d
    if rest_records is None or len(rest_30d) == 0:
        quick_return_count_30d = None
    else:
        qr_count = 0
        for r in rest_30d:
            gap_res = validate_rest_gap(r.get("rest_gap_hours"))
            if gap_res.is_valid and gap_res.value is not None:
                if gap_res.value < QUICK_RETURN_THRESHOLD_HOURS:
                    qr_count += 1
        quick_return_count_30d = float(qr_count)

    # 9. deployment_days_30d (days in [w30_start, cutoff_date) capped at cutoff_date)
    deployed_dates: Set[date] = set()
    for dep in (deployments or []):
        if str(dep.get("personnel_id", "")) != str(personnel_id):
            continue
        d_start = _parse_date(dep.get("start_date"))
        if d_start is None or d_start >= cutoff_date:
            continue
        d_end = _parse_date(dep.get("end_date")) or (cutoff_date - timedelta(days=1))
        # Clamp to [w30_start, cutoff_date - 1]
        cur_d = max(d_start, w30_start)
        end_d = min(d_end, cutoff_date - timedelta(days=1))
        while cur_d <= end_d:
            deployed_dates.add(cur_d)
            cur_d += timedelta(days=1)
    deployment_days_30d = float(len(deployed_dates))

    # 10. training_days_30d
    training_dates: Set[date] = set()
    for trn in (training or []):
        if str(trn.get("personnel_id", "")) != str(personnel_id):
            continue
        t_start = _parse_date(trn.get("start_date"))
        if t_start is None or t_start >= cutoff_date:
            continue
        t_end = _parse_date(trn.get("end_date")) or t_start
        cur_t = max(t_start, w30_start)
        end_t = min(t_end, cutoff_date - timedelta(days=1))
        while cur_t <= end_t:
            training_dates.add(cur_t)
            cur_t += timedelta(days=1)
    training_days_30d = float(len(training_dates))

    # 11. staffing_ratio_7d (most recent record for unit_id in [w7_start, cutoff_date))
    unit_staffing = []
    for s in (staffing or []):
        if str(s.get("unit_id", "")) != str(unit_id):
            continue
        s_date = _parse_date(s.get("record_date") or s.get("date"))
        if s_date is None or s_date >= cutoff_date or s_date < w7_start:
            continue
        unit_staffing.append({**s, "_date": s_date})

    if not unit_staffing:
        staffing_ratio_7d = None
    else:
        unit_staffing.sort(key=lambda x: x["_date"], reverse=True)
        latest_s = unit_staffing[0]
        avail = float(latest_s.get("available_strength", 0))
        req = float(latest_s.get("required_strength", 0))
        staffing_ratio_7d = round(avail / req, 4) if req > 0 else None

    # 12. workload_change_14v14
    duties_prior_14 = [d for d in person_duties if w28_start <= d["_date"] < w14_start]
    hours_curr_14 = sum(float(d.get("hours", 0.0) or 0.0) for d in duties_14d)
    hours_prior_14 = sum(float(d.get("hours", 0.0) or 0.0) for d in duties_prior_14)

    if not duties_prior_14 or hours_prior_14 <= 0.0:
        workload_change_14v14 = None
    else:
        workload_change_14v14 = round(100.0 * (hours_curr_14 - hours_prior_14) / hours_prior_14, 2)

    # 13. ewma_workload (daily duty hours through cutoff_date - 1, lambda = 0.30)
    # Build 30-day chronological daily duty series
    daily_series: List[float] = []
    d_day = w30_start
    while d_day < cutoff_date:
        day_duties = duties_by_date.get(d_day, [])
        day_h = sum(float(d.get("hours", 0.0) or 0.0) for d in day_duties)
        daily_series.append(day_h)
        d_day += timedelta(days=1)

    if not daily_series or sum(daily_series) == 0.0 and len(person_duties) == 0:
        ewma_workload = None
    else:
        ewma_workload = calculate_ewma(daily_series, lambda_param=0.30)

    # 14. baseline_z_workload (lookback 56d prior to cutoff_date)
    history_daily: List[float] = []
    h_day = w56_start
    while h_day < cutoff_date - timedelta(days=1):
        h_duties = duties_by_date.get(h_day, [])
        h_hours = sum(float(d.get("hours", 0.0) or 0.0) for d in h_duties)
        history_daily.append(h_hours)
        h_day += timedelta(days=1)

    curr_day_duties = duties_by_date.get(cutoff_date - timedelta(days=1), [])
    curr_day_hours = sum(float(d.get("hours", 0.0) or 0.0) for d in curr_day_duties)

    med, mad = calculate_median_mad(history_daily, min_observations=5)
    if med is not None and mad is not None:
        baseline_z_workload = calculate_robust_z_score(curr_day_hours, med, mad)
    else:
        baseline_z_workload = None

    # 15. peer_deviation_workload
    if peer_cohort_duties_30d and len(peer_cohort_duties_30d) >= 5 and duty_hours_30d is not None:
        p_med, p_mad = calculate_median_mad(peer_cohort_duties_30d, min_observations=5)
        if p_med is not None and p_mad is not None:
            peer_deviation_workload = calculate_robust_z_score(duty_hours_30d, p_med, p_mad)
        else:
            peer_deviation_workload = None
    else:
        peer_deviation_workload = None

    return {
        "duty_hours_7d": duty_hours_7d,
        "duty_hours_30d": duty_hours_30d,
        "night_duty_count_14d": night_duty_count_14d,
        "night_duty_ratio_30d": night_duty_ratio_30d,
        "consecutive_duty_days": consecutive_duty_days,
        "min_rest_hours_14d": min_rest_hours_14d,
        "avg_rest_hours_30d": avg_rest_hours_30d,
        "quick_return_count_30d": quick_return_count_30d,
        "deployment_days_30d": deployment_days_30d,
        "training_days_30d": training_days_30d,
        "staffing_ratio_7d": staffing_ratio_7d,
        "workload_change_14v14": workload_change_14v14,
        "ewma_workload": ewma_workload,
        "baseline_z_workload": baseline_z_workload,
        "peer_deviation_workload": peer_deviation_workload,
    }


def extract_hr_features(df: pd.DataFrame, feature_set: str = "B") -> pd.DataFrame:
    """
    Extracts strictly approved Model-A features from a precomputed dataset.
    - feature_set 'B' (default, canonical): 15 operational features excluding leave features.
    - feature_set 'A' (comparative A/B): 17 features including historical leave features.
    """
    selected_features = FEATURE_SET_A if feature_set.upper() == "A" else FEATURE_SET_B
    missing_cols = [col for col in selected_features if col not in df.columns]
    if missing_cols:
        raise ValueError(
            f"DataFrame is missing required feature columns for set {feature_set}: {missing_cols}"
        )
    return df[selected_features].copy()


__all__ = [
    "MODEL_A_FEATURE_NAMES",
    "HISTORICAL_LEAVE_FEATURE_NAMES",
    "FEATURE_SET_A",
    "FEATURE_SET_B",
    "QUICK_RETURN_THRESHOLD_HOURS",
    "extract_hr_features_for_cutoff",
    "extract_hr_features",
]
