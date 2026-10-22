"""Tests for Task 19B: Clean Synthetic Validation Governance & Anti-Leakage Contracts.

Verifies:
1. Generator manifest is frozen and immutable.
2. Development and validation seeds differ and validation seed is predetermined.
3. No validation/test rows were used to calculate centering/scaling constants.
4. No validation/test rows enter preprocessing fit (only transform).
5. No validation/test rows enter calibration fit (only predict_proba).
6. Target uses strictly prior operational history (events <= T do not trigger future horizon).
7. No direct WSI-to-label mapping (not a deterministic function of WSI).
8. No deterministic feature threshold creates Y (stochastic property holds at extremes).
"""

from dataclasses import FrozenInstanceError
from datetime import date, timedelta
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

from tools.training.synthetic_leave_manifest import (
    SYNTHETIC_COUPLING_MANIFEST_V2_1,
)
from tools.training.dataset_builder import build_model_a_dataset
from tools.training.split import create_temporal_split
from app.ml.features_hr import FEATURE_SET_B
from tools.training.preprocessing import GovernedPreprocessor
from tools.training.calibrate import GovernedCalibrator
from tools.training.models.hr_model import build_hr_model
from app.ml.targets import generate_leave_anomaly_target, LeaveTargetState


def test_manifest_immutable_and_frozen():
    """Requirement 16.1: Generator manifest is immutable/frozen."""
    manifest = SYNTHETIC_COUPLING_MANIFEST_V2_1
    assert manifest.manifest_version == "v2.1-frozen-prototype"
    with pytest.raises(FrozenInstanceError):
        manifest.base_event_rate = 0.05  # type: ignore


def test_development_and_validation_seeds_differ():
    """Requirement 16.2 & 16.3: Dev and validation seeds differ and are predetermined."""
    manifest = SYNTHETIC_COUPLING_MANIFEST_V2_1
    assert manifest.development_seed == 26186
    assert manifest.validation_seed == 27186
    assert manifest.development_seed != manifest.validation_seed
    assert manifest.validation_seed is not None


def test_centering_scaling_strictly_training_only():
    """Requirement 16.4: Centering/scaling constants match training-only data, not full data."""
    raw_path = Path(__file__).resolve().parents[2] / "data" / "seed26186" / "ml_training.csv"
    assert raw_path.is_file(), f"Required synthetic validation fixture is missing: {raw_path}"

    df = pd.read_csv(raw_path)
    df_train = df[df["split"] == "train"]

    manifest = SYNTHETIC_COUPLING_MANIFEST_V2_1
    train_mean_duty = df_train["duty_hours_30d"].mean()
    full_mean_duty = df["duty_hours_30d"].mean()

    assert abs(manifest.duty_hours_center - train_mean_duty) < 0.5
    assert abs(manifest.duty_hours_center - full_mean_duty) > 3.0


def test_no_validation_rows_enter_preprocessing_fit():
    """Requirement 16.5: Validation/test rows are only transformed, never fit."""
    df, _ = build_model_a_dataset(random_seed=SYNTHETIC_COUPLING_MANIFEST_V2_1.development_seed)
    df_train, df_test, _ = create_temporal_split(df, test_weeks=7, min_embargo_days=30)

    preprocessor = GovernedPreprocessor(expected_features=FEATURE_SET_B)
    X_train = preprocessor.fit_transform(df_train)
    assert preprocessor.is_fitted_

    X_test = preprocessor.transform(df_test)
    assert X_test.shape[0] == len(df_test)
    assert X_test.shape[1] == X_train.shape[1]


def test_no_validation_rows_enter_calibration_fit():
    """Requirement 16.6: Calibrator is fit only on training data."""
    df, _ = build_model_a_dataset(random_seed=SYNTHETIC_COUPLING_MANIFEST_V2_1.development_seed)
    df_train, df_test, _ = create_temporal_split(df, test_weeks=7, min_embargo_days=30)

    preprocessor = GovernedPreprocessor(expected_features=FEATURE_SET_B)
    X_train = preprocessor.fit_transform(df_train)
    y_train = df_train["target_leave_anomaly"].values

    base_model = build_hr_model()
    calibrator = GovernedCalibrator(base_estimator=base_model, method="sigmoid", cv=3)
    calibrator.fit(X_train, y_train)
    assert calibrator.is_fitted_

    X_test = preprocessor.transform(df_test)
    test_probs = calibrator.predict_proba(X_test)[:, 1]
    assert len(test_probs) == len(df_test)
    assert (test_probs >= 0.0).all() and (test_probs <= 1.0).all()


def test_target_uses_strictly_prior_operational_history():
    """Requirement 16.7: Past events (<= T) do NOT trigger future target horizon (T, T+30d]."""
    cutoff = date(2026, 6, 1)
    past_event = {
        "planning_classification": "UNPLANNED",
        "actual_start_date": date(2026, 5, 25),
        "actual_end_date": date(2026, 5, 30),
    }
    state, _ = generate_leave_anomaly_target([past_event], cutoff_date=cutoff, horizon_days=30)
    assert state == LeaveTargetState.NEGATIVE


def test_no_direct_wsi_to_label_mapping():
    """Requirement 16.8: Target is not a deterministic transformation of WSI."""
    df, _ = build_model_a_dataset(random_seed=SYNTHETIC_COUPLING_MANIFEST_V2_1.development_seed)
    corr = df["ewma_workload"].corr(df["target_leave_anomaly"])
    assert 0.05 < corr < 0.60


def test_stochastic_property_holds_at_extremes():
    """Requirement 16.9: High workload has non-zero chance of 0, low workload has non-zero chance of 1."""
    df, _ = build_model_a_dataset(random_seed=SYNTHETIC_COUPLING_MANIFEST_V2_1.development_seed)
    high_workload = df[df["duty_hours_30d"] > df["duty_hours_30d"].quantile(0.85)]
    low_workload = df[df["duty_hours_30d"] < df["duty_hours_30d"].quantile(0.15)]

    assert (high_workload["target_leave_anomaly"] == 0).sum() > 0
    assert (low_workload["target_leave_anomaly"] == 1).sum() > 0
