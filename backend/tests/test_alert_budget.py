"""Tests for Task 21: Alert-Budget & Threshold Analysis."""

import numpy as np
import pytest

from tools.training.alert_budget import CANDIDATE_THRESHOLDS, compute_threshold_curve


def test_threshold_curve_properties():
    # Synthetic ground truth and predicted probabilities
    y_true = np.array([0, 0, 0, 1, 0, 1, 0, 1, 1, 0] * 10)
    y_prob = np.array([0.05, 0.12, 0.18, 0.25, 0.30, 0.45, 0.08, 0.55, 0.60, 0.22] * 10)

    curve = compute_threshold_curve(y_true, y_prob, thresholds=[0.10, 0.20, 0.30, 0.50], n_personnel=10, n_weeks=1)

    assert len(curve) == 4

    # Monotonicity checks:
    # As threshold increases, total alerts and recall must be non-increasing
    alerts = [row["total_alerts"] for row in curve]
    recalls = [row["recall"] for row in curve]
    for i in range(len(curve) - 1):
        assert alerts[i] >= alerts[i + 1]
        assert recalls[i] >= recalls[i + 1]

    # Metrics range
    for row in curve:
        assert 0.0 <= row["precision"] <= 1.0
        assert 0.0 <= row["recall"] <= 1.0
        assert 0.0 <= row["f1"] <= 1.0
        assert row["total_alerts"] == row["true_positives"] + row["false_positives"]
