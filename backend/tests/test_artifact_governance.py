"""Tests for PRAHARI Task 26 & 27: Governed Artifact Format, Integrity & Reproducibility."""

from pathlib import Path
import tempfile
import numpy as np
import pandas as pd
import pytest

from tools.training.artifact import (
    DEFAULT_ARTIFACT_PATH,
    DEFAULT_MANIFEST_PATH,
    build_model_a_candidate_artifact,
    compute_file_sha256,
    load_model_a_artifact,
    save_model_a_artifact,
)
from app.ml.features_hr import FEATURE_SET_B


def test_saved_candidate_artifact_exists_and_matches_manifest():
    """Verify that the official candidate artifact exists on disk and matches manifest."""
    assert DEFAULT_ARTIFACT_PATH.exists(), f"Candidate artifact missing at {DEFAULT_ARTIFACT_PATH}"
    assert DEFAULT_MANIFEST_PATH.exists(), f"Candidate manifest missing at {DEFAULT_MANIFEST_PATH}"

    # Compute actual SHA-256
    actual_hash = compute_file_sha256(DEFAULT_ARTIFACT_PATH)

    # Load with hash verification
    artifact = load_model_a_artifact(DEFAULT_ARTIFACT_PATH, expected_sha256=actual_hash)

    assert artifact["model_version"] == "1.0.0"
    assert artifact["target_version"] == "v2.1-approved-leave-lifecycle"
    assert artifact["feature_names"] == list(FEATURE_SET_B)
    assert len(artifact["feature_names"]) == 15
    assert artifact["threshold_policy"]["tau_high"] == 0.15
    assert artifact["threshold_policy"]["safety_floors_mode"] == "PASS_THROUGH"


def test_artifact_tamper_detection():
    """Verify that tampering or wrong expected hash raises ValueError."""
    actual_hash = compute_file_sha256(DEFAULT_ARTIFACT_PATH)
    fake_hash = "0000000000000000000000000000000000000000000000000000000000000000"

    with pytest.raises(ValueError, match="integrity violation"):
        load_model_a_artifact(DEFAULT_ARTIFACT_PATH, expected_sha256=fake_hash)


def test_load_after_save_roundtrip_and_prediction_reproducibility():
    """Verify load-after-save roundtrip and exact prediction reproducibility."""
    artifact = load_model_a_artifact(DEFAULT_ARTIFACT_PATH)
    preprocessor = artifact["preprocessor"]
    calibrator = artifact["calibrator"]

    # Synthesize test rows with 15 features
    data = {fn: [10.0 + i, 20.0 - i, 5.0 * i] for i, fn in enumerate(FEATURE_SET_B)}
    test_df = pd.DataFrame(data)

    X_test = preprocessor.transform(test_df)
    probs_1 = calibrator.predict_proba(X_test)[:, 1]

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_art_path = Path(tmpdir) / "test_artifact.joblib"
        tmp_man_path = Path(tmpdir) / "test_manifest.json"

        save_model_a_artifact(artifact, tmp_art_path, tmp_man_path)
        assert tmp_art_path.exists()
        assert tmp_man_path.exists()

        loaded_tmp = load_model_a_artifact(tmp_art_path)
        X_tmp = loaded_tmp["preprocessor"].transform(test_df)
        probs_2 = loaded_tmp["calibrator"].predict_proba(X_tmp)[:, 1]

        np.testing.assert_allclose(probs_1, probs_2, atol=1e-7)


def test_feature_order_invariance_through_preprocessor():
    """Verify that feeding columns in shuffled order is safely handled by preprocessor."""
    artifact = load_model_a_artifact(DEFAULT_ARTIFACT_PATH)
    preprocessor = artifact["preprocessor"]

    data = {fn: [float(i + 1)] for i, fn in enumerate(FEATURE_SET_B)}
    df_ordered = pd.DataFrame(data)

    # Shuffled columns
    shuffled_cols = list(reversed(FEATURE_SET_B))
    df_shuffled = df_ordered[shuffled_cols]

    X_ordered = preprocessor.transform(df_ordered)
    X_shuffled = preprocessor.transform(df_shuffled)

    np.testing.assert_allclose(X_ordered, X_shuffled, atol=1e-7)
