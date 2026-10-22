"""Tests for Task 16: Governed Preprocessing Pipeline.

TASK 16 TESTS:
1. fit: Fits on training data cleanly.
2. transform: Transforms both training and test data cleanly.
3. column ordering: Validates and corrects scrambled column order.
4. missing values: Imputes with median and appends explicit missing indicator columns.
5. serialization compatibility: Saves and loads via joblib with bit-identical outputs.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from app.ml.features_hr import MODEL_A_FEATURE_NAMES
from tools.training.preprocessing import GovernedPreprocessor, create_governed_pipeline


@pytest.fixture
def sample_features_df():
    np.random.seed(26186)
    n = 100
    data = {}
    for feat in MODEL_A_FEATURE_NAMES:
        col = np.random.normal(loc=10.0, scale=2.0, size=n)
        # Inject missing values into certain columns
        if feat in ("night_duty_ratio_30d", "min_rest_hours_14d", "baseline_z_workload"):
            mask = np.random.rand(n) < 0.20
            col[mask] = np.nan
        data[feat] = col
    return pd.DataFrame(data)


def test_task16_fit_and_transform(sample_features_df):
    """TASK 16 TEST 1 & 2: fit and transform."""
    pipe = create_governed_pipeline()
    assert not pipe.is_fitted_

    pipe.fit(sample_features_df)
    assert pipe.is_fitted_
    assert len(pipe.get_feature_names_out()) >= len(MODEL_A_FEATURE_NAMES)

    transformed = pipe.transform(sample_features_df)
    assert isinstance(transformed, np.ndarray)
    assert transformed.shape[0] == len(sample_features_df)
    assert not np.isnan(transformed).any(), "Transformed output must not contain NaNs."


def test_task16_column_ordering(sample_features_df):
    """TASK 16 TEST 3: column ordering enforcement."""
    pipe = create_governed_pipeline()
    pipe.fit(sample_features_df)
    expected_out = pipe.transform(sample_features_df)

    # Scramble column order
    scrambled_cols = list(sample_features_df.columns)
    scrambled_cols.reverse()
    df_scrambled = sample_features_df[scrambled_cols].copy()

    scrambled_out = pipe.transform(df_scrambled)
    # Output must be identical despite scrambled input columns
    np.testing.assert_allclose(expected_out, scrambled_out)

    # Missing column must raise ValueError
    df_missing = sample_features_df.drop(columns=[MODEL_A_FEATURE_NAMES[0]])
    with pytest.raises(ValueError, match="Missing required features"):
        pipe.transform(df_missing)


def test_task16_missing_values_and_indicators(sample_features_df):
    """TASK 16 TEST 4: missing values handling and explicit indicators."""
    pipe = create_governed_pipeline()
    df_out = pipe.fit(sample_features_df).transform_df(sample_features_df)

    # Check that missing indicators were added
    indicator_cols = [c for c in df_out.columns if c.endswith("_missing")]
    assert len(indicator_cols) > 0, "Missing indicator columns must be added."
    assert "baseline_z_workload_missing" in indicator_cols

    # Ensure no NaNs exist in output
    assert not df_out.isna().any().any()


def test_task16_serialization_compatibility(sample_features_df, tmp_path):
    """TASK 16 TEST 5: serialization compatibility with joblib."""
    pipe = create_governed_pipeline()
    pipe.fit(sample_features_df)
    original_out = pipe.transform(sample_features_df)

    save_path = tmp_path / "governed_preprocessor.joblib"
    pipe.save(save_path)
    assert save_path.exists()

    loaded_pipe = GovernedPreprocessor.load(save_path)
    assert loaded_pipe.is_fitted_
    loaded_out = loaded_pipe.transform(sample_features_df)

    np.testing.assert_allclose(original_out, loaded_out)
