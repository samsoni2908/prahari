"""PRAHARI Operational Risk Score & Attention Band Mapping Module.

Task 22 Contract:
Pipeline:
    features
    → classifier
    → calibrated probability (p in [0.0, 1.0])
    → 0–100 operational score (continuous)
    → safety floors (deterministic, outside ML)
    → trend (temporal direction)
    → band (LOW = 0–39, MEDIUM = 40–69, HIGH = 70–100)

Strict Governance Rules:
1. Operational Terminology Only:
   - "Operational strain score" / "Operational attention band".
   - Strictly NO clinical or mental health risk labeling ("clinical risk", "mental health risk" prohibited).
2. Monotonic Piecewise Linear Mapping:
   - Approved operational alert threshold tau_high = 0.15 maps exactly to score 70.0 (entry to HIGH band).
   - Midpoint operational threshold tau_med = 0.075 maps to score 40.0 (entry to MEDIUM band).
   - Low strain: p in [0.0, 0.075) -> score in [0.0, 40.0) -> LOW (0–39).
   - Moderate strain: p in [0.075, 0.15) -> score in [40.0, 70.0) -> MEDIUM (40–69).
   - Elevated strain / Alert: p in [0.15, 1.0] -> score in [70.0, 100.0] -> HIGH (70–100).
3. Truthful State Rule:
   - Missing / invalid / non-finite inputs return (None, "NOT_COMPUTED" / "INVALID_INPUT").
   - NEVER fabricate a healthy numeric score (e.g. 0.0 or 20.0) when probability is unavailable.
"""

from typing import Any, Dict, List, Optional, Tuple
import math
import numpy as np

# Canonical Band Definitions
BAND_LOW = "LOW"        # 0–39
BAND_MEDIUM = "MEDIUM"  # 40–69
BAND_HIGH = "HIGH"      # 70–100
BAND_NOT_COMPUTED = "NOT_COMPUTED"

SCORE_MIN = 0.0
SCORE_MEDIUM_THRESHOLD = 40.0
SCORE_HIGH_THRESHOLD = 70.0
SCORE_MAX = 100.0

# User-Approved Operational Decision Threshold (Option 2 - Balanced Operational Threshold)
DEFAULT_TAU_HIGH = 0.15
DEFAULT_TAU_MED = 0.075


def map_probability_to_operational_score(
    p: Optional[float],
    tau_high: float = DEFAULT_TAU_HIGH,
    tau_med: float = DEFAULT_TAU_MED,
) -> Tuple[Optional[float], str]:
    """
    Monotonically maps calibrated probability p in [0.0, 1.0] to continuous 0–100 operational score.

    Mapping properties:
    - p = 0.0       -> score = 0.0
    - p = tau_med   (0.075) -> score = 40.0 (LOW / MEDIUM boundary)
    - p = tau_high  (0.150) -> score = 70.0 (MEDIUM / HIGH alert boundary)
    - p = 1.0       -> score = 100.0

    Returns:
        (operational_score, status)
    """
    if p is None:
        return None, "NOT_COMPUTED"

    try:
        p_val = float(p)
    except (TypeError, ValueError):
        return None, "INVALID_INPUT"

    if math.isnan(p_val) or math.isinf(p_val):
        return None, "INVALID_INPUT"

    if p_val < 0.0 or p_val > 1.0:
        return None, "OUT_OF_BOUNDS"

    if not (0.0 < tau_med < tau_high < 1.0):
        raise ValueError(f"Invalid thresholds: require 0 < tau_med ({tau_med}) < tau_high ({tau_high}) < 1.0")

    # Piecewise linear monotonic scaling
    if p_val <= 0.0:
        score = 0.0
    elif p_val < tau_med:
        # Region 1: [0.0, tau_med) -> [0.0, 40.0)
        score = (p_val / tau_med) * SCORE_MEDIUM_THRESHOLD
    elif p_val < tau_high:
        # Region 2: [tau_med, tau_high) -> [40.0, 70.0)
        fraction = (p_val - tau_med) / (tau_high - tau_med)
        score = SCORE_MEDIUM_THRESHOLD + fraction * (SCORE_HIGH_THRESHOLD - SCORE_MEDIUM_THRESHOLD)
    else:
        # Region 3: [tau_high, 1.0] -> [70.0, 100.0]
        fraction = (p_val - tau_high) / (1.0 - tau_high)
        score = SCORE_HIGH_THRESHOLD + fraction * (SCORE_MAX - SCORE_HIGH_THRESHOLD)

    # Clamp safely to [0.0, 100.0]
    score = max(SCORE_MIN, min(SCORE_MAX, score))
    return round(score, 2), "VALID"


