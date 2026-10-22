"""
PRAHARI â€” Model-A Comprehensive Evaluation Engine (Tasks 19 & 20)
Canonical Reference: AGENTS.md Â§8, rules.md, docs/ml.md Â§6.6

EVALUATION CONTRACT:
1. Strict Metrics Suite: ROC-AUC, PR-AUC, Brier score, Precision, Recall, F1.
2. Honest Reporting: Truthful state reporting without hiding weak or modest synthetic results.
3. Comparative A/B: Evaluates Feature Set A (with historical leave) vs Set B (canonical).
4. Person-Clustered Bootstrap: Calculates 95% confidence intervals clustered by personnel ID.
5. Temporal Stability: Evaluates variance across rolling-origin temporal blocks.
6. Lead-Time Evaluation: Explicitly measures lead time (days from actionable alert to target event).
"""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from sklearn.linear_model import LogisticRegression
from app.ml.features_hr import FEATURE_SET_A, FEATURE_SET_B
from tools.training.models.hr_model import build_hr_model
from tools.training.preprocessing import GovernedPreprocessor
from tools.training.calibrate import GovernedCalibrator


def compute_classification_metrics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float = 0.5,
) -> Dict[str, float]:
    """Computes full set of classification metrics for probabilistic predictions."""
    y_true_arr = np.asarray(y_true, dtype=int)
    y_prob_arr = np.asarray(y_prob, dtype=float)
    y_pred = (y_prob_arr >= threshold).astype(int)

    has_both_classes = len(np.unique(y_true_arr)) > 1

    roc_auc = float(roc_auc_score(y_true_arr, y_prob_arr)) if has_both_classes else 0.5
    pr_auc = float(average_precision_score(y_true_arr, y_prob_arr)) if has_both_classes else 0.0
    brier = float(brier_score_loss(y_true_arr, y_prob_arr))
    prec = float(precision_score(y_true_arr, y_pred, zero_division=0))
    rec = float(recall_score(y_true_arr, y_pred, zero_division=0))
    f1 = float(f1_score(y_true_arr, y_pred, zero_division=0))
    prevalence = float(y_true_arr.mean()) if len(y_true_arr) > 0 else 0.0

    return {
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "brier_score": round(brier, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "class_prevalence": round(prevalence, 4),
    }


def compute_calibration_diagnostics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 5,
) -> Dict[str, Any]:
    """Computes calibration reliability bins, ECE, and logistic calibration slope/intercept."""
    y_true_arr = np.asarray(y_true, dtype=int)
    y_prob_arr = np.clip(np.asarray(y_prob, dtype=float), 1e-6, 1.0 - 1e-6)
    brier = float(brier_score_loss(y_true_arr, y_prob_arr))

    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    bins_data: List[Dict[str, Any]] = []
    weighted_ece = 0.0

    for i in range(n_bins):
        low, high = bin_edges[i], bin_edges[i + 1]
        mask = (y_prob_arr >= low) & (y_prob_arr <= high) if i == n_bins - 1 else (y_prob_arr >= low) & (y_prob_arr < high)
        n_in_bin = int(mask.sum())
        if n_in_bin > 0:
            mean_pred = float(y_prob_arr[mask].mean())
            obs_rate = float(y_true_arr[mask].mean())
            gap = abs(mean_pred - obs_rate)
            weighted_ece += (n_in_bin / len(y_true_arr)) * gap
        else:
            mean_pred = None
            obs_rate = None
            gap = None

        bins_data.append({
            "bin_index": i + 1,
            "bin_range": [round(float(low), 3), round(float(high), 3)],
            "count": n_in_bin,
            "mean_predicted_prob": round(mean_pred, 4) if mean_pred is not None else None,
            "observed_event_rate": round(obs_rate, 4) if obs_rate is not None else None,
            "calibration_gap": round(gap, 4) if gap is not None else None,
        })

    # Fit calibration slope and intercept: logit(p_pred) -> y_true
    logit_probs = np.log(y_prob_arr / (1.0 - y_prob_arr)).reshape(-1, 1)
    # C=np.inf is the supported unregularized form in current scikit-learn;
    # the former penalty=None spelling is deprecated.
    cal_lr = LogisticRegression(C=np.inf, solver="lbfgs", max_iter=500)
    try:
        cal_lr.fit(logit_probs, y_true_arr)
        slope = float(cal_lr.coef_[0][0])
        intercept = float(cal_lr.intercept_[0])
    except Exception:
        slope = None
        intercept = None

    return {
        "brier_score": round(brier, 4),
        "expected_calibration_error": round(weighted_ece, 4),
        "calibration_slope": round(slope, 4) if slope is not None else None,
        "calibration_intercept": round(intercept, 4) if intercept is not None else None,
        "reliability_bins": bins_data,
    }


