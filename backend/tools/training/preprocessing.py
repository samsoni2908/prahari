"""Offline fitting and serialization; inference implementation is in app.ml.preprocessing."""
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union
import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from app.ml.features_hr import MODEL_A_FEATURE_NAMES

from app.ml.preprocessing import GovernedPreprocessor as RuntimeGovernedPreprocessor

class GovernedPreprocessor(RuntimeGovernedPreprocessor):
    def fit(self, X: pd.DataFrame, y: Optional[Any] = None) -> "GovernedPreprocessor":
        """Fits imputer and scaler on training features."""
        df_ordered = self._validate_columns(X)

        # 1. Fit Imputer with explicit missing indicators
        self.imputer_ = SimpleImputer(
            strategy=self.impute_strategy,
            add_indicator=self.with_missing_indicator,
        )
        X_imputed = self.imputer_.fit_transform(df_ordered.values)

        # 2. Determine output feature names
        out_names = list(self.expected_features)
        if self.with_missing_indicator and self.imputer_.indicator_ is not None:
            ind_indices = self.imputer_.indicator_.features_
            for idx in ind_indices:
                out_names.append(f"{self.expected_features[idx]}_missing")
        self.feature_names_out_ = out_names

        # 3. Fit Scaler if enabled
        if self.with_scaling:
            self.scaler_ = StandardScaler()
            self.scaler_.fit(X_imputed)
        else:
            self.scaler_ = None

        self.is_fitted_ = True
        return self

    def fit_transform(self, X: pd.DataFrame, y: Optional[Any] = None) -> np.ndarray:
        return self.fit(X, y).transform(X)

    def save(self, filepath: Union[str, Path]) -> None:
        """Serializes fitted pipeline to disk."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "GovernedPreprocessor":
        """Loads serialized pipeline from disk."""
        obj = joblib.load(filepath)
        if not isinstance(obj, cls):
            raise TypeError(f"Loaded object is of type {type(obj)}, expected {cls}.")
        return obj


def create_governed_pipeline(
    features: Optional[Sequence[str]] = None,
) -> GovernedPreprocessor:
    """Factory creating a standard governed preprocessor for Model-A."""
    return GovernedPreprocessor(expected_features=features)

__all__ = [
    "GovernedPreprocessor",
    "create_governed_pipeline",
]
