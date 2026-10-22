"""
Unit tests for Task 06: Personal Baseline (PRAHARI Model-A).
Tests required:
- normal data (Median + MAD z-score)
- single observation (INSUFFICIENT_HISTORY)
- constant history (zero-MAD handling: z=0 if current==median, z=None + direction if current!=median)
- missing history (INSUFFICIENT_HISTORY)
- outlier-heavy history (robustness of Median+MAD vs mean/std)
- invalid values (non-finite and missing values properly rejected)
"""

import math
import pytest

from app.analytics.baseline import (
    MAD_SCALE_FACTOR,
    BaselineResult,
    BaselineStatus,
    DeviationDirection,
    calculate_median_mad,
    calculate_robust_z_score,
    compute_personal_baseline,
)


def test_t06_normal_data_robust_z_score():
    """Verify standard baseline calculation with Median + MAD."""
    history = [50.0, 52.0, 48.0, 51.0, 49.0, 50.0, 53.0, 47.0]
    # Median is 50.0, MAD is 1.5
    med, mad = calculate_median_mad(history)
    assert med == 50.0
    assert mad == 1.5

    # Current value higher than median
    res_above = compute_personal_baseline(history, current_val=55.0)
    assert res_above.status == BaselineStatus.VALID
    assert res_above.zero_mad is False
    assert res_above.direction == DeviationDirection.ABOVE
    expected_z = round((55.0 - 50.0) / (MAD_SCALE_FACTOR * 1.5), 4)
    assert res_above.z_score == expected_z
    assert res_above.z_score > 0

    # Current value lower than median
    res_below = compute_personal_baseline(history, current_val=45.0)
    assert res_below.direction == DeviationDirection.BELOW
    assert res_below.z_score < 0


def test_t06_single_observation_insufficient_history():
    """Verify single observation returns INSUFFICIENT_HISTORY."""
    res = compute_personal_baseline([50.0], current_val=55.0, min_observations=5)
    assert res.status == BaselineStatus.INSUFFICIENT_HISTORY
    assert res.z_score is None
    assert res.median is None
    assert res.mad is None
    assert res.observation_count == 1
    assert "Insufficient history" in (res.reason or "")


def test_t06_constant_history_zero_mad():
    """
    CRITICAL CONTRACT:
    When MAD = 0:
    - If current == median: z = 0.0, direction = EQUAL, zero_mad = True
    - If current != median: z = None (NEVER fabricated 3.0 or 0.0!),
      direction = ABOVE/BELOW, zero_mad = True, reason = 'ZERO_MAD_NONZERO_DEVIATION'
    """
    history = [50.0, 50.0, 50.0, 50.0, 50.0, 50.0]
    med, mad = calculate_median_mad(history)
    assert med == 50.0
    assert mad == 0.0

    # Case A: current matches constant history exactly
    res_equal = compute_personal_baseline(history, current_val=50.0)
    assert res_equal.status == BaselineStatus.VALID
    assert res_equal.zero_mad is True
    assert res_equal.z_score == 0.0
    assert res_equal.direction == DeviationDirection.EQUAL
    assert res_equal.reason is None

    # Case B: current differs from constant history (elevated)
    res_diff_above = compute_personal_baseline(history, current_val=65.0)
    assert res_diff_above.status == BaselineStatus.VALID
    assert res_diff_above.zero_mad is True
    assert res_diff_above.z_score is None  # MUST NOT fabricate 3.0 or 0.0!
    assert res_diff_above.direction == DeviationDirection.ABOVE
    assert res_diff_above.reason == "ZERO_MAD_NONZERO_DEVIATION"

    # Case C: current differs from constant history (lower)
    res_diff_below = compute_personal_baseline(history, current_val=35.0)
    assert res_diff_below.status == BaselineStatus.VALID
    assert res_diff_below.zero_mad is True
    assert res_diff_below.z_score is None
    assert res_diff_below.direction == DeviationDirection.BELOW
    assert res_diff_below.reason == "ZERO_MAD_NONZERO_DEVIATION"


def test_t06_missing_history_insufficient_history():
    """Verify empty or None history returns INSUFFICIENT_HISTORY."""
    res_empty = compute_personal_baseline([], current_val=50.0)
    assert res_empty.status == BaselineStatus.INSUFFICIENT_HISTORY
    assert res_empty.z_score is None
    assert res_empty.observation_count == 0

    res_none = compute_personal_baseline(None, current_val=50.0)
    assert res_none.status == BaselineStatus.INSUFFICIENT_HISTORY
    assert res_none.z_score is None


def test_t06_outlier_heavy_history_robustness():
    """Verify that Median+MAD is robust against extreme outliers compared to Mean/Std."""
    # Clean history of 50s, with one huge outlier of 1000
    history = [50.0, 51.0, 49.0, 50.0, 50.0, 52.0, 1000.0]
    med, mad = calculate_median_mad(history)
    assert med == 50.0  # Median completely unaffected by 1000
    assert mad <= 1.0   # MAD completely unaffected

    res = compute_personal_baseline(history, current_val=55.0)
    assert res.status == BaselineStatus.VALID
    assert res.median == 50.0
    # A standard deviation would be corrupted to >300, falsely making 55 look normal (z < 0.1).
    # Robust z-score correctly identifies 55 as an elevated departure (> 3.0).
    assert res.z_score > 3.0


def test_t06_invalid_values_handled_truthfully():
    """Verify non-finite and missing current values return appropriate status."""
    history = [50.0, 52.0, 48.0, 51.0, 49.0, 50.0]

    # Current value is None
    res_none = compute_personal_baseline(history, current_val=None)
    assert res_none.status == BaselineStatus.CURRENT_VALUE_UNAVAILABLE
    assert res_none.z_score is None
    assert res_none.median == 50.0
    assert res_none.mad is not None

    # Current value is NaN
    res_nan = compute_personal_baseline(history, current_val=float("nan"))
    assert res_nan.status == BaselineStatus.COMPUTATION_ERROR
    assert res_nan.z_score is None

    # Current value is Inf
    res_inf = compute_personal_baseline(history, current_val=float("inf"))
    assert res_inf.status == BaselineStatus.COMPUTATION_ERROR
    assert res_inf.z_score is None

    # Current value is non-numeric string
    res_str = compute_personal_baseline(history, current_val="invalid")
    assert res_str.status == BaselineStatus.COMPUTATION_ERROR
    assert res_str.z_score is None
