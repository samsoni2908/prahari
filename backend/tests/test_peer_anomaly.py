"""
Unit tests for Task 08: Peer Anomaly Detection (PRAHARI Model-A).
Tests required:
- adequate cohort (successful Isolation Forest execution)
- small cohort (INSUFFICIENT_PEER_DATA, never fake score 0.0)
- single person (INSUFFICIENT_PEER_DATA)
- missing feature data (MISSING_FEATURE_DATA for member, never arbitrary imputation)
- obvious anomaly (correctly flagged by Isolation Forest)
"""

import numpy as np
import pytest

from app.analytics.peer_anomaly import (
    DEFAULT_CONTAMINATION,
    DEFAULT_MIN_COHORT_SIZE,
    DEFAULT_N_ESTIMATORS,
    PeerAnomalyStatus,
    detect_peer_anomalies,
)


def test_t08_adequate_cohort_success():
    """Verify Isolation Forest execution on an adequate cohort."""
    np.random.seed(26186)
    # 25 synthetic members with 3 operational features: duty_hours, night_ratio, rest_hours
    cohort = np.random.normal(loc=[40.0, 0.20, 8.0], scale=[3.0, 0.05, 0.5], size=(25, 3)).tolist()
    pids = [f"P_{i:02d}" for i in range(25)]

    results = detect_peer_anomalies(cohort, identifiers=pids, min_cohort_size=5)
    assert len(results) == 25
    for pid, res in results.items():
        assert res["status"] == PeerAnomalyStatus.VALID.value
        assert res["score"] is not None
        assert res["is_anomaly"] is not None
        assert isinstance(res["is_anomaly"], bool)


def test_t08_small_cohort_insufficient_peer_data():
    """
    CRITICAL CONTRACT:
    When peer group is sparse (< min_cohort_size), DO NOT return fake score 0.0
    or fabricated is_anomaly=False.
    Must return INSUFFICIENT_PEER_DATA with score=None.
    """
    # Cohort of 3 members when min_cohort_size is 5
    small_cohort = [
        [40.0, 0.20, 8.0],
        [42.0, 0.22, 7.5],
        [38.0, 0.18, 8.5],
    ]
    pids = ["P1", "P2", "P3"]

    results = detect_peer_anomalies(small_cohort, identifiers=pids, min_cohort_size=5)
    assert len(results) == 3
    for pid, res in results.items():
        assert res["status"] == PeerAnomalyStatus.INSUFFICIENT_PEER_DATA.value
        # MUST NOT be fake 0.0 or False!
        assert res["score"] is None
        assert res["anomaly_score"] is None
        assert res["is_anomaly"] is None
        assert "Insufficient peer cohort size" in (res["reason"] or "")


def test_t08_single_person_cohort():
    """Verify single-person cohort returns INSUFFICIENT_PEER_DATA."""
    single_person = [[40.0, 0.20, 8.0]]
    results = detect_peer_anomalies(single_person, identifiers=["P1"], min_cohort_size=5)
    assert results["P1"]["status"] == PeerAnomalyStatus.INSUFFICIENT_PEER_DATA.value
    assert results["P1"]["score"] is None
    assert results["P1"]["is_anomaly"] is None


def test_t08_missing_feature_data_handling():
    """Verify feature row containing None or NaN returns MISSING_FEATURE_DATA."""
    # Cohort of 8 members (adequate), but member at index 2 has None
    cohort = [
        [40.0, 0.20, 8.0],
        [42.0, 0.22, 7.5],
        [45.0, None, 8.0],  # Corrupted row
        [39.0, 0.19, 8.2],
        [41.0, 0.21, 7.8],
        [43.0, 0.23, 7.6],
        [38.0, 0.18, 8.4],
        [40.5, 0.20, 8.1],
    ]
    pids = [f"P_{i}" for i in range(8)]

    results = detect_peer_anomalies(cohort, identifiers=pids, min_cohort_size=5)
    # Member 2 must be flagged with MISSING_FEATURE_DATA
    assert results["P_2"]["status"] == PeerAnomalyStatus.MISSING_FEATURE_DATA.value
    assert results["P_2"]["score"] is None
    assert results["P_2"]["is_anomaly"] is None

    # Other members remain VALID (7 remaining > min_cohort_size 5)
    assert results["P_0"]["status"] == PeerAnomalyStatus.VALID.value
    assert results["P_0"]["score"] is not None


def test_t08_obvious_anomaly_detection():
    """Verify that extreme multivariate outliers are correctly identified as anomalies."""
    np.random.seed(26186)
    # 30 normal, tightly clustered peers
    normal_cohort = np.random.normal(loc=[40.0, 0.15, 8.0], scale=[2.0, 0.03, 0.3], size=(30, 3)).tolist()
    # 2 obvious extreme outliers: massive duty hours, high night shift, near-zero rest
    outlier_1 = [95.0, 0.90, 1.5]
    outlier_2 = [92.0, 0.85, 2.0]

    matrix = normal_cohort + [outlier_1, outlier_2]
    pids = [f"norm_{i}" for i in range(30)] + ["outlier_1", "outlier_2"]

    results = detect_peer_anomalies(matrix, identifiers=pids, contamination=0.10, min_cohort_size=5)
    assert len(results) == 32

    # Both outliers must be flagged
    assert results["outlier_1"]["is_anomaly"] is True
    assert results["outlier_1"]["is_peer_anomaly"] is True
    assert results["outlier_1"]["score"] < 0.0  # decision_function < 0 indicates anomaly

    assert results["outlier_2"]["is_anomaly"] is True
    assert results["outlier_2"]["is_peer_anomaly"] is True
    assert results["outlier_2"]["score"] < 0.0
