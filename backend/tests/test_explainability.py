"""Tests for PRAHARI Task 24: Operational Explainability & Driver Ordering."""

import numpy as np
import pytest

from app.ml.explain import (
    FACTOR_CATEGORY_MAP,
    FACTOR_LABEL_MAP,
    explain_operational_prediction,
    sanitize_operational_text,
)
from tools.training.policy_config import BANNED_PHRASES


def test_banned_wording_filter():
    """Verify that no banned clinical / diagnostic words appear in any factor label or category."""
    for fn, label in FACTOR_LABEL_MAP.items():
        l_lower = label.lower()
        for phrase in BANNED_PHRASES:
            assert phrase.lower() not in l_lower, f"Banned phrase '{phrase}' in label '{label}'"

    for fn, cat in FACTOR_CATEGORY_MAP.items():
        c_lower = cat.lower()
        for phrase in BANNED_PHRASES:
            assert phrase.lower() not in c_lower, f"Banned phrase '{phrase}' in category '{cat}'"

    # Verify sanitizer raises ValueError on banned word
    with pytest.raises(ValueError):
        sanitize_operational_text("High clinical stress observed")

    with pytest.raises(ValueError):
        sanitize_operational_text("Personnel appears depressed")


def test_driver_ordering_and_sign_correctness():
    """Verify deterministic |impact| sorting and positive/negative direction assignment."""
    feature_names = [
        "duty_hours_30d",       # beta > 0, z > 0 -> positive impact
        "min_rest_hours_14d",   # beta < 0, z < 0 -> positive impact (deficit increases strain)
        "avg_rest_hours_30d",   # beta < 0, z > 0 -> negative impact (protective)
        "deployment_days_30d",  # beta > 0, z = 0 -> zero impact
    ]
    # Scaled values (z-scores)
    scaled_vals = np.array([2.0, -1.5, 1.0, 0.0])
    # Fitted coefficients
    coefs = np.array([0.5, -0.8, -0.4, 0.3])
    # Expected impacts:
    # duty_hours_30d:      2.0 * 0.5  = 1.0   (|1.0|)  -> RISK_INCREASING
    # min_rest_hours_14d:  -1.5 * -0.8 = 1.2  (|1.2|)  -> RISK_INCREASING (largest!)
    # avg_rest_hours_30d:   1.0 * -0.4 = -0.4 (|0.4|)  -> PROTECTIVE
    # deployment_days_30d: 0.0 * 0.3  = 0.0   (|0.0|)  -> NEUTRAL

    res = explain_operational_prediction(
        feature_names=feature_names,
        scaled_feature_values=scaled_vals,
        coefficients=coefs,
        top_k=3,
    )

    all_c = res["all_contributions"]
    assert len(all_c) == 4

    # Ordering check: |1.2| > |1.0| > |0.4| > |0.0|
    assert all_c[0]["feature"] == "min_rest_hours_14d"
    assert all_c[0]["impact"] == 1.2
    assert all_c[0]["direction"] == "RISK_INCREASING"

    assert all_c[1]["feature"] == "duty_hours_30d"
    assert all_c[1]["impact"] == 1.0
    assert all_c[1]["direction"] == "RISK_INCREASING"

    assert all_c[2]["feature"] == "avg_rest_hours_30d"
    assert all_c[2]["impact"] == -0.4
    assert all_c[2]["direction"] == "PROTECTIVE"

    assert all_c[3]["feature"] == "deployment_days_30d"
    assert all_c[3]["impact"] == 0.0
    assert all_c[3]["direction"] == "NEUTRAL"

    # Primary driver must be the strongest strain driver
    assert res["primary_driver"] == FACTOR_LABEL_MAP["min_rest_hours_14d"]
    assert len(res["top_drivers"]) == 2
    assert len(res["protective_factors"]) == 1


def test_explainability_reproducibility():
    """Verify exact reproducibility across repeated invocations."""
    fn = ["duty_hours_7d", "consecutive_duty_days", "staffing_ratio_7d"]
    z = np.array([1.234, 0.567, -0.891])
    b = np.array([0.45, 0.32, -0.60])

    run1 = explain_operational_prediction(fn, z, b)
    run2 = explain_operational_prediction(fn, z, b)

    assert run1 == run2
