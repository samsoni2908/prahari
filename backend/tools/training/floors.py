"""PRAHARI Safety Floors Module.

Task 23 & Consistency Audit Contract:
Safety floors are deterministic and OUTSIDE ML.
Rules:
1. No Approved Safety Floors:
   - Hidden "clinical safety floors" (e.g. PHQ >= threshold -> Operational HIGH) are STRICTLY PROHIBITED (docs/ml.md §29).
   - Operational safety floor overrides have not been approved in canonical policy.
   - Status: NO_APPROVED_SAFETY_FLOORS. Mode: PASS_THROUGH.
2. Model-A operational strain score and attention band are driven purely by calibrated
   operational probability and approved threshold tau=0.15; hard workload/duty constraints
   remain handled separately by the roster balance engine.
"""

from typing import Any, Dict, List, Optional, Tuple

SAFETY_FLOORS_STATUS = "NO_APPROVED_SAFETY_FLOORS"
SAFETY_FLOORS_MODE = "PASS_THROUGH"

# Backward compatibility alias
SAFETY_FLOORS_NOT_FINALIZED = "NO_APPROVED_SAFETY_FLOORS"


def get_safety_floors_status() -> str:
    """Returns the governance status of deterministic safety floors."""
    return SAFETY_FLOORS_STATUS


def apply_operational_safety_floors(
    operational_score: Optional[float],
    context: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[float], List[str], Dict[str, Any]]:
    """
    Pass-through handler for operational safety floors outside ML.

    Returns the score unmodified with explicit PASS_THROUGH status.
    """
    if operational_score is None:
        return None, [], {"status": SAFETY_FLOORS_STATUS, "mode": SAFETY_FLOORS_MODE, "override_applied": False}

    return (
        operational_score,
        [],
        {
            "status": SAFETY_FLOORS_STATUS,
            "mode": SAFETY_FLOORS_MODE,
            "override_applied": False,
            "reason": "PASS_THROUGH mode active: No approved deterministic safety floors outside ML",
        },
    )


def compute_confidence_score(
    data_completeness: float,
    model_availability_factor: float,
    calibration_reliability_factor: float,
) -> Tuple[float, Dict[str, float]]:
    """
    Computes data quality / model confidence score.
    Confidence = data_completeness * model_availability * calibration_reliability.
    """
    c = float(data_completeness) * float(model_availability_factor) * float(calibration_reliability_factor)
    score = round(max(0.0, min(1.0, c)), 2)
    breakdown = {
        "data_completeness": round(float(data_completeness), 2),
        "model_availability_factor": round(float(model_availability_factor), 2),
        "calibration_reliability_factor": round(float(calibration_reliability_factor), 2),
    }
    return score, breakdown
