"""
PRAHARI — Operational Alert-Budget & Threshold Analysis Engine (Task 21)
Canonical Reference: AGENTS.md §8, rules.md, docs/ml.md §6.7

Evaluates the threshold curve for Model-A decision support:
- Evaluates trade-offs between precision, recall, F1, and unit operational workload (alerts per 100 personnel).
- Avoids arbitrary default threshold (0.50 collapses recall to ~8%).
- Provides transparent empirical data for human command/policy selection.
"""

from typing import Any, Dict, List, Optional, Sequence
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score


CANDIDATE_THRESHOLDS: List[float] = [
    0.05, 0.08, 0.10, 0.12, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50
]


def compute_threshold_curve(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    thresholds: Optional[Sequence[float]] = None,
    n_personnel: int = 300,
    n_weeks: int = 7,
) -> List[Dict[str, Any]]:
    """Evaluates classification performance and alert volume across candidate decision thresholds.

    Args:
        y_true: Binary ground truth array {0, 1}.
        y_prob: Predicted calibrated probability array [0.0, 1.0].
        thresholds: List of candidate decision thresholds.
        n_personnel: Unique personnel count in evaluation cohort.
        n_weeks: Observational period length in weeks.

    Returns:
        List of dictionaries detailing metrics and operational alert volume per threshold.
    """
    y_true_arr = np.asarray(y_true, dtype=int)
    y_prob_arr = np.asarray(y_prob, dtype=float)

    if thresholds is None:
        thresholds = CANDIDATE_THRESHOLDS

    curve_data: List[Dict[str, Any]] = []

    for tau in thresholds:
        preds = (y_prob_arr >= tau).astype(int)
        n_alerts = int(preds.sum())
        tp = int(((preds == 1) & (y_true_arr == 1)).sum())
        fp = int(((preds == 1) & (y_true_arr == 0)).sum())
        fn = int(((preds == 0) & (y_true_arr == 1)).sum())
        tn = int(((preds == 0) & (y_true_arr == 0)).sum())

        prec = float(precision_score(y_true_arr, preds, zero_division=0))
        rec = float(recall_score(y_true_arr, preds, zero_division=0))
        f1 = float(f1_score(y_true_arr, preds, zero_division=0))

        # Alert budget metrics
        total_eval_person_weeks = max(1, n_personnel * n_weeks)
        alerts_per_100_per_week = (n_alerts / total_eval_person_weeks) * 100.0

        curve_data.append({
            "threshold": round(float(tau), 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "total_alerts": n_alerts,
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "true_negatives": tn,
            "alerts_per_100_personnel_per_week": round(float(alerts_per_100_per_week), 2),
        })

    return curve_data


__all__ = ["CANDIDATE_THRESHOLDS", "compute_threshold_curve"]
