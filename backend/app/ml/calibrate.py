"""Frozen Model-A GovernedCalibrator: runtime transform/predict only.

Original module identity is required by the approved artifact. Offline fitting
subclasses live in tools.training; these classes cannot train or persist models.
"""
from typing import Optional
import numpy as np
from sklearn.base import BaseEstimator
from sklearn.calibration import CalibratedClassifierCV


class GovernedCalibrator:
    def __init__(
        self,
        base_estimator: BaseEstimator,
        method: str = "sigmoid",
        cv: int = 3,
    ):
        self.base_estimator = base_estimator
        self.method = method
        self.cv = cv
        self.calibrated_classifier_: Optional[CalibratedClassifierCV] = None
        self.is_fitted_: bool = False

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Returns calibrated class probabilities."""
        if not self.is_fitted_ or self.calibrated_classifier_ is None:
            raise RuntimeError("GovernedCalibrator must be fitted before predict_proba.")
        probs = self.calibrated_classifier_.predict_proba(X)
        # Guarantee probabilities in [0.0, 1.0]
        return np.clip(probs, 0.0, 1.0)

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        """Returns binary predictions based on decision threshold."""
        prob_pos = self.predict_proba(X)[:, 1]
        return (prob_pos >= threshold).astype(int)