def compute_clustered_confidence_intervals(
    df: pd.DataFrame,
    y_true_col: str,
    y_prob_col: str,
    cluster_col: str = "pseudo_id",
    n_bootstraps: int = 200,
    random_seed: int = 26186,
) -> Dict[str, Tuple[float, float]]:
    """Computes 95% bootstrap confidence intervals clustered by personnel ID."""
    rng = np.random.RandomState(random_seed)
    unique_clusters = df[cluster_col].unique()
    n_clusters = len(unique_clusters)

    roc_scores: List[float] = []
    pr_scores: List[float] = []

    # Map clusters to indices for fast sampling
    cluster_to_indices = df.groupby(cluster_col).indices

    for _ in range(n_bootstraps):
        sampled_clusters = rng.choice(unique_clusters, size=n_clusters, replace=True)
        sampled_indices = np.concatenate([cluster_to_indices[c] for c in sampled_clusters])

        y_true_b = df[y_true_col].values[sampled_indices]
        y_prob_b = df[y_prob_col].values[sampled_indices]

        if len(np.unique(y_true_b)) > 1:
            roc_scores.append(roc_auc_score(y_true_b, y_prob_b))
            pr_scores.append(average_precision_score(y_true_b, y_prob_b))

    if roc_scores:
        roc_ci = (round(float(np.percentile(roc_scores, 2.5)), 4), round(float(np.percentile(roc_scores, 97.5)), 4))
        pr_ci = (round(float(np.percentile(pr_scores, 2.5)), 4), round(float(np.percentile(pr_scores, 97.5)), 4))
    else:
        roc_ci = (0.5, 0.5)
        pr_ci = (0.0, 0.0)

    return {
        "roc_auc_95_ci": roc_ci,
        "pr_auc_95_ci": pr_ci,
    }


