"""Required evidence gates preserve truthful unavailable and optional states."""
from datetime import date
import pytest
from app.analytics.attention import evaluate_attention


@pytest.mark.parametrize("status", ["NOT_COMPUTED", "DATA_STALE", "INSUFFICIENT_HISTORY", "COMPUTATION_ERROR"])
def test_missing_or_invalid_wsi_never_becomes_low(status):
    result = evaluate_attention({"wsi":{"status":status,"reason_codes":["SOURCE_UNAVAILABLE"]}},
        {"prediction_date":date(2026,3,15),"risk_level":"HIGH"})
    assert result["status"] == status and result["band"] is None


def test_current_evidence_optional_missing_model_and_stale_cutoff():
    analytics = {"wsi":{"status":"VALID", "as_of":"2026-03-15"},
        "baseline":{"status":"INSUFFICIENT_HISTORY"},"trend":{"status":"INSUFFICIENT_HISTORY"},
        "peer":{"status":"NOT_COMPUTED"}}
    assert evaluate_attention(analytics, None)["status"] == "MODEL_UNAVAILABLE"
    assert evaluate_attention(analytics, {"prediction_date":date(2026,3,14),"risk_level":"HIGH"})["status"] == "DATA_STALE"
    assert evaluate_attention(analytics, {"prediction_date":date(2026,3,15),"risk_level":"HIGH"})["band"] == "HIGH"
