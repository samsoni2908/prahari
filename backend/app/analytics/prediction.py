"""PRAHARI Operational Prediction Adapter.

Task 28 & 29 Compliance:
- RUNTIME NEVER TRAINS: Delegates strictly to pre-trained, validated Model-A artifact.
- Zero Hardcoded Fallbacks: Never returns fake 0.12 probability or fake LOW risk.
- Explicit Availability States: Returns MODEL_UNAVAILABLE if artifact is missing or invalid.
"""

from typing import Any, Dict, List, Optional
from app.ml.features_hr import FEATURE_SET_B
from app.ml.runtime_loader import model_a_runtime, STATUS_AVAILABLE, STATUS_UNAVAILABLE

FEATURE_NAMES = list(FEATURE_SET_B)


class LeaveAnomalyPredictor:
    """Compatibility adapter for Model-A runtime inference."""

    def __init__(self):
        self.feature_names = FEATURE_NAMES
        self.runtime = model_a_runtime

    @property
    def is_trained(self) -> bool:
        return self.runtime.status == STATUS_AVAILABLE

    def predict_one(self, feature_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Runs governed Model-A runtime inference for single feature dictionary."""
        res = self.runtime.predict_operational_attention(feature_dict)
        if res["availability_status"] != STATUS_AVAILABLE:
            return {
                "status": STATUS_UNAVAILABLE,
                "probability": None,
                "predicted_class": None,
                "operational_score": None,
                "operational_band": STATUS_UNAVAILABLE,
                "explanation": {
                    "primary_driver": None,
                    "top_drivers": [],
                    "model_type": "Model-A (Calibrated Logistic Regression)",
                    "status": STATUS_UNAVAILABLE,
                },
            }

        return {
            "status": STATUS_AVAILABLE,
            "probability": res["calibrated_probability"],
            "predicted_class": res["predicted_class"],
            "operational_score": res["operational_strain_score"],
            "operational_band": res["operational_attention_band"],
            "explanation": {
                "primary_driver": res["primary_driver"],
                "top_drivers": res["top_operational_drivers"],
                "protective_factors": res["protective_factors"],
                "model_type": "Model-A (Calibrated Logistic Regression)",
                "status": STATUS_AVAILABLE,
            },
            "confidence_score": res["confidence_score"],
            "confidence_descriptor": res["confidence_descriptor"],
        }


# Singleton instance
predictor = LeaveAnomalyPredictor()

__all__ = [
    "FEATURE_NAMES",
    "LeaveAnomalyPredictor",
    "predictor",
]
