"""Tests for PRAHARI Task 25: Operational Confidence & Epistemological Reliability."""

import math
import pytest

from app.ml.confidence import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MODERATE,
    CONFIDENCE_UNAVAILABLE,
    calculate_feature_completeness,
    compute_operational_confidence,
)


def test_confidence_formula_mathematical_correctness():
    """Verify confidence = data_completeness * model_availability * calibration_reliability."""
    score, desc, bd = compute_operational_confidence(
        data_completeness=0.90,
        model_availability=1.0,
        calibration_reliability=0.95,
    )
    expected = round(0.90 * 1.0 * 0.95, 4)  # 0.8550
    assert score == expected
    assert desc == CONFIDENCE_HIGH
    assert bd["status"] == "VALID"
    assert bd["data_completeness"] == 0.90
    assert bd["model_availability"] == 1.0
    assert bd["calibration_reliability"] == 0.95


def test_artifact_unavailable_behavior():
    """Verify that when artifact is missing/corrupt, confidence is strictly 0.0 with status MODEL_UNAVAILABLE."""
    score, desc, bd = compute_operational_confidence(
        data_completeness=1.0,
        model_availability=0.0,
        calibration_reliability=0.95,
    )
    assert score == 0.0
    assert desc == CONFIDENCE_UNAVAILABLE
    assert bd["status"] == "MODEL_UNAVAILABLE"
    assert "unavailable" in bd["rationale"].lower()


def test_confidence_descriptors_partition():
    """Verify categorical ranges: HIGH (>=0.80), MODERATE (0.50-0.79), LOW (<0.50)."""
    # High
    s_hi, d_hi, _ = compute_operational_confidence(0.95, 1.0, 0.90)
    assert d_hi == CONFIDENCE_HIGH

    # Moderate
    s_mod, d_mod, _ = compute_operational_confidence(0.70, 1.0, 0.90)
    assert d_mod == CONFIDENCE_MODERATE

    # Low
    s_lo, d_lo, _ = compute_operational_confidence(0.40, 1.0, 0.80)
    assert d_lo == CONFIDENCE_LOW


def test_feature_completeness_calculation():
    """Verify calculation of completeness fraction against expected feature allowlist."""
    features = ["f1", "f2", "f3", "f4", "f5"]
    data_dict = {
        "f1": 12.5,
        "f2": 0.0,
        "f3": None,
        "f4": float("nan"),
        "f5": 45.0,
    }
    # f1, f2, f5 valid -> 3/5 = 0.60
    comp = calculate_feature_completeness(data_dict, features)
    assert comp == 0.60


def test_confidence_is_strictly_independent_of_prediction_probability():
    """Verify that confidence measures evidence quality, not prediction probability."""
    # Case A: Low event probability (p = 0.03) with complete data -> High confidence
    score_a, desc_a, _ = compute_operational_confidence(1.0, 1.0, 0.95)
    assert desc_a == CONFIDENCE_HIGH

    # Case B: High event probability (p = 0.85) with partial/sparse data -> Low confidence
    score_b, desc_b, _ = compute_operational_confidence(0.40, 1.0, 0.95)
    assert desc_b == CONFIDENCE_LOW