def determine_operational_band(score: Optional[float]) -> str:
    """
    Assigns canonical operational attention band based on 0–100 score:
    - LOW: [0.0, 40.0) (displayed as 0–39)
    - MEDIUM: [40.0, 70.0) (displayed as 40–69)
    - HIGH: [70.0, 100.0] (displayed as 70–100)
    - NOT_COMPUTED: if score is None or invalid
    """
    if score is None:
        return BAND_NOT_COMPUTED

    try:
        s = float(score)
    except (TypeError, ValueError):
        return BAND_NOT_COMPUTED

    if math.isnan(s) or math.isinf(s):
        return BAND_NOT_COMPUTED

    if s < SCORE_MEDIUM_THRESHOLD:
        return BAND_LOW
    elif s < SCORE_HIGH_THRESHOLD:
        return BAND_MEDIUM
    else:
        return BAND_HIGH


def assess_operational_trend(
    current_score: Optional[float],
    prior_scores: Optional[List[float]] = None,
    tolerance: float = 2.0,
) -> str:
    """
    Calculates operational workload/strain trend direction from prior sequence.

    Returns:
    - 'RISING': delta > tolerance
    - 'FALLING': delta < -tolerance
    - 'STABLE': |delta| <= tolerance
    - 'INSUFFICIENT_HISTORY': fewer than 2 valid observations
    """
    if current_score is None:
        return "NOT_COMPUTED"

    if not prior_scores or len(prior_scores) == 0:
        return "INSUFFICIENT_HISTORY"

    valid_priors = [s for s in prior_scores if s is not None and not math.isnan(s) and not math.isinf(s)]
    if len(valid_priors) == 0:
        return "INSUFFICIENT_HISTORY"

    prev_score = valid_priors[-1]
    delta = current_score - prev_score

    if delta > tolerance:
        return "RISING"
    elif delta < -tolerance:
        return "FALLING"
    else:
        return "STABLE"


def execute_operational_pipeline(
    calibrated_prob: Optional[float],
    prior_scores: Optional[List[float]] = None,
    tau_high: float = DEFAULT_TAU_HIGH,
    tau_med: float = DEFAULT_TAU_MED,
    safety_floor_override_score: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Executes the full Task 22 operational pipeline:
    features → classifier → calibrated probability → 0–100 operational score → safety floors → trend → band.

    Returns dictionary with truthful operational fields.
    """
    # Step 1: Probability to raw operational score
    raw_score, score_status = map_probability_to_operational_score(
        calibrated_prob, tau_high=tau_high, tau_med=tau_med
    )

    if score_status != "VALID" or raw_score is None:
        return {
            "calibrated_probability": calibrated_prob,
            "raw_operational_score": None,
            "final_operational_score": None,
            "operational_band": BAND_NOT_COMPUTED,
            "operational_trend": "NOT_COMPUTED",
            "safety_floors_status": "SAFETY_FLOORS_NOT_FINALIZED",
            "safety_floors_applied": False,
            "status": score_status,
        }

    # Step 2: Safety Floors (Deterministic, outside ML)
    # If a finalized safety floor rule applies, ML can elevate but never lower the floor
    final_score = raw_score
    floor_applied = False
    floors_status = "SAFETY_FLOORS_NOT_FINALIZED"

    if safety_floor_override_score is not None:
        floors_status = "SAFETY_FLOOR_ACTIVE"
        if safety_floor_override_score > final_score:
            final_score = round(float(safety_floor_override_score), 2)
            floor_applied = True

    # Step 3: Trend
    trend = assess_operational_trend(final_score, prior_scores=prior_scores)

    # Step 4: Band assignment
    band = determine_operational_band(final_score)

    return {
        "calibrated_probability": round(float(calibrated_prob), 4) if calibrated_prob is not None else None,
        "raw_operational_score": raw_score,
        "final_operational_score": final_score,
        "operational_band": band,
        "operational_trend": trend,
        "safety_floors_status": floors_status,
        "safety_floors_applied": floor_applied,
        "status": "VALID",
    }
