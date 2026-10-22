"""Frozen Model-A GovernedPreprocessor: runtime transform/predict only.

Original module identity is required by the approved artifact. Offline fitting
subclasses live in tools.training; these classes cannot train or persist models.
"""
from typing import Any, Dict, List, Optional, Sequence, Union
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from app.ml.features_hr import MODEL_A_FEATURE_NAMES


class GovernedPreprocessor(BaseEstimator, TransformerMixin):
    def __init__(
        self,
        expected_features: Optional[Sequence[str]] = None,
        impute_strategy: str = "median",
        with_missing_indicator: bool = True,
        with_scaling: bool = True,
    ):
        self.expected_features: List[str] = list(expected_features or MODEL_A_FEATURE_NAMES)
        self.impute_strategy: str = impute_strategy
        self.with_missing_indicator: bool = with_missing_indicator
        self.with_scaling: bool = with_scaling

        self.imputer_: Optional[SimpleImputer] = None
        self.scaler_: Optional[StandardScaler] = None
        self.feature_names_out_: List[str] = []
        self.is_fitted_: bool = False

    def _validate_columns(self, X: Union[pd.DataFrame, Dict[str, Any]]) -> pd.DataFrame:
        """Enforces column presence and exact canonical ordering."""
        if isinstance(X, dict):
            X = pd.DataFrame([X])
        elif not isinstance(X, pd.DataFrame):
            X = pd.DataFrame(X, columns=self.expected_features)

        missing = [c for c in self.expected_features if c not in X.columns]
        if missing:
            raise ValueError(f"Missing required features for governed preprocessing: {missing}")

        # Reorder strictly according to expected_features
        return X[self.expected_features].copy()

    def transform(self, X: pd.DataFrame) -> np.ndarray:
        """Transforms input features using fitted imputer and scaler."""
        if not self.is_fitted_ or self.imputer_ is None:
            raise RuntimeError("GovernedPreprocessor must be fitted before transform.")

        df_ordered = self._validate_columns(X)
        X_imputed = self.imputer_.transform(df_ordered.values)

        if self.scaler_ is not None:
            return self.scaler_.transform(X_imputed)
        return X_imputed

    def transform_df(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transforms features and returns DataFrame with explicit column names."""
        arr = self.transform(X)
        return pd.DataFrame(arr, columns=self.feature_names_out_)

    def get_feature_names_out(self, input_features: Optional[Any] = None) -> List[str]:
        if not self.is_fitted_:
            raise RuntimeError("GovernedPreprocessor must be fitted to get feature names out.")
        return list(self.feature_names_out_)
