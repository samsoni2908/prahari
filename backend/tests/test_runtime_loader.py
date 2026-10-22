"""Tests for PRAHARI Task 28 & 29: Model-A Runtime Loader & Safe Inference."""

from pathlib import Path
import tempfile
import joblib
import numpy as np
import pytest
from unittest.mock import patch

from tools.training.artifact import (
    DEFAULT_ARTIFACT_PATH,
    FEATURE_SPEC_VERSION,
    TARGET_VERSION,
    load_model_a_artifact,
)
from app.ml.features_hr import FEATURE_SET_B
from app.ml.runtime_loader import (
    ModelARuntimeLoader,
    STATUS_AVAILABLE,
    STATUS_UNAVAILABLE,
    model_a_runtime,
)


def test_valid_artifact_loads_as_model_available():
    """Verify that the default approved artifact loads with STATUS_AVAILABLE."""
    loader = ModelARuntimeLoader(DEFAULT_ARTIFACT_PATH)
    assert loader.status == STATUS_AVAILABLE
    assert loader.artifact is not None
    assert "VALID" in loader.status_reason


def test_missing_artifact_sets_model_unavailable_with_zero_fallback():
    """Verify that a nonexistent artifact sets MODEL_UNAVAILABLE with no crashes or fallbacks."""
    missing_path = Path("/tmp/nonexistent_model_artifact_xyz.joblib")
    loader = ModelARuntimeLoader(missing_path)

    assert loader.status == STATUS_UNAVAILABLE
    assert "ARTIFACT_MISSING" in loader.status_reason

    # Attempt inference: must NOT crash and must NOT return fake fallback 0.12 or 28.4
    res = loader.predict_operational_attention({"duty_hours_7d": 40.0})
    assert res["availability_status"] == STATUS_UNAVAILABLE
    assert res["calibrated_probability"] is None
    assert res["predicted_class"] is None
    assert res["operational_strain_score"] is None
    assert res["operational_attention_band"] == STATUS_UNAVAILABLE
    assert res["confidence_score"] == 0.0


def test_corrupt_artifact_sets_model_unavailable():
    """Verify that a corrupted artifact file safely sets MODEL_UNAVAILABLE."""
    with tempfile.TemporaryDirectory() as tmpdir:
        corrupt_path = Path(tmpdir) / "corrupt_artifact.joblib"
        corrupt_path.write_text("THIS IS NOT A VALID JOBLIB ARCHIVE")

        loader = ModelARuntimeLoader(corrupt_path)
        assert loader.status == STATUS_UNAVAILABLE
        assert "ARTIFACT_CORRUPT" in loader.status_reason

        res = loader.predict_operational_attention({"duty_hours_7d": 40.0})
        assert res["calibrated_probability"] is None


def test_wrong_target_version_sets_model_unavailable():
    """Verify that an artifact with mismatched target_version is rejected."""
    valid_art = load_model_a_artifact(DEFAULT_ARTIFACT_PATH)
    mutated = dict(valid_art)
    mutated["target_version"] = "v999.0-incompatible-target"

    with tempfile.TemporaryDirectory() as tmpdir:
        bad_art_path = Path(tmpdir) / "bad_target_artifact.joblib"
        joblib.dump(mutated, bad_art_path)

        with patch("app.ml.runtime_loader.joblib.load", side_effect=AssertionError("Unapproved bytes must not be deserialized")):
            loader = ModelARuntimeLoader(bad_art_path)
        assert loader.status == STATUS_UNAVAILABLE
        # Stage-3 hash-first contract rejects mutated bytes before reading metadata.
        assert "checksum mismatch" in loader.status_reason


def test_wrong_feature_version_sets_model_unavailable():
    """Verify that an artifact with mismatched feature_spec_version is rejected."""
    valid_art = load_model_a_artifact(DEFAULT_ARTIFACT_PATH)
    mutated = dict(valid_art)
    mutated["feature_spec_version"] = "v999.0-incompatible-features"

    with tempfile.TemporaryDirectory() as tmpdir:
        bad_art_path = Path(tmpdir) / "bad_feat_artifact.joblib"
        joblib.dump(mutated, bad_art_path)

        with patch("app.ml.runtime_loader.joblib.load", side_effect=AssertionError("Unapproved bytes must not be deserialized")):
            loader = ModelARuntimeLoader(bad_art_path)
        assert loader.status == STATUS_UNAVAILABLE
        assert "checksum mismatch" in loader.status_reason


def test_valid_inference_execution_and_personnel_differentiation():
    """Verify inference produces valid predictions and differentiates between distinct personnel profiles."""
    loader = ModelARuntimeLoader(DEFAULT_ARTIFACT_PATH)
    assert loader.status == STATUS_AVAILABLE

    # Low workload profile
    low_profile = {fn: 5.0 for fn in FEATURE_SET_B}
    low_profile["min_rest_hours_14d"] = 8.0
    low_profile["avg_rest_hours_30d"] = 8.0

    res_low = loader.predict_operational_attention(low_profile)
    assert res_low["availability_status"] == STATUS_AVAILABLE
    assert res_low["calibrated_probability"] is not None
    assert 0.0 <= res_low["calibrated_probability"] <= 1.0
    assert res_low["operational_strain_score"] is not None
    assert res_low["confidence_score"] > 0.80

    # High workload profile
    high_profile = {fn: 80.0 for fn in FEATURE_SET_B}
    high_profile["duty_hours_30d"] = 300.0
    high_profile["min_rest_hours_14d"] = 1.0
    high_profile["avg_rest_hours_30d"] = 2.0
    high_profile["consecutive_duty_days"] = 15.0

    res_high = loader.predict_operational_attention(high_profile)
    assert res_high["availability_status"] == STATUS_AVAILABLE
    assert res_high["calibrated_probability"] is not None
    assert res_high["calibrated_probability"] > res_low["calibrated_probability"]
    assert res_high["operational_strain_score"] > res_low["operational_strain_score"]

    # Verify explainability returned
    assert res_high["primary_driver"] is not None
    assert len(res_high["top_operational_drivers"]) > 0


def test_analytics_prediction_adapter_delegation():
    """Verify that app.analytics.prediction.predictor delegates to model_a_runtime."""
    from app.analytics.prediction import predictor

    sample = {fn: 15.0 for fn in FEATURE_SET_B}
    res = predictor.predict_one(sample)
    assert res["status"] == STATUS_AVAILABLE
    assert res["probability"] is not None
    assert res["probability"] != 0.12  # Ensure legacy 0.12 is NEVER returned
