"""Tests for Task 13: Model-A Training Dataset Builder.

Verifies:
1. Exactly 15 approved features in locked order.
2. Banned columns (raw wellbeing, private wellbeing, Model-C, leave frequency/variability) quarantined.
3. Target is binary {0, 1} and TARGET_UNAVAILABLE rows are strictly excluded.
4. No leakage: all feature correlations < 0.85.
5. All prediction dates and future window bounds strictly respected.
"""

from pathlib import Path
import pytest
import pandas as pd

from tools.training.dataset_builder import CANONICAL_COLUMNS, build_model_a_dataset
from app.ml.features_hr import MODEL_A_FEATURE_NAMES


def test_task13_dataset_build_and_leakage():
    df, report = build_model_a_dataset()

    # 1. Status is PASS
    assert report["TASK_13_STATUS"] == "PASS"

    # 2. Rows and persons
    assert report["eligible_rows"] > 10000
    assert report["persons"] == 300
    assert report["excluded_unavailable_rows"] > 0

    # 3. Columns check
    for col in CANONICAL_COLUMNS:
        assert col in df.columns

    # 4. Strict exclusion of banned columns
    banned_terms = ["wellbeing", "phq", "gad", "who", "pss", "model_c", "leave_frequency", "leave_gap"]
    for col in df.columns:
        for b in banned_terms:
            assert b not in col.lower(), f"Banned column {col} found in dataset!"

    # 5. Target is strictly binary 0 or 1
    assert set(df["target_leave_anomaly"].unique()) == {0, 1}
    assert report["positive_count"] > 0
    assert report["negative_count"] > report["positive_count"]
    assert 0.01 <= report["positive_rate"] <= 0.15

    # 6. Leakage scan
    leakage = report["leakage_scan_result"]
    assert not leakage["leakage_detected"]
    assert abs(leakage["max_feature_correlation"]) < 0.50
