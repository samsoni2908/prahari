import math
from typing import Any, Dict, List, Optional

# Version identifier
WSI_POLICY_VERSION = "WSI-POLICY-1.0"
WSI_VERSION = "1.0.0"

# Canonical locked weights (sum = 1.00)
WSI_WEIGHTS: Dict[str, float] = {
    "D": 0.25,
    "R": 0.20,
    "C": 0.15,
    "N": 0.15,
    "L": 0.10,
    "H": 0.10,
    "S": 0.05,
}

# Canonical reference benchmark
REFERENCE_INPUT: Dict[str, float] = {
    "D": 78.0,
    "R": 85.0,
    "C": 90.0,
    "N": 80.0,
    "L": 70.0,
    "H": 65.0,
    "S": 40.0,
}
REFERENCE_WSI: float = 77.50

# Severity band thresholds
SEVERITY_THRESHOLDS = {
    "CRITICAL": 85.0,
    "ELEVATED": 70.0,
    "MODERATE": 50.0,
}


def validate_component_value(name: str, value: Any) -> float:
    """
    Validates that a normalized WSI component is a finite float in [0.0, 100.0].
    Raises ValueError on invalid/negative/impossible/non-finite values.
    Silent clamping is strictly prohibited under PRAHARI truthful state rules.
    """
    if value is None:
        raise ValueError(f"WSI component '{name}' is missing (None).")
    try:
        val = float(value)
    except (TypeError, ValueError) as err:
        raise ValueError(f"WSI component '{name}' must be numeric, got {value!r}") from err

    if math.isnan(val) or math.isinf(val):
        raise ValueError(f"WSI component '{name}' is non-finite ({val}).")

    if val < 0.0 or val > 100.0:
        raise ValueError(
            f"WSI component '{name}' value {val} is outside valid normalized range [0.0, 100.0]. "
            f"Silent clamping is prohibited."
        )

    return val


def get_strain_severity(wsi_score: Optional[float]) -> Optional[str]:
    """Map WSI score to operational severity level."""
    if wsi_score is None:
        return None
    if wsi_score >= SEVERITY_THRESHOLDS["CRITICAL"]:
        return "CRITICAL"
    elif wsi_score >= SEVERITY_THRESHOLDS["ELEVATED"]:
        return "ELEVATED"
    elif wsi_score >= SEVERITY_THRESHOLDS["MODERATE"]:
        return "MODERATE"
    return "NORMAL"


get_wsi_category = get_strain_severity


