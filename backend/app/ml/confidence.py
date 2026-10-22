"""PRAHARI Operational Confidence & Epistemological Reliability Module.

Task 25 Contract:
Confidence is NOT prediction probability.
Confidence reflects:
    data_completeness * model_availability * calibration_reliability

Transparent Components:
1. data_completeness in [0.0, 1.0]: fraction of required operational inputs validly observed.
2. model_availability in {0.0, 1.0}: 1.0 if approved artifact loaded & verified, else 0.0.
3. calibration_reliability in [0.0, 1.0]: empirical reliability based on validation calibration.

If artifact unavailable:
    model_availability = 0.0 -> confidence = 0.0 (Status: MODEL_UNAVAILABLE).
"""

from typing import Any, Dict, List, Optional, Tuple
import math

# Categorical Confidence Descriptors
CONFIDENCE_HIGH = "HIGH"          # >= 0.80
CONFIDENCE_MODERATE = "MODERATE"  # 0.50 - 0.79
CONFIDENCE_LOW = "LOW"            # 0.01 - 0.49
CONFIDENCE_UNAVAILABLE = "UNAVAILABLE"  # 0.0 or artifact missing


def compute_operational_confidence(
    data_completeness: float,
    model_availability: float,
    calibration_reliability: float,
) -> Tuple[float, str, Dict[str, Any]]:
    """
    Computes transparent 3-factor confidence score:
        Confidence = data_completeness * model_availability * calibration_reliability

    Returns:
        (confidence_score, confidence_descriptor, breakdown_dict)
    """
    try:
        dc = float(data_completeness)
        ma = float(model_availability)
        cr = float(calibration_reliability)
    except (TypeError, ValueError):
        return 0.0, CONFIDENCE_UNAVAILABLE, {
            "data_completeness": 0.0,
            "model_availability": 0.0,
            "calibration_reliability": 0.0,
            "rationale": "Invalid or non-numeric confidence inputs",
            "status": "COMPUTATION_ERROR",
        }

    # Clamp individual components to valid ranges
    dc = max(0.0, min(1.0, dc))
    ma = max(0.0, min(1.0, ma))
    cr = max(0.0, min(1.0, cr))

    if ma == 0.0:
        return 0.0, CONFIDENCE_UNAVAILABLE, {
            "data_completeness": round(dc, 4),
            "model_availability": 0.0,
            "calibration_reliability": round(cr, 4),
            "rationale": "Approved Model-A artifact is unavailable or unverified",
            "status": "MODEL_UNAVAILABLE",
        }

    score = dc * ma * cr
    score = round(max(0.0, min(1.0, score)), 4)

    # Assign descriptor
    if score >= 0.80:
        descriptor = CONFIDENCE_HIGH
        rationale = "High data completeness and validated calibration"
    elif score >= 0.50:
        descriptor = CONFIDENCE_MODERATE
        rationale = "Moderate confidence; some operational inputs imputed or historical window partial"
    elif score > 0.0:
        descriptor = CONFIDENCE_LOW
        rationale = "Low confidence due to substantial missing inputs or low calibration stability"
    else:
        descriptor = CONFIDENCE_UNAVAILABLE
        rationale = "Confidence unavailable"

    breakdown = {
        "data_completeness": round(dc, 4),
        "model_availability": round(ma, 4),
        "calibration_reliability": round(cr, 4),
        "rationale": rationale,
        "status": "VALID",
    }
    return score, descriptor, breakdown


def calculate_feature_completeness(
    feature_dict: Dict[str, Any],
    expected_features: List[str],
) -> float:
    """Calculates the proportion of expected features with valid, non-null, finite values."""
    if not expected_features:
        return 0.0

    valid_count = 0
    for fn in expected_features:
        val = feature_dict.get(fn)
        if val is not None:
            try:
                v_flt = float(val)
                if not (math.isnan(v_flt) or math.isinf(v_flt)):
                    valid_count += 1
            except (TypeError, ValueError):
                pass

    return round(valid_count / len(expected_features), 4)
