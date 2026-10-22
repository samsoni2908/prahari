"""Offline fitting and serialization; inference implementation is in app.ml.calibrate."""
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
import joblib
import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import brier_score_loss

from app.ml.calibrate import GovernedCalibrator as RuntimeGovernedCalibrator

class GovernedCalibrator(RuntimeGovernedCalibrator):
    def fit(self, X_train: np.ndarray, y_train: np.ndarray) -> "GovernedCalibrator":
        """Fits calibration on training data using internal cross-validation."""
        self.calibrated_classifier_ = CalibratedClassifierCV(
            estimator=self.base_estimator,
            method=self.method,
            cv=self.cv,
        )
        self.calibrated_classifier_.fit(X_train, y_train)
        self.is_fitted_ = True
        return self

    def save(self, filepath: Union[str, Path]) -> None:
        """Serializes calibrated model to disk."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "GovernedCalibrator":
        """Loads serialized calibrated model from disk."""
        obj = joblib.load(filepath)
        if not isinstance(obj, cls):
            raise TypeError(f"Loaded object is of type {type(obj)}, expected {cls}.")
        return obj


def calculate_brier_score(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """Computes Brier score loss: lower is better calibrated."""
    return float(brier_score_loss(y_true, y_prob))

def calibrate_and_evaluate(
    base_estimator: BaseEstimator,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    method: str = "sigmoid",
    cv: int = 3,
) -> Tuple[GovernedCalibrator, Dict[str, Any]]:
    """Fits calibrator on training data and computes Brier score comparison on validation set."""
    # 1. Evaluate uncalibrated model
    base_estimator.fit(X_train, y_train)
    uncal_probs = base_estimator.predict_proba(X_val)[:, 1]
    uncal_brier = calculate_brier_score(y_val, uncal_probs)

    # 2. Fit and evaluate calibrated model
    calibrator = GovernedCalibrator(base_estimator=base_estimator, method=method, cv=cv)
    calibrator.fit(X_train, y_train)
    cal_probs = calibrator.predict_proba(X_val)[:, 1]
    cal_brier = calculate_brier_score(y_val, cal_probs)

    report = {
        "calibration_method": f"{method} (Platt scaling)",
        "uncalibrated_brier": round(uncal_brier, 4),
        "calibrated_brier": round(cal_brier, 4),
        "brier_improvement": round(uncal_brier - cal_brier, 4),
        "probabilities_min": round(float(cal_probs.min()), 4),
        "probabilities_max": round(float(cal_probs.max()), 4),
    }

    return calibrator, report

__all__ = [
    "calculate_brier_score",
    "GovernedCalibrator",
    "calibrate_and_evaluate",
]
