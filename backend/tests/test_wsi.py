import pytest
import numpy as np
from app.analytics.wsi import calculate_wsi, get_wsi_category
from app.analytics.baseline import calculate_robust_z_score, calculate_ewma


def test_wsi_reference_value():
    """
    CRITICAL PRAHARI REFERENCE TEST:
    D=78, R=85, C=90, N=80, L=70, H=65, S=40
    Formula: 0.25D + 0.20R + 0.15C + 0.15N + 0.10L + 0.10H + 0.05S
    Expected: 77.50
    """
    wsi = calculate_wsi(
        d=78.0,
        r=85.0,
        c=90.0,
        n=80.0,
        l=70.0,
        h=65.0,
        s=40.0,
    )
    assert wsi == 77.50, f"Expected 77.50, got {wsi}"
    assert get_wsi_category(wsi) == "ELEVATED"


def test_wsi_bounds():
    """Test boundary conditions for WSI calculation."""
    min_wsi = calculate_wsi(0, 0, 0, 0, 0, 0, 0)
    assert min_wsi == 0.0
    assert get_wsi_category(min_wsi) == "NORMAL"

    max_wsi = calculate_wsi(100, 100, 100, 100, 100, 100, 100)
    assert max_wsi == 100.0
    assert get_wsi_category(max_wsi) == "CRITICAL"


def test_wsi_weights_exact_values_and_sum():
    """Test that canonical WSI weights match locked contract and sum to exactly 1.0."""
    from app.analytics.wsi import WSI_WEIGHTS
    assert WSI_WEIGHTS["D"] == 0.25
    assert WSI_WEIGHTS["R"] == 0.20
    assert WSI_WEIGHTS["C"] == 0.15
    assert WSI_WEIGHTS["N"] == 0.15
    assert WSI_WEIGHTS["L"] == 0.10
    assert WSI_WEIGHTS["H"] == 0.10
    assert WSI_WEIGHTS["S"] == 0.05
    assert round(sum(WSI_WEIGHTS.values()), 6) == 1.0


def test_wsi_explainability_and_contributions():
    """Test detailed WSI computation returns valid contributions matching weights."""
    from app.analytics.wsi import compute_wsi_detailed
    res = compute_wsi_detailed(
        d=78.0, r=85.0, c=90.0, n=80.0, l=70.0, h=65.0, s=40.0
    )
    assert res["status"] == "VALID"
    assert res["score"] == 77.50
    assert res["unrounded_score"] == 77.50
    assert res["severity"] == "ELEVATED"
    assert res["policy_version"] == "WSI-POLICY-1.0"

    # Contributions = weight * value
    contribs = res["contributions"]
    assert contribs["D"] == round(0.25 * 78.0, 4)  # 19.5
    assert contribs["R"] == round(0.20 * 85.0, 4)  # 17.0
    assert contribs["C"] == round(0.15 * 90.0, 4)  # 13.5
    assert contribs["N"] == round(0.15 * 80.0, 4)  # 12.0
    assert contribs["L"] == round(0.10 * 70.0, 4)  # 7.0
    assert contribs["H"] == round(0.10 * 65.0, 4)  # 6.5
    assert contribs["S"] == round(0.05 * 40.0, 4)  # 2.0
    assert sum(contribs.values()) == 77.50


def test_wsi_invalid_inputs_rejected_no_silent_clamping():
    """Verify that negative, out-of-range, NaN, and non-finite inputs are strictly rejected."""
    from app.analytics.wsi import compute_wsi_detailed
    # 1. Negative input raises ValueError in calculate_wsi
    with pytest.raises(ValueError, match="outside valid normalized range"):
        calculate_wsi(d=-10.0, r=50, c=50, n=50, l=50, h=50, s=50)

    # 2. Exceeding 100 raises ValueError
    with pytest.raises(ValueError, match="outside valid normalized range"):
        calculate_wsi(d=50, r=150.0, c=50, n=50, l=50, h=50, s=50)

    # 3. NaN raises ValueError
    with pytest.raises(ValueError, match="non-finite"):
        calculate_wsi(d=float("nan"), r=50, c=50, n=50, l=50, h=50, s=50)

    # 4. Inf raises ValueError
    with pytest.raises(ValueError, match="non-finite"):
        calculate_wsi(d=50, r=float("inf"), c=50, n=50, l=50, h=50, s=50)

    # 5. Non-numeric raises ValueError
    with pytest.raises(ValueError, match="must be numeric"):
        calculate_wsi(d="invalid", r=50, c=50, n=50, l=50, h=50, s=50)

    # 6. compute_wsi_detailed captures COMPUTATION_ERROR gracefully
    detailed_res = compute_wsi_detailed(
        d=-5.0, r=50, c=50, n=50, l=50, h=50, s=50
    )
    assert detailed_res["status"] == "COMPUTATION_ERROR"
    assert detailed_res["score"] is None
    assert detailed_res["contributions"] is None
    assert len(detailed_res["reasons"]) > 0


def test_wsi_missing_inputs_truthful_unavailability():
    """Verify missing inputs produce truthful unavailable status without weight redistribution."""
    from app.analytics.wsi import compute_wsi_detailed

    # 1. calculate_wsi raises when component is None
    with pytest.raises(ValueError, match="is missing"):
        calculate_wsi(d=None, r=50, c=50, n=50, l=50, h=50, s=50)

    # 2. Missing R returns REST_DATA_MISSING
    res_r_missing = compute_wsi_detailed(
        d=50, r=None, c=50, n=50, l=50, h=50, s=50
    )
    assert res_r_missing["status"] == "REST_DATA_MISSING"
    assert res_r_missing["score"] is None
    assert res_r_missing["contributions"] is None

    # 3. Insufficient history component returns INSUFFICIENT_HISTORY
    res_hist_missing = compute_wsi_detailed(
        d=50, r=50, c=None, n=50, l=50, h=50, s=50,
        component_reasons={"C": "INSUFFICIENT_HISTORY"}
    )
    assert res_hist_missing["status"] == "INSUFFICIENT_HISTORY"
    assert res_hist_missing["score"] is None

    # 4. Generic missing returns NOT_COMPUTED
    res_generic_missing = compute_wsi_detailed(
        d=50, r=50, c=50, n=None, l=50, h=50, s=50
    )
    assert res_generic_missing["status"] == "NOT_COMPUTED"
    assert res_generic_missing["score"] is None


def test_wsi_reproducibility():
    """Verify that identical inputs produce bit-for-bit identical outputs across 1000 executions."""
    scores = [
        calculate_wsi(d=78.0, r=85.0, c=90.0, n=80.0, l=70.0, h=65.0, s=40.0)
        for _ in range(1000)
    ]
    assert all(s == 77.50 for s in scores)
    assert len(set(scores)) == 1



def test_baseline_robust_z_score():
    """Test Median/MAD robust z-score calculation."""
    from app.analytics.baseline import calculate_median_mad
    history = [50.0, 52.0, 48.0, 51.0, 49.0, 50.0]
    med, mad = calculate_median_mad(history)
    assert med is not None and mad is not None
    z = calculate_robust_z_score(current_val=85.0, median=med, mad=mad)
    assert z is not None
    assert z > 2.0  # Significant deviation above median


def test_baseline_ewma():
    """Test EWMA calculation."""
    values = [40.0, 45.0, 50.0, 60.0]
    ewma = calculate_ewma(values, alpha=0.3)
    assert ewma is not None
    assert 40.0 <= ewma <= 60.0
