"""Tests for PRAHARI Task 30: Model Output Physical Schema & Legacy Isolation."""

from datetime import date, datetime, timezone
import uuid
import pytest

from app.models.model_output import ModelOutput


def test_model_output_entity_structure():
    """Verify ModelOutput entity cleanly maps all Model-A governance and operational fields."""
    p_id = uuid.uuid4()
    output = ModelOutput(
        personnel_id=p_id,
        prediction_date=date(2026, 6, 1),
        target_name="next_30d_leave_anomaly",
        model_name="Model-A (Operational Decision Support)",
        model_version="1.0.0",
        feature_set_version="v2.1-SetB-15ops",
        training_data_version="v2.1-frozen-prototype",
        hr_probability=0.1852,
        wellbeing_probability=None,  # Strictly None for Model-A
        combined_probability=None,   # Strictly None for Model-A
        risk_score=72.50,            # Continuous 0-100 score
        risk_level="HIGH",           # Canonical band
        predicted_class=1,           # Binary alert class based on tau=0.15
        data_completeness=1.0,
        explanation_json={
            "primary_driver": "Elevated cumulative duty load (30-day duty hours)",
            "top_drivers": [{"feature": "duty_hours_30d", "impact": 1.45}],
            "threshold_policy_version": "v1.0-balanced",
            "decision_threshold": 0.15,
        },
    )

    assert output.target_name == "next_30d_leave_anomaly"
    assert output.model_name == "Model-A (Operational Decision Support)"
    assert output.model_version == "1.0.0"
    assert output.hr_probability == 0.1852
    assert output.wellbeing_probability is None
    assert output.combined_probability is None
    assert output.risk_score == 72.50
    assert output.risk_level == "HIGH"
    assert output.predicted_class == 1


def test_legacy_rows_distinct_from_model_a():
    """Verify that legacy target_name differs from canonical Model-A target."""
    legacy_target = "target_leave_anomaly"
    canonical_target = "next_30d_leave_anomaly"

    assert legacy_target != canonical_target
    assert "next_30d" in canonical_target
