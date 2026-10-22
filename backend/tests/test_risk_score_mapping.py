"""Tests for PRAHARI Task 22: Risk Score & Attention Band Mapping."""

import math
import numpy as np
import pytest

from app.ml.risk_score import (
    BAND_HIGH,
    BAND_LOW,
    BAND_MEDIUM,
    BAND_NOT_COMPUTED,
    DEFAULT_TAU_HIGH,
    DEFAULT_TAU_MED,
    assess_operational_trend,
    determine_operational_band,
    execute_operational_pipeline,
    map_probability_to_operational_score,
)
from tools.training.floors import (
    SAFETY_FLOORS_STATUS,
    apply_operational_safety_floors,
    get_safety_floors_status,
)


def test_piecewise_linear_monotonic_mapping_critical_points():
    """Verify exact score at key inflection and boundary points."""
    # p = 0.0 -> score = 0.0
    s0, st0 = map_probability_to_operational_score(0.0)
    assert st0 == "VALID"
    assert s0 == 0.0

    # p = tau_med / 2 (0.0375) -> score = 20.0
    s_low, st_low = map_probability_to_operational_score(0.0375)
    assert st_low == "VALID"
    assert s_low == 20.0

    # p = tau_med (0.075) -> score = 40.0 (Boundary of MEDIUM)
    s_med, st_med = map_probability_to_operational_score(0.075)
    assert st_med == "VALID"
    assert s_med == 40.0

    # p = (0.075 + 0.15) / 2 = 0.1125 -> score = 55.0
    s_mid, st_mid = map_probability_to_operational_score(0.1125)
    assert st_mid == "VALID"
    assert s_mid == 55.0

    # p = tau_high (0.150) -> score = 70.0 (Boundary of HIGH alert)
    s_high, st_high = map_probability_to_operational_score(0.150)
    assert st_high == "VALID"
    assert s_high == 70.0

    # p = 0.575 (halfway between 0.15 and 1.0) -> score = 85.0
    s_hmid, st_hmid = map_probability_to_operational_score(0.575)
    assert st_hmid == "VALID"
    assert s_hmid == 85.0

    # p = 1.0 -> score = 100.0
    s1, st1 = map_probability_to_operational_score(1.0)
    assert st1 == "VALID"
    assert s1 == 100.0


def test_monotonicity_across_probability_range():
    """Verify that score is strictly monotonic across [0.0, 1.0]."""
    probs = np.linspace(0.0, 1.0, 1001)
    scores = []
    for p in probs:
        s, st = map_probability_to_operational_score(float(p))
        assert st == "VALID"
        assert s is not None
        assert 0.0 <= s <= 100.0
        scores.append(s)

    # Monotonicity check: scores[i] <= scores[i+1]
    for i in range(len(scores) - 1):
        assert scores[i] <= scores[i + 1], f"Monotonicity violation: p={probs[i]} (s={scores[i]}) vs p={probs[i+1]} (s={scores[i+1]})"


def test_canonical_operational_bands():
    """Verify strict 3-band categorization: LOW (0â€“39), MEDIUM (40â€“69), HIGH (70â€“100)."""
    assert determine_operational_band(0.0) == BAND_LOW
    assert determine_operational_band(39.9) == BAND_LOW
    assert determine_operational_band(40.0) == BAND_MEDIUM
    assert determine_operational_band(69.9) == BAND_MEDIUM
    assert determine_operational_band(70.0) == BAND_HIGH
    assert determine_operational_band(100.0) == BAND_HIGH
    assert determine_operational_band(None) == BAND_NOT_COMPUTED


def test_truthful_state_on_invalid_inputs():
    """Verify that missing/corrupt inputs produce explicit statuses, never fallback scores."""
    # None input
    s, st = map_probability_to_operational_score(None)
    assert s is None
    assert st == "NOT_COMPUTED"

    # NaN input
    s_nan, st_nan = map_probability_to_operational_score(float("nan"))
    assert s_nan is None
    assert st_nan == "INVALID_INPUT"

    # Inf input
    s_inf, st_inf = map_probability_to_operational_score(float("inf"))
    assert s_inf is None
    assert st_inf == "INVALID_INPUT"

    # Out of bounds
    s_neg, st_neg = map_probability_to_operational_score(-0.05)
    assert s_neg is None
    assert st_neg == "OUT_OF_BOUNDS"

    s_over, st_over = map_probability_to_operational_score(1.05)
    assert s_over is None
    assert st_over == "OUT_OF_BOUNDS"


def test_operational_trend_assessment():
    """Verify trend direction logic from prior history."""
    # Insufficient history
    assert assess_operational_trend(50.0, None) == "INSUFFICIENT_HISTORY"
    assert assess_operational_trend(50.0, []) == "INSUFFICIENT_HISTORY"
    assert assess_operational_trend(None, [50.0]) == "NOT_COMPUTED"

    # Valid trend comparisons
    assert assess_operational_trend(55.0, [50.0], tolerance=2.0) == "RISING"
    assert assess_operational_trend(45.0, [50.0], tolerance=2.0) == "FALLING"
    assert assess_operational_trend(51.0, [50.0], tolerance=2.0) == "STABLE"
    assert assess_operational_trend(49.0, [50.0], tolerance=2.0) == "STABLE"


def test_full_pipeline_execution():
    """Verify end-to-end pipeline execution from probability to final band."""
    # Normal case below threshold
    res_low = execute_operational_pipeline(0.04, prior_scores=[20.0])
    assert res_low["status"] == "VALID"
    assert res_low["raw_operational_score"] < 40.0
    assert res_low["operational_band"] == BAND_LOW
    assert res_low["safety_floors_status"] == "SAFETY_FLOORS_NOT_FINALIZED"

    # Case at alert threshold (0.15 -> score 70.0 -> HIGH)
    res_high = execute_operational_pipeline(0.15, prior_scores=[50.0])
    assert res_high["status"] == "VALID"
    assert res_high["raw_operational_score"] == 70.0
    assert res_high["operational_band"] == BAND_HIGH
    assert res_high["operational_trend"] == "RISING"

    # Invalid probability produces clean error dictionary
    res_err = execute_operational_pipeline(None)
    assert res_err["status"] == "NOT_COMPUTED"
    assert res_err["final_operational_score"] is None
    assert res_err["operational_band"] == BAND_NOT_COMPUTED


def test_safety_floors_task23_contract():
    """Verify Task 23 contract: safety floors are outside ML and reported truthfully."""
    status = get_safety_floors_status()
    assert status in ("NO_APPROVED_SAFETY_FLOORS", "SAFETY_FLOORS_NOT_FINALIZED")

    score, floors, diag = apply_operational_safety_floors(50.0)
    assert score == 50.0
    assert diag["status"] in ("NO_APPROVED_SAFETY_FLOORS", "SAFETY_FLOORS_NOT_FINALIZED")
    assert diag["override_applied"] is False

    # Pipeline with floor override capability
    res_override = execute_operational_pipeline(0.05, safety_floor_override_score=75.0)
    assert res_override["raw_operational_score"] < 40.0
    assert res_override["final_operational_score"] == 75.0
    assert res_override["safety_floors_applied"] is True
    assert res_override["operational_band"] == BAND_HIGH

    # Floor cannot lower a higher model score
    res_preserve = execute_operational_pipeline(0.50, safety_floor_override_score=75.0)
    assert res_preserve["raw_operational_score"] > 75.0
    assert res_preserve["final_operational_score"] == res_preserve["raw_operational_score"]
    assert res_preserve["safety_floors_applied"] is False
