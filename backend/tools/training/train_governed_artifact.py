"""Script to build and persist the official governed Model-A candidate artifact (Task 27)."""

from pathlib import Path
import numpy as np

from tools.training.artifact import (
    DEFAULT_ARTIFACT_PATH,
    DEFAULT_MANIFEST_PATH,
    build_model_a_candidate_artifact,
    load_model_a_artifact,
    save_model_a_artifact,
)
from tools.training.calibrate import GovernedCalibrator
from tools.training.dataset_builder import build_model_a_dataset
from app.ml.features_hr import FEATURE_SET_B
from tools.training.models.hr_model import build_hr_model
from tools.training.preprocessing import GovernedPreprocessor
from tools.training.split import create_temporal_split
from tools.training.synthetic_leave_manifest import SYNTHETIC_COUPLING_MANIFEST_V2_1


def train_and_persist_candidate_artifact():
    print("Building Model-A dataset from frozen synthetic generator (dev seed 26186)...")
    df, _ = build_model_a_dataset(random_seed=SYNTHETIC_COUPLING_MANIFEST_V2_1.development_seed)

    print("Splitting chronologically with 70-day embargo...")
    df_train, df_test, split_res = create_temporal_split(df, test_weeks=7, min_embargo_days=30)

    print(f"Training partition: {len(df_train)} rows. Fitting GovernedPreprocessor on Feature Set B...")
    preprocessor = GovernedPreprocessor(expected_features=FEATURE_SET_B)
    X_train = preprocessor.fit_transform(df_train)
    y_train = df_train["target_leave_anomaly"].values

    print("Fitting GovernedCalibrator (Platt sigmoid with 3-fold internal CV)...")
    base_model = build_hr_model()
    calibrator = GovernedCalibrator(base_estimator=base_model, method="sigmoid", cv=3)
    calibrator.fit(X_train, y_train)

    print("Building candidate artifact dictionary...")
    artifact = build_model_a_candidate_artifact(
        preprocessor=preprocessor,
        calibrator=calibrator,
        training_data_meta={
            "train_rows": len(df_train),
            "test_rows": len(df_test),
            "train_date_min": str(df_train["prediction_date"].min()),
            "train_date_max": str(df_train["prediction_date"].max()),
            "embargo_days": 70,
        },
    )

    print(f"Saving artifact to {DEFAULT_ARTIFACT_PATH}...")
    art_path, sha256 = save_model_a_artifact(artifact)
    print(f"Artifact successfully saved! SHA-256: {sha256}")

    # Load-after-save verification
    print("Executing load-after-save verification...")
    loaded = load_model_a_artifact(art_path, expected_sha256=sha256)
    assert loaded["model_version"] == "1.0.0"

    # Prediction reproducibility verification on test set sample
    sample_df = df_test.head(10)
    X_sample_orig = preprocessor.transform(sample_df)
    probs_orig = calibrator.predict_proba(X_sample_orig)[:, 1]

    X_sample_loaded = loaded["preprocessor"].transform(sample_df)
    probs_loaded = loaded["calibrator"].predict_proba(X_sample_loaded)[:, 1]

    np.testing.assert_allclose(probs_orig, probs_loaded, atol=1e-7)
    print(f"Prediction reproducibility verified on {len(sample_df)} sample test rows (max abs delta: {np.max(np.abs(probs_orig - probs_loaded))}).")
    return art_path, sha256


if __name__ == "__main__":
    train_and_persist_candidate_artifact()
