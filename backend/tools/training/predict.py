"""PRAHARI Model-A Inference Entrypoint.

Task 29 Compliance:
- Zero Hardcoded Fallbacks: Never returns fake 28.4 risk score or fake LOW risk.
- Governed Model-A Runtime: Consumes persisted, approved artifact via ModelARuntimeLoader.
"""

from typing import Any, Dict, Optional
from app.ml.runtime_loader import model_a_runtime


def predict_operational_attention(
    feature_dict: Dict[str, Any],
    personnel_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Runs Model-A operational attention inference for personnel."""
    res = model_a_runtime.predict_operational_attention(feature_dict)
    if personnel_id:
        res["personnel_id"] = str(personnel_id)
    return res


# Compatibility helper with updated non-fallback behavior
def predict_risk(personnel_id: str, feature_dict: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Legacy interface updated to remove hardcoded 28.4 fallback."""
    if feature_dict is None:
        feature_dict = {}
    return predict_operational_attention(feature_dict, personnel_id=personnel_id)