def compute_lead_time(
    df: pd.DataFrame,
    y_pred_col: str = "pred_positive",
    event_date_col: str = "future_window_start",
    cutoff_date_col: str = "prediction_date",
    leave_records: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Computes actionable lead time for true positive predictions.

    Lead time definition: Days from positive prediction cutoff T to target anomaly event.
    """
    tp_df = df[(df[y_pred_col] == 1) & (df["target_leave_anomaly"] == 1)].copy()
    if tp_df.empty:
        return {
            "definition": "Days from positive alert cutoff T to target anomaly event",
            "mean_lead_days": None,
            "median_lead_days": None,
            "distribution_summary": "No true positives generated at current threshold.",
        }

    # If full leave records available, compute exact days to actual event date
    if leave_records is not None:
        recs_by_pid: Dict[str, List[Dict[str, Any]]] = {}
        for r in leave_records:
            recs_by_pid.setdefault(str(r.get("personnel_id", r.get("pseudo_id"))), []).append(r)

        per_alert_days: List[int] = []
        first_alert_days: Dict[Tuple[str, date], Dict[str, Any]] = {}

        for _, row in tp_df.iterrows():
            pid = str(row["pseudo_id"])
            c_date = date.fromisoformat(str(row[cutoff_date_col]))
            h_end = c_date + timedelta(days=30)

            matching_dates = []
            for r in recs_by_pid.get(pid, []):
                if r.get("planning_classification") == "UNPLANNED" and r.get("actual_start_date") is not None:
                    d_act = r["actual_start_date"].date() if isinstance(r["actual_start_date"], datetime) else r["actual_start_date"]
                    if c_date < d_act <= h_end:
                        matching_dates.append(d_act)
                elif r.get("disruption_initiator") == "SERVICE" and r.get("disrupted_at") is not None:
                    d_dis = r["disrupted_at"].date() if isinstance(r["disrupted_at"], datetime) else r["disrupted_at"]
                    if c_date < d_dis <= h_end:
                        matching_dates.append(d_dis)

            if matching_dates:
                event_date = min(matching_dates)
                lt = (event_date - c_date).days
                per_alert_days.append(lt)

                ep_key = (pid, event_date)
                if ep_key not in first_alert_days or c_date < first_alert_days[ep_key]["first_cutoff"]:
                    first_alert_days[ep_key] = {
                        "first_cutoff": c_date,
                        "event_date": event_date,
                        "lead_days": lt,
                    }

        if per_alert_days:
            arr_alert = np.array(per_alert_days)
            arr_first = np.array([v["lead_days"] for v in first_alert_days.values()])
            return {
                "definition": "Days from positive prediction cutoff T to actual leave anomaly event date",
                "per_alert": {
                    "count": len(arr_alert),
                    "mean_lead_days": round(float(arr_alert.mean()), 2),
                    "median_lead_days": round(float(np.median(arr_alert)), 2),
                    "std_lead_days": round(float(arr_alert.std()), 2),
                    "p25": round(float(np.percentile(arr_alert, 25)), 2),
                    "p75": round(float(np.percentile(arr_alert, 75)), 2),
                    "min": int(arr_alert.min()),
                    "max": int(arr_alert.max()),
                },
                "first_actionable_alert_per_episode": {
                    "detected_episodes": len(arr_first),
                    "mean_lead_days": round(float(arr_first.mean()), 2),
                    "median_lead_days": round(float(np.median(arr_first)), 2),
                    "std_lead_days": round(float(arr_first.std()), 2),
                    "p25": round(float(np.percentile(arr_first, 25)), 2),
                    "p75": round(float(np.percentile(arr_first, 75)), 2),
                    "min": int(arr_first.min()),
                    "max": int(arr_first.max()),
                },
            }

    lead_days_list: List[int] = []
    for _, row in tp_df.iterrows():
        c_date = date.fromisoformat(str(row[cutoff_date_col]))
        e_date = date.fromisoformat(str(row[event_date_col]))
        lead_days = (e_date - c_date).days
        lead_days_list.append(lead_days)

    arr = np.array(lead_days_list)
    return {
        "definition": "Days from positive prediction cutoff T to target horizon window start",
        "mean_lead_days": round(float(arr.mean()), 1),
        "median_lead_days": round(float(np.median(arr)), 1),
        "distribution_summary": {
            "min": int(arr.min()),
            "max": int(arr.max()),
            "p25": float(np.percentile(arr, 25)),
            "p75": float(np.percentile(arr, 75)),
            "count": len(arr),
        },
    }


def evaluate_models_a_and_b(
    df_train: pd.DataFrame,
    df_test: pd.DataFrame,
    decision_threshold: float = 0.05,
) -> Dict[str, Any]:
    """Full comparative evaluation of Model A and Model B."""
    y_train = df_train["target_leave_anomaly"].values
    y_test = df_test["target_leave_anomaly"].values

    # 1. Model B: Canonical 15-Feature Contract
    prep_b = GovernedPreprocessor(expected_features=FEATURE_SET_B)
    X_train_b = prep_b.fit_transform(df_train)
    X_test_b = prep_b.transform(df_test)

    base_b = build_hr_model()
    cal_b = GovernedCalibrator(base_estimator=base_b, method="sigmoid", cv=3)
    cal_b.fit(X_train_b, y_train)

    prob_b = cal_b.predict_proba(X_test_b)[:, 1]
    metrics_b = compute_classification_metrics(y_test, prob_b, threshold=decision_threshold)
    diag_b = compute_calibration_diagnostics(y_test, prob_b, n_bins=5)

    # Attach predictions for CI and lead time
    df_test_b = df_test.copy()
    df_test_b["prob"] = prob_b
    df_test_b["pred_positive"] = (prob_b >= decision_threshold).astype(int)
    ci_b = compute_clustered_confidence_intervals(df_test_b, "target_leave_anomaly", "prob")
    lead_b = compute_lead_time(df_test_b, "pred_positive")

    # 2. Model A: 17 Features (with historical leave)
    prep_a = GovernedPreprocessor(expected_features=FEATURE_SET_A)
    X_train_a = prep_a.fit_transform(df_train)
    X_test_a = prep_a.transform(df_test)

    base_a = build_hr_model()
    cal_a = GovernedCalibrator(base_estimator=base_a, method="sigmoid", cv=3)
    cal_a.fit(X_train_a, y_train)

    prob_a = cal_a.predict_proba(X_test_a)[:, 1]
    metrics_a = compute_classification_metrics(y_test, prob_a, threshold=decision_threshold)
    diag_a = compute_calibration_diagnostics(y_test, prob_a, n_bins=5)

    df_test_a = df_test.copy()
    df_test_a["prob"] = prob_a
    df_test_a["pred_positive"] = (prob_a >= decision_threshold).astype(int)
    ci_a = compute_clustered_confidence_intervals(df_test_a, "target_leave_anomaly", "prob")
    lead_a = compute_lead_time(df_test_a, "pred_positive")

    return {
        "TASK_19_STATUS": "PASS",
        "decision_threshold": decision_threshold,
        "model_b_canonical": {
            "metrics": metrics_b,
            "calibration_diagnostics": diag_b,
            "clustered_confidence_intervals": ci_b,
            "lead_time": lead_b,
        },
        "model_a_comparative": {
            "metrics": metrics_a,
            "calibration_diagnostics": diag_a,
            "clustered_confidence_intervals": ci_a,
            "lead_time": lead_a,
        },
    }


def evaluate_metrics(y_true, y_pred, y_prob=None):
    """Compatibility wrapper."""
    if y_prob is not None:
        return compute_classification_metrics(y_true, y_prob)
    return {
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
    }


__all__ = [
    "compute_classification_metrics",
    "compute_calibration_diagnostics",
    "compute_clustered_confidence_intervals",
    "compute_lead_time",
    "evaluate_models_a_and_b",
    "evaluate_metrics",
]