def calculate_wsi(
    d: float,
    r: float,
    c: float,
    n: float,
    l: float,
    h: float,
    s: float,
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """
    Computes Workload Strain Index (WSI) normalized to 0-100:
    WSI = 0.25D + 0.20R + 0.15C + 0.15N + 0.10L + 0.10H + 0.05S

    All components must be valid normalized values in [0.0, 100.0].
    Raises ValueError if any input is missing, non-finite, or out of range.
    """
    w = weights or WSI_WEIGHTS

    d_val = validate_component_value("D", d)
    r_val = validate_component_value("R", r)
    c_val = validate_component_value("C", c)
    n_val = validate_component_value("N", n)
    l_val = validate_component_value("L", l)
    h_val = validate_component_value("H", h)
    s_val = validate_component_value("S", s)

    score = (
        w["D"] * d_val
        + w["R"] * r_val
        + w["C"] * c_val
        + w["N"] * n_val
        + w["L"] * l_val
        + w["H"] * h_val
        + w["S"] * s_val
    )
    return round(score, 2)


def compute_wsi_detailed(
    components: Optional[Dict[str, Optional[float]]] = None,
    *,
    d: Optional[float] = None,
    r: Optional[float] = None,
    c: Optional[float] = None,
    n: Optional[float] = None,
    l: Optional[float] = None,
    h: Optional[float] = None,
    s: Optional[float] = None,
    weights: Optional[Dict[str, float]] = None,
    component_reasons: Optional[Dict[str, str]] = None,
    policy_version: str = WSI_POLICY_VERSION,
) -> Dict[str, Any]:
    """
    Detailed, explainable, versioned WSI computation returning explicit status.

    Contract: docs/ml.md §8.1:
    - Precedence: COMPUTATION_ERROR > REST_DATA_MISSING > INSUFFICIENT_HISTORY > NOT_COMPUTED
    - Any unavailable component makes WSI score and contributions unavailable.
    - No redistribution of weights when a component is missing.
    - Unrounded score stored alongside rounded presentation score.
    - Component contributions = weight * component.
    """
    w = weights or WSI_WEIGHTS
    reasons_map = component_reasons or {}

    raw_inputs: Dict[str, Optional[float]] = {
        "D": d if d is not None else (components.get("D") if components else None),
        "R": r if r is not None else (components.get("R") if components else None),
        "C": c if c is not None else (components.get("C") if components else None),
        "N": n if n is not None else (components.get("N") if components else None),
        "L": l if l is not None else (components.get("L") if components else None),
        "H": h if h is not None else (components.get("H") if components else None),
        "S": s if s is not None else (components.get("S") if components else None),
    }

    component_details: Dict[str, Dict[str, Any]] = {}
    contributions: Dict[str, float] = {}
    computation_errors: List[str] = []
    missing_components: List[str] = []
    insufficient_history: List[str] = []
    rest_data_missing: bool = False

    validated_values: Dict[str, float] = {}

    for comp_name, weight in w.items():
        val = raw_inputs.get(comp_name)
        assigned_reason = reasons_map.get(comp_name)

        if val is None:
            missing_components.append(comp_name)
            if comp_name == "R" or assigned_reason == "REST_DATA_MISSING":
                rest_data_missing = True
                state_reason = "REST_DATA_MISSING"
            elif assigned_reason == "INSUFFICIENT_HISTORY":
                insufficient_history.append(comp_name)
                state_reason = "INSUFFICIENT_HISTORY"
            else:
                state_reason = assigned_reason or "NOT_COMPUTED"

            component_details[comp_name] = {
                "weight": weight,
                "value": None,
                "contribution": None,
                "input_state": "COMPONENT_INPUT_UNAVAILABLE",
                "reason": state_reason,
            }
        else:
            try:
                valid_val = validate_component_value(comp_name, val)
                validated_values[comp_name] = valid_val
                contrib = weight * valid_val
                contributions[comp_name] = round(contrib, 4)
                component_details[comp_name] = {
                    "weight": weight,
                    "value": valid_val,
                    "contribution": round(contrib, 4),
                    "input_state": "VALID",
                    "reason": None,
                }
            except ValueError as err:
                computation_errors.append(str(err))
                component_details[comp_name] = {
                    "weight": weight,
                    "value": val,
                    "contribution": None,
                    "input_state": "COMPONENT_INPUT_UNAVAILABLE",
                    "reason": "COMPUTATION_ERROR",
                }

    # Evaluate overall status per precedence:
    # COMPUTATION_ERROR > REST_DATA_MISSING > INSUFFICIENT_HISTORY > NOT_COMPUTED > VALID
    all_reasons: List[str] = []
    if computation_errors:
        status = "COMPUTATION_ERROR"
        all_reasons.extend(computation_errors)
    elif rest_data_missing:
        status = "REST_DATA_MISSING"
        all_reasons.append("Rest record data missing for component R")
    elif insufficient_history:
        status = "INSUFFICIENT_HISTORY"
        all_reasons.append(f"Insufficient history for components: {', '.join(insufficient_history)}")
    elif missing_components:
        status = "NOT_COMPUTED"
        all_reasons.append(f"Missing required components: {', '.join(missing_components)}")
    else:
        status = "VALID"

    if status == "VALID":
        unrounded_score = sum(w[c] * validated_values[c] for c in w)
        score = round(unrounded_score, 2)
        severity = get_strain_severity(score)
        return {
            "status": "VALID",
            "score": score,
            "unrounded_score": unrounded_score,
            "severity": severity,
            "contributions": contributions,
            "components": component_details,
            "reasons": [],
            "policy_version": policy_version,
            "wsi_version": WSI_VERSION,
        }
    else:
        return {
            "status": status,
            "score": None,
            "unrounded_score": None,
            "severity": None,
            "contributions": None,
            "components": component_details,
            "reasons": all_reasons,
            "policy_version": policy_version,
            "wsi_version": WSI_VERSION,
        }


# Convenient alias
compute_wsi = compute_wsi_detailed
