"""
Unit tests for Task 10: Model-A Feature Engineering.
Tests required:
- future-row exclusion (adding future rows has zero effect on features)
- boundary date behavior (record at T-1 included, record at T excluded)
- missing windows (truthfully return None, never fabricated/zero-filled)
- person isolation (Person A unaffected by Person B's data)
- unit aggregation correctness (staffing and peer metrics scoped to person's unit)
"""

from datetime import date, timedelta
import pandas as pd
import pytest

from app.ml.features_hr import (
    MODEL_A_FEATURE_NAMES,
    compute_operational_features_at_cutoff,
    extract_hr_features,
)


def test_t10_feature_count_and_order():
    """Verify exactly 15 approved features in exact approved order."""
    assert len(MODEL_A_FEATURE_NAMES) == 15
    expected_15 = [
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
    assert MODEL_A_FEATURE_NAMES == expected_15

    # Excluded leave features must NOT be present
    assert "leave_frequency_90d" not in MODEL_A_FEATURE_NAMES
    assert "leave_gap_variability_90d" not in MODEL_A_FEATURE_NAMES


def test_t10_future_row_exclusion():
    """Verify records with timestamps > T are strictly excluded with zero impact."""
    cutoff = date(2026, 3, 1)
    person_id = "P001"
    unit_id = "U01"

    past_duties = [
        {"personnel_id": person_id, "date": "2026-02-27", "hours": 8.0, "is_night": False},
        {"personnel_id": person_id, "date": "2026-02-28", "hours": 12.0, "is_night": True},
    ]
    past_rest = [
        {"personnel_id": person_id, "record_date": "2026-02-27", "rest_hours": 8.0, "rest_gap_hours": 14.0},
        {"personnel_id": person_id, "record_date": "2026-02-28", "rest_hours": 6.0, "rest_gap_hours": 10.0},
    ]

    base_features = compute_operational_features_at_cutoff(
        as_of=cutoff,
        personnel_id=person_id,
        unit_id=unit_id,
        duties=past_duties,
        rest_records=past_rest,
    )

    # Now add FUTURE records (> cutoff)
    future_duties = past_duties + [
        {"personnel_id": person_id, "date": "2026-03-02", "hours": 16.0, "is_night": True},
        {"personnel_id": person_id, "date": "2026-03-10", "hours": 24.0, "is_night": True},
    ]
    future_rest = past_rest + [
        {"personnel_id": person_id, "record_date": "2026-03-02", "rest_hours": 2.0, "rest_gap_hours": 4.0},
        {"personnel_id": person_id, "record_date": "2026-03-05", "rest_hours": 0.0, "rest_gap_hours": 2.0},
    ]

    features_with_future = compute_operational_features_at_cutoff(
        as_of=cutoff,
        personnel_id=person_id,
        unit_id=unit_id,
        duties=future_duties,
        rest_records=future_rest,
    )

    # All 15 features must be bitwise identical
    for fn in MODEL_A_FEATURE_NAMES:
        assert features_with_future[fn] == base_features[fn], f"Feature {fn} changed when future records were added!"


def test_t10_boundary_date_behavior():
    """Verify record at T-1 is included, record at T is excluded from trailing lookback."""
    cutoff = date(2026, 3, 1)
    person_id = "P001"
    unit_id = "U01"

    # T-1 duty
    duties_t_minus_1 = [
        {"personnel_id": person_id, "date": "2026-02-28", "hours": 8.0, "is_night": False},
    ]
    feat_t_minus_1 = compute_operational_features_at_cutoff(
        as_of=cutoff,
        personnel_id=person_id,
        unit_id=unit_id,
        duties=duties_t_minus_1,
        rest_records=[],
    )
    assert feat_t_minus_1["duty_hours_7d"] == 8.0

    # Exactly on T duty (must not enter trailing [T-7d, T) window)
    duties_on_t = [
        {"personnel_id": person_id, "date": "2026-03-01", "hours": 10.0, "is_night": False},
    ]
    feat_on_t = compute_operational_features_at_cutoff(
        as_of=cutoff,
        personnel_id=person_id,
        unit_id=unit_id,
        duties=duties_on_t,
        rest_records=[],
    )
    assert feat_on_t["duty_hours_7d"] == 0.0 or feat_on_t["duty_hours_7d"] is None


def test_t10_missing_windows_truthful_none():
    """Verify missing source windows return None and are never fabricated/zero-filled."""
    cutoff = date(2026, 3, 1)
    person_id = "P001"
    unit_id = "U01"

    # Empty rest_records provided
    features = compute_operational_features_at_cutoff(
        as_of=cutoff,
        personnel_id=person_id,
        unit_id=unit_id,
        duties=[],
        rest_records=[],  # Missing rest data
        staffing=[],      # Missing staffing
    )
    # Rest features MUST be None (not 0.0, not mean)
    assert features["min_rest_hours_14d"] is None
    assert features["avg_rest_hours_30d"] is None
    assert features["quick_return_count_30d"] is None
    assert features["staffing_ratio_7d"] is None


def test_t10_person_isolation():
    """Verify Person A's features are completely isolated from Person B's records."""
    cutoff = date(2026, 3, 1)

    mixed_duties = [
        {"personnel_id": "PERSON_A", "date": "2026-02-25", "hours": 8.0, "is_night": False},
        {"personnel_id": "PERSON_A", "date": "2026-02-26", "hours": 8.0, "is_night": False},
        # Heavy duties for Person B
        {"personnel_id": "PERSON_B", "date": "2026-02-25", "hours": 16.0, "is_night": True},
        {"personnel_id": "PERSON_B", "date": "2026-02-26", "hours": 16.0, "is_night": True},
        {"personnel_id": "PERSON_B", "date": "2026-02-27", "hours": 16.0, "is_night": True},
    ]

    feat_a = compute_operational_features_at_cutoff(
        as_of=cutoff,
        personnel_id="PERSON_A",
        unit_id="U01",
        duties=mixed_duties,
        rest_records=[],
    )
    assert feat_a["duty_hours_7d"] == 16.0
    assert feat_a["night_duty_count_14d"] == 0.0

    feat_b = compute_operational_features_at_cutoff(
        as_of=cutoff,
        personnel_id="PERSON_B",
        unit_id="U01",
        duties=mixed_duties,
        rest_records=[],
    )
    assert feat_b["duty_hours_7d"] == 48.0
    assert feat_b["night_duty_count_14d"] == 3.0


def test_t10_unit_aggregation_correctness():
    """Verify staffing and peer metrics are correctly scoped to person's unit."""
    cutoff = date(2026, 3, 1)
    staffing_records = [
        {"unit_id": "UNIT_ALPHA", "record_date": "2026-02-27", "available_strength": 80, "required_strength": 100},
        {"unit_id": "UNIT_BRAVO", "record_date": "2026-02-27", "available_strength": 120, "required_strength": 100},
    ]

    feat_alpha = compute_operational_features_at_cutoff(
        as_of=cutoff,
        personnel_id="P_ALPHA",
        unit_id="UNIT_ALPHA",
        duties=[],
        rest_records=[],
        staffing=staffing_records,
    )
    assert feat_alpha["staffing_ratio_7d"] == 0.80

    feat_bravo = compute_operational_features_at_cutoff(
        as_of=cutoff,
        personnel_id="P_BRAVO",
        unit_id="UNIT_BRAVO",
        duties=[],
        rest_records=[],
        staffing=staffing_records,
    )
    assert feat_bravo["staffing_ratio_7d"] == 1.20


def test_t10_extract_hr_features_dataframe():
    """Verify extract_hr_features filters DataFrame strictly to 15 approved columns."""
    sample_data = {col: [1.0, 2.0] for col in MODEL_A_FEATURE_NAMES}
    sample_data["unauthorized_leave_freq"] = [5.0, 6.0]
    sample_data["target_future_label"] = [0, 1]
    df = pd.DataFrame(sample_data)

    extracted = extract_hr_features(df)
    assert list(extracted.columns) == MODEL_A_FEATURE_NAMES
    assert "unauthorized_leave_freq" not in extracted.columns
    assert "target_future_label" not in extracted.columns
