"""PRAHARI Operational Explainability Module.

Task 24 Contract:
- Logistic regression direct contribution explanation: impact_j = z_j * beta_j.
- Operational drivers only (higher-than-personal-baseline duty load, reduced recovery opportunity,
  higher night-duty burden, staffing pressure, peer deviation, etc.).
- Strictly NO clinical or psychiatric words (no "depressed", "mentally unstable", "clinical stress", etc.).
- Driver ordering: deterministic sorting by |impact| descending.
- Sign correctness: positive impact increases operational strain signal; negative impact is protective.
"""

from typing import Any, Dict, List, Optional
import numpy as np

from app.ml.terminology import BANNED_PHRASES

# 15 Canonical Model-A Operational Features Mapping
FACTOR_LABEL_MAP: Dict[str, str] = {
    "duty_hours_7d": "High short-term duty burden (7-day duty load)",
    "duty_hours_30d": "Elevated cumulative duty load (30-day duty hours)",
    "night_duty_count_14d": "Concentrated night-shift assignments (14-day night duties)",
    "night_duty_ratio_30d": "High night-duty concentration (30-day night-shift ratio)",
    "consecutive_duty_days": "Prolonged consecutive duty stretch without rest days",
    "min_rest_hours_14d": "Rest gap deficit / acute short recovery interval",
    "avg_rest_hours_30d": "Reduced daily recovery opportunity (30-day average rest hours)",
    "quick_return_count_30d": "Frequent quick returns with short turnaround between shifts",
    "deployment_days_30d": "High field deployment intensity (30-day operational deployment)",
    "training_days_30d": "Intensive field training duty (30-day training days)",
    "staffing_ratio_7d": "Unit understaffing / elevated operational staffing pressure",
    "workload_change_14v14": "Workload acceleration (recent 14d vs prior 14d load surge)",
    "ewma_workload": "Rising exponential workload trend",
    "baseline_z_workload": "Workload elevated significantly above personal historical baseline",
    "peer_deviation_workload": "Workload substantially higher than unit peer cohort",
}

FACTOR_CATEGORY_MAP: Dict[str, str] = {
    "duty_hours_7d": "Duty Load",
    "duty_hours_30d": "Duty Load",
    "night_duty_count_14d": "Shift Pattern",
    "night_duty_ratio_30d": "Shift Pattern",
    "consecutive_duty_days": "Fatigue & Continuity",
    "min_rest_hours_14d": "Recovery & Rest",
    "avg_rest_hours_30d": "Recovery & Rest",
    "quick_return_count_30d": "Recovery & Rest",
    "deployment_days_30d": "Operational Deployment",
    "training_days_30d": "Operational Deployment",
    "staffing_ratio_7d": "Staffing Context",
    "workload_change_14v14": "Workload Dynamics",
    "ewma_workload": "Trend & History",
    "baseline_z_workload": "Personal Baseline",
    "peer_deviation_workload": "Peer Comparison",
}


def sanitize_operational_text(text: str) -> str:
    """Verifies that no banned clinical or diagnostic phrase appears in generated explanation text."""
    t_lower = text.lower()
    for phrase in BANNED_PHRASES:
        if phrase.lower() in t_lower:
            raise ValueError(f"Prohibited non-operational phrase detected: '{phrase}' in text: {text}")
    return text


def explain_operational_prediction(
    feature_names: List[str],
    scaled_feature_values: np.ndarray,
    coefficients: np.ndarray,
    raw_feature_values: Optional[Dict[str, Any]] = None,
    top_k: int = 5,
) -> Dict[str, Any]:
    """
    Computes deterministic logistic regression directional factor contributions:
        impact_j = z_j * beta_j

    Returns:
    - primary_driver: string description of strongest strain-increasing factor
    - top_drivers: list of top strain-increasing factors (impact > 0)
    - protective_factors: list of top strain-reducing factors (impact < 0)
    - all_contributions: complete list sorted by |impact| descending
    """
    if len(scaled_feature_values) != len(coefficients):
        raise ValueError(
            f"Dimension mismatch: {len(scaled_feature_values)} features vs {len(coefficients)} coefficients"
        )

    all_contributions: List[Dict[str, Any]] = []

    for idx, (fn, z_val, beta) in enumerate(zip(feature_names, scaled_feature_values, coefficients)):
        impact = float(z_val * beta)
        label = FACTOR_LABEL_MAP.get(fn, fn.replace("_", " ").title())
        category = FACTOR_CATEGORY_MAP.get(fn, "Operational Context")

        # Verify no banned clinical words
        sanitize_operational_text(label)
        sanitize_operational_text(category)

        raw_val = None
        if raw_feature_values is not None:
            raw_val = raw_feature_values.get(fn)

        direction = "NEUTRAL"
        if impact > 1e-4:
            direction = "RISK_INCREASING"
        elif impact < -1e-4:
            direction = "PROTECTIVE"

        all_contributions.append({
            "feature": fn,
            "label": label,
            "category": category,
            "scaled_value": round(float(z_val), 4),
            "raw_value": round(float(raw_val), 2) if isinstance(raw_val, (int, float)) else raw_val,
            "coefficient": round(float(beta), 4),
            "impact": round(impact, 4),
            "abs_impact": round(abs(impact), 4),
            "direction": direction,
        })

    # Sort strictly deterministically by |impact| descending
    all_contributions.sort(key=lambda x: (x["abs_impact"], abs(x["coefficient"])), reverse=True)

    strain_drivers = [c for c in all_contributions if c["direction"] == "RISK_INCREASING"]
    protective_drivers = [c for c in all_contributions if c["direction"] == "PROTECTIVE"]

    primary_driver = (
        strain_drivers[0]["label"]
        if strain_drivers
        else "Operational workload within historical tolerance"
    )

    return {
        "primary_driver": primary_driver,
        "top_drivers": strain_drivers[:top_k],
        "protective_factors": protective_drivers[:top_k],
        "all_contributions": all_contributions,
    }


# Backwards compatibility helper
def explain_prediction(feature_dict: Dict[str, float], weights: Dict[str, float]) -> List[Dict[str, Any]]:
    """Legacy helper preserving existing interface for any historical consumer."""
    contributions = []
    for k, v in feature_dict.items():
        w = weights.get(k, 1.0)
        contributions.append({"factor": k, "impact": float(v * w)})
    return sorted(contributions, key=lambda x: abs(x["impact"]), reverse=True)
