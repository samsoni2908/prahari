"""Tests for Task 19 & 20: Comprehensive Model-A Evaluation & Lead Time.

Verifies:
1. Classification metrics computation (ROC-AUC, PR-AUC, Brier, F1).
2. Person-clustered confidence intervals generation.
3. Actionable lead time calculation.
4. Comparative A/B evaluation between Model A and Model B.
"""

import numpy as np
import pandas as pd
import pytest

from tools.training.dataset_builder import build_model_a_dataset
from tools.training.evaluate import (
    compute_classification_metrics,
    compute_clustered_confidence_intervals,
    compute_lead_time,
    evaluate_models_a_and_b,
)
from tools.training.split import create_temporal_split


def test_compute_classification_metrics():
    y_true = np.array([0, 0, 1, 1, 0, 1])
    y_prob = np.array([0.1, 0.2, 0.8, 0.9, 0.3, 0.7])
    metrics = compute_classification_metrics(y_true, y_prob, threshold=0.5)

    assert metrics["roc_auc"] == 1.0
    assert metrics["brier_score"] < 0.10
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1"] == 1.0


def test_task19_full_evaluation():
    df, _ = build_model_a_dataset()
    # Ensure leave features for Model A are available
    if "leave_frequency_90d" not in df.columns:
        df["leave_frequency_90d"] = 1.0
        df["leave_gap_variability_90d"] = 1.0

    df_train, df_test, _ = create_temporal_split(df, test_weeks=7, min_embargo_days=30)
    report = evaluate_models_a_and_b(df_train, df_test)

    assert report["TASK_19_STATUS"] == "PASS"
    assert "model_b_canonical" in report
    assert "model_a_comparative" in report

    # Check Model B metrics
    m_b = report["model_b_canonical"]["metrics"]
    for k in ["roc_auc", "pr_auc", "brier_score", "precision", "recall", "f1"]:
        assert k in m_b

    # Check Clustered CIs
    ci_b = report["model_b_canonical"]["clustered_confidence_intervals"]
    assert "roc_auc_95_ci" in ci_b
    assert "pr_auc_95_ci" in ci_b
    assert len(ci_b["roc_auc_95_ci"]) == 2

    # Check Lead Time
    lead_b = report["model_b_canonical"]["lead_time"]
    assert "definition" in lead_b
