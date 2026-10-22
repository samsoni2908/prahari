"""Locked V1 operational rules: valid WSI plus governed Model-A risk evidence.

Baseline/trend/peer remain disclosed optional evidence. No numeric fusion,
clinical/private predicates, or reinterpretation of missing signals as LOW.
"""
POLICY = "OPERATIONAL_ATTENTION_POLICY_V1_SYNTHETIC_DEMO"


def evaluate_attention(analytics, prediction):
    wsi = analytics["wsi"]
    result = {"status": "NOT_COMPUTED", "band": None, "policy_version": POLICY,
        "reason_codes": [], "required_signals": ["wsi", "model_a"],
        "optional_signals": ["baseline", "trend", "peer"]}
    if wsi["status"] != "VALID":
        return {**result, "status": wsi["status"], "reason_codes": wsi["reason_codes"]}
    if prediction is None:
        return {**result, "status": "MODEL_UNAVAILABLE", "reason_codes": ["MODEL_A_UNAVAILABLE"]}
    if prediction["prediction_date"].isoformat() != wsi["as_of"]:
        return {**result, "status": "DATA_STALE", "reason_codes": ["SIGNAL_CUTOFF_MISMATCH"]}
    if prediction.get("risk_level") not in ("LOW", "MEDIUM", "HIGH"):
        return {**result, "status": "COMPUTATION_ERROR", "reason_codes": ["INVALID_MODEL_A_BAND"]}
    return {**result, "status": "VALID", "band": prediction["risk_level"]}
