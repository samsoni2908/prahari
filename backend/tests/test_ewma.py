"""
Unit tests for Task 07: EWMA Engine (PRAHARI Model-A).
Tests required:
- first observation (initialization with S_0 = X_0, never artificial zero)
- multiple observations (correct recurrence progression)
- missing observation (segment break, no silent time compression)
- known hand-calculated sequence (lambda = 0.30 exact progression)
"""

import pytest

from app.analytics.ewma import (
    DEFAULT_LAMBDA,
    EwmaResult,
    EwmaStatus,
    TrendDirection,
    calculate_ewma,
    compute_ewma_trend,
)


def test_t07_first_observation_initialization_no_artificial_zero():
    """Verify first observation initializes S_0 = X_0 and NEVER with artificial zero."""
    # A single observation of 50.0 must yield 50.0
    res = calculate_ewma([50.0], lambda_param=0.30)
    assert res == 50.0  # NOT 0.30 * 50.0 = 15.0!

    res_trend = compute_ewma_trend([50.0], lambda_param=0.30)
    assert res_trend.current_ewma == 50.0
    # A lone point has no trend (minimum segment length is 2)
    assert res_trend.status == EwmaStatus.INSUFFICIENT_HISTORY
    assert res_trend.trend is None
    assert res_trend.segment_length == 1


def test_t07_multiple_observations_progression():
    """Verify correct sequential progression over multiple observations."""
    # Series: [50.0, 60.0, 70.0] with lambda = 0.30
    # S_0 = 50.0
    # S_1 = 0.30 * 60.0 + 0.70 * 50.0 = 18.0 + 35.0 = 53.0
    # S_2 = 0.30 * 70.0 + 0.70 * 53.0 = 21.0 + 37.1 = 58.1
    res = calculate_ewma([50.0, 60.0, 70.0], lambda_param=0.30)
    assert res == 58.1

    res_trend = compute_ewma_trend([50.0, 60.0, 70.0], lambda_param=0.30)
    assert res_trend.status == EwmaStatus.VALID
    assert res_trend.current_ewma == 58.1
    assert res_trend.delta == round(58.1 - 53.0, 4)  # 5.1
    assert res_trend.trend == TrendDirection.RISING
    assert res_trend.segment_length == 3


def test_t07_missing_observation_segment_break():
    """
    CRITICAL CONTRACT (docs/ml.md §8.1):
    A missing day breaks the segment; resumes with new initialization S_t = X_t.
    Never silently compresses time or carries an old value as current.
    """
    # Series with missing middle point: [10.0, 20.0, None, 50.0]
    # S_0 = 10.0, S_1 = 13.0
    # None -> breaks segment
    # S_3 = 50.0 (new initialization with X_3, NOT carrying 13.0 forward!)
    res_break = calculate_ewma([10.0, 20.0, None, 50.0], lambda_param=0.30, break_on_missing=True)
    assert res_break == 50.0

    res_trend = compute_ewma_trend([10.0, 20.0, None, 50.0], lambda_param=0.30)
    assert res_trend.current_ewma == 50.0
    assert res_trend.segment_length == 1
    assert res_trend.status == EwmaStatus.INSUFFICIENT_HISTORY  # Lone point after break has no trend

    # If current (latest) observation is missing
    res_current_missing = compute_ewma_trend([10.0, 20.0, 30.0, None], lambda_param=0.30)
    assert res_current_missing.status == EwmaStatus.CURRENT_VALUE_UNAVAILABLE
    assert res_current_missing.current_ewma is None

    # Empty series
    res_empty = calculate_ewma([])
    assert res_empty is None


def test_t07_known_hand_calculated_sequence():
    """
    HAND-CALCULATED BENCHMARK:
    lambda = 0.30, Series: [10.0, 20.0, 30.0, 40.0]
    t = 0: S_0 = 10.00
    t = 1: S_1 = 0.30 * 20.0 + 0.70 * 10.00 = 6.0 + 7.00 = 13.00
    t = 2: S_2 = 0.30 * 30.0 + 0.70 * 13.00 = 9.0 + 9.10 = 18.10
    t = 3: S_3 = 0.30 * 40.0 + 0.70 * 18.10 = 12.0 + 12.67 = 24.67
    """
    series = [10.0, 20.0, 30.0, 40.0]
    ewma_val = calculate_ewma(series, lambda_param=0.30)
    assert ewma_val == 24.67

    trend_res = compute_ewma_trend(series, lambda_param=0.30)
    assert trend_res.status == EwmaStatus.VALID
    assert trend_res.current_ewma == 24.67
    assert trend_res.ewma_series == [10.0, 13.0, 18.1, 24.67]
    assert trend_res.delta == round(24.67 - 18.10, 4)  # 6.57
    assert trend_res.trend == TrendDirection.RISING


def test_t07_default_lambda_replaces_legacy_0_20():
    """Verify default lambda parameter is strictly 0.30, replacing legacy 0.20."""
    assert DEFAULT_LAMBDA == 0.30

    # With lambda = 0.30, [10.0, 20.0] -> 13.00
    # With legacy 0.20, [10.0, 20.0] -> 12.00
    default_res = calculate_ewma([10.0, 20.0])
    assert default_res == 13.00  # Proves 0.30 is active default
