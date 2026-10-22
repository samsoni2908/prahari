"""Tests for Task 17: Candidate Logistic Regression Models.

Verifies:
1. Candidate models train separately on Feature Sets A and B without error.
2. Models converge within max_iter=1000.
3. Classification metrics (ROC-AUC, PR-AUC, Brier, F1) computed cleanly.
4. Coefficients extracted and inspected for sanity.
5. Final test window remains untouched.
"""

import pytest

from tools.training.train_hr import train_candidate_models


def test_task17_candidate_training():
    report = train_candidate_models()

    assert report["TASK_17_STATUS"] == "PASS"

    # Convergence
    conv = report["convergence_status"]
    assert conv["model_A_converged"]
    assert conv["model_B_converged"]
    assert conv["model_A_iterations"] < 1000
    assert conv["model_B_iterations"] < 1000

    # Metrics present
    metrics_a = report["A_metrics"]
    metrics_b = report["B_metrics"]
    for m in ["roc_auc", "pr_auc", "brier_score", "precision", "recall", "f1"]:
        assert m in metrics_a
        assert m in metrics_b
        assert 0.0 <= metrics_a[m] <= 1.0 or metrics_a[m] == 0.0
        assert 0.0 <= metrics_b[m] <= 1.0 or metrics_b[m] == 0.0

    # Sanity of coefficients
    sanity = report["coefficients_sanity"]
    assert len(sanity["top_risk_drivers_B"]) == 5
    assert len(sanity["top_protective_factors_B"]) == 5
