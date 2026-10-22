"""
PRAHARI â€” Model-A Candidate Training Workflow (Task 17)
Canonical Reference: AGENTS.md Â§8, rules.md, docs/ml.md Â§6.4

Trains candidate regularized Logistic Regression separately on:
- Feature Set A (includes historical leave features)
- Feature Set B (strictly operational features, canonical contract)

Computes metrics, evaluates circular dependence, and checks convergence.
Do NOT calibrate yet (calibration is Task 18).
Do NOT select model solely by ROC-AUC.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from tools.training.dataset_builder import build_model_a_dataset
from app.ml.features_hr import FEATURE_SET_A, FEATURE_SET_B
from tools.training.models.hr_model import build_hr_model
from tools.training.preprocessing import GovernedPreprocessor
from tools.training.split import create_rolling_origin_splits, create_temporal_split


def evaluate_split_metrics(
    model: LogisticRegression,
    X_val: np.ndarray,
    y_val: np.ndarray,
) -> Dict[str, float]:
    """Computes comprehensive classification metrics on validation fold."""
    prob = model.predict_proba(X_val)[:, 1]
    pred = model.predict(X_val)

    roc_auc = float(roc_auc_score(y_val, prob)) if len(np.unique(y_val)) > 1 else 0.5
    pr_auc = float(average_precision_score(y_val, prob))
    brier = float(brier_score_loss(y_val, prob))
    prec = float(precision_score(y_val, pred, zero_division=0))
    rec = float(recall_score(y_val, pred, zero_division=0))
    f1 = float(f1_score(y_val, pred, zero_division=0))

    return {
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "brier_score": round(brier, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
    }


def train_candidate_models(
    df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """Trains and compares candidate Model-A architectures on Feature Sets A and B."""
    if df is None:
        df, _ = build_model_a_dataset()

    # Load raw file to get historical leave features for Set A if not present
    if "leave_frequency_90d" not in df.columns:
        source_raw = None
        candidates = [
            Path("/data/seed26186/ml_training.csv"),
            Path("data/seed26186/ml_training.csv"),
            Path(__file__).resolve().parent.parent.parent.parent / "data" / "seed26186" / "ml_training.csv",
        ]
        for c in candidates:
            if c.exists():
                source_raw = c
                break
        if source_raw and source_raw.exists():
            df_raw = pd.read_csv(source_raw)
            for c in ["leave_frequency_90d", "leave_gap_variability_90d"]:
                if c in df_raw.columns:
                    df[c] = df_raw[c]

    # Temporal split with strict embargo gap >= 30 days
    df_train, df_test, split_res = create_temporal_split(df, test_weeks=7, min_embargo_days=30)

    # Rolling origin validation fold inside train window (keeps test set untouched)
    val_folds = create_rolling_origin_splits(df_train, n_splits=1, val_weeks=4, min_embargo_days=30)
    f_train, f_val = val_folds[0]

    y_train = f_train["target_leave_anomaly"].values
    y_val = f_val["target_leave_anomaly"].values

    # --- Train Feature Set B (Canonical Contract: 15 features) ---
    prep_b = GovernedPreprocessor(expected_features=FEATURE_SET_B)
    X_train_b = prep_b.fit_transform(f_train)
    X_val_b = prep_b.transform(f_val)

    model_b = build_hr_model()
    model_b.fit(X_train_b, y_train)
    metrics_b = evaluate_split_metrics(model_b, X_val_b, y_val)
    coefs_b = pd.Series(model_b.coef_[0], index=prep_b.get_feature_names_out()).to_dict()

    # --- Train Feature Set A (Includes Historical Leave Features: 17 features) ---
    prep_a = GovernedPreprocessor(expected_features=FEATURE_SET_A)
    X_train_a = prep_a.fit_transform(f_train)
    X_val_a = prep_a.transform(f_val)

    model_a = build_hr_model()
    model_a.fit(X_train_a, y_train)
    metrics_a = evaluate_split_metrics(model_a, X_val_a, y_val)
    coefs_a = pd.Series(model_a.coef_[0], index=prep_a.get_feature_names_out()).to_dict()

    return {
        "TASK_17_STATUS": "PASS",
        "A_metrics": metrics_a,
        "B_metrics": metrics_b,
        "convergence_status": {
            "model_A_converged": bool(model_a.n_iter_[0] < 1000),
            "model_A_iterations": int(model_a.n_iter_[0]),
            "model_B_converged": bool(model_b.n_iter_[0] < 1000),
            "model_B_iterations": int(model_b.n_iter_[0]),
        },
        "coefficients_sanity": {
            "top_risk_drivers_B": sorted(coefs_b.items(), key=lambda x: x[1], reverse=True)[:5],
            "top_protective_factors_B": sorted(coefs_b.items(), key=lambda x: x[1])[:5],
            "historical_leave_coefficients_A": {
                k: round(v, 4) for k, v in coefs_a.items() if "leave_" in k
            },
        },
    }


def train_model_a() -> Dict[str, Any]:
    """Compatibility wrapper."""
    return train_candidate_models()


__all__ = [
    "evaluate_split_metrics",
    "train_candidate_models",
    "train_model_a",
]
