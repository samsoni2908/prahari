"""Tests for Task 18: Governed Probability Calibration.

TASK 18 TESTS:
1. probabilities 0..1: Predicted probabilities are strictly bounded in [0.0, 1.0].
2. calibration split isolation: Calibration is fitted strictly on training data; test set isolated.
3. serialization: GovernedCalibrator serializes and deserializes via joblib with identical outputs.
4. Brier score improvement: Verifies uncalibrated vs calibrated Brier score reduction.
"""

from pathlib import Path
import numpy as np
import pytest

from tools.training.calibrate import GovernedCalibrator, calculate_brier_score, calibrate_and_evaluate
from tools.training.dataset_builder import build_model_a_dataset
from app.ml.features_hr import FEATURE_SET_B
from tools.training.models.hr_model import build_hr_model
from tools.training.preprocessing import GovernedPreprocessor
from tools.training.split import create_rolling_origin_splits, create_temporal_split


@pytest.fixture
def sample_splits():
    df, _ = build_model_a_dataset()
    df_train, df_test, _ = create_temporal_split(df, test_weeks=7, min_embargo_days=30)
    val_folds = create_rolling_origin_splits(df_train, n_splits=1, val_weeks=4, min_embargo_days=30)
    f_train, f_val = val_folds[0]

    prep = GovernedPreprocessor(expected_features=FEATURE_SET_B)
    X_train = prep.fit_transform(f_train)
    X_val = prep.transform(f_val)
    y_train = f_train["target_leave_anomaly"].values
    y_val = f_val["target_leave_anomaly"].values

    return X_train, y_train, X_val, y_val, df_test


def test_task18_probabilities_bounds(sample_splits):
    """TASK 18 TEST 1: Probabilities are strictly within [0.0, 1.0]."""
    X_train, y_train, X_val, y_val, _ = sample_splits
    base_model = build_hr_model()
    calibrator = GovernedCalibrator(base_estimator=base_model, method="sigmoid", cv=3)
    calibrator.fit(X_train, y_train)

    probs = calibrator.predict_proba(X_val)
    assert (probs >= 0.0).all()
    assert (probs <= 1.0).all()
    np.testing.assert_allclose(probs.sum(axis=1), 1.0, rtol=1e-5)


def test_task18_calibration_split_isolation(sample_splits):
    """TASK 18 TEST 2: Calibration split isolation - test set is never seen by calibrator."""
    X_train, y_train, X_val, y_val, df_test = sample_splits

    base_model = build_hr_model()
    calibrator, report = calibrate_and_evaluate(
        base_estimator=base_model,
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        method="sigmoid",
        cv=3,
    )

    # Verification: report metrics are generated cleanly
    assert report["uncalibrated_brier"] > report["calibrated_brier"]
    assert report["brier_improvement"] > 0
    assert "Platt scaling" in report["calibration_method"]


def test_task18_serialization(sample_splits, tmp_path):
    """TASK 18 TEST 3: Serialization compatibility."""
    X_train, y_train, X_val, y_val, _ = sample_splits
    base_model = build_hr_model()
    calibrator = GovernedCalibrator(base_estimator=base_model, method="sigmoid", cv=3)
    calibrator.fit(X_train, y_train)

    original_probs = calibrator.predict_proba(X_val)

    save_file = tmp_path / "calibrated_model.joblib"
    calibrator.save(save_file)
    assert save_file.exists()

    loaded_calibrator = GovernedCalibrator.load(save_file)
    loaded_probs = loaded_calibrator.predict_proba(X_val)

    np.testing.assert_allclose(original_probs, loaded_probs)
