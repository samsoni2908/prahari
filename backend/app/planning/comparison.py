"""Schedule Comparison Engine for Current vs Proposed Scenarios.

Computes truthful differences across schedule-based metrics:
- duty hours distribution
- night duty distribution
- consecutive duty streaks
- inter-duty rest opportunities
- assignment disruption (moves, swaps, affected personnel)
- projected WSI: explicitly NULL with PROJECTION_NOT_COMPUTED
"""

from typing import Any, Dict, List, Optional, Set
import uuid


def compute_scenario_comparison(
    before_metrics: Dict[str, Any],
    after_metrics: Dict[str, Any],
    changes: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute detailed comparative analysis between current and proposed plans."""
    affected_pids: Set[str] = set()
    for c in changes:
        if c.get("pseudo_id"):
            affected_pids.add(c["pseudo_id"])
        elif c.get("personnel_id"):
            affected_pids.add(str(c["personnel_id"])[:8])

    def calc_delta(key: str, round_digits: int = 2) -> Optional[float]:
        b = before_metrics.get(key)
        a = after_metrics.get(key)
        if b is not None and a is not None:
            return round(float(a) - float(b), round_digits)
        return None

    return {
        "workload": {
            "total_duty_hours": {
                "current": before_metrics.get("total_duty_hours"),
                "proposed": after_metrics.get("total_duty_hours"),
                "difference": calc_delta("total_duty_hours"),
                "unit": "hours",
            },
            "avg_duty_hours_per_person": {
                "current": before_metrics.get("avg_duty_hours_per_person"),
                "proposed": after_metrics.get("avg_duty_hours_per_person"),
                "difference": calc_delta("avg_duty_hours_per_person"),
                "unit": "hours",
            },
            "max_duty_hours_per_person": {
                "current": before_metrics.get("max_duty_hours_per_person"),
                "proposed": after_metrics.get("max_duty_hours_per_person"),
                "difference": calc_delta("max_duty_hours_per_person"),
                "unit": "hours",
            },
        },
        "night_duty": {
            "total_night_duties": {
                "current": before_metrics.get("total_night_duties"),
                "proposed": after_metrics.get("total_night_duties"),
                "difference": calc_delta("total_night_duties", 0),
                "unit": "shifts",
            },
            "max_night_duties_per_person": {
                "current": before_metrics.get("max_night_duties_per_person"),
                "proposed": after_metrics.get("max_night_duties_per_person"),
                "difference": calc_delta("max_night_duties_per_person", 0),
                "unit": "shifts",
            },
            "night_duty_variance": {
                "current": before_metrics.get("night_duty_variance"),
                "proposed": after_metrics.get("night_duty_variance"),
                "difference": calc_delta("night_duty_variance", 4),
                "unit": "variance",
            },
        },
        "recovery": {
            "min_rest_gap_hours": {
                "current": before_metrics.get("min_rest_gap_hours"),
                "proposed": after_metrics.get("min_rest_gap_hours"),
                "difference": calc_delta("min_rest_gap_hours"),
                "unit": "hours",
            },
            "short_rest_gaps_count": {
                "current": before_metrics.get("short_rest_gaps_count"),
                "proposed": after_metrics.get("short_rest_gaps_count"),
                "difference": calc_delta("short_rest_gaps_count", 0),
                "unit": "count",
            },
            "quick_returns_count": {
                "current": before_metrics.get("quick_returns_count"),
                "proposed": after_metrics.get("quick_returns_count"),
                "difference": calc_delta("quick_returns_count", 0),
                "unit": "count",
            },
            "max_consecutive_days": {
                "current": before_metrics.get("max_consecutive_days"),
                "proposed": after_metrics.get("max_consecutive_days"),
                "difference": calc_delta("max_consecutive_days", 0),
                "unit": "days",
            },
        },
        "disruption": {
            "moved_assignments_count": len(changes),
            "affected_personnel_count": len(affected_pids),
            "affected_personnel_pseudonyms": sorted(list(affected_pids)),
        },
        "wsi": {
            "projected_wsi": None,
            "projected_wsi_status": "PROJECTION_NOT_COMPUTED",
            "reason": "Complete 7-factor WSI projection rules are not active for what-if scenarios",
        },
    }
