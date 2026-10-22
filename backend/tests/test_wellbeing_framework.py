"""Tests for Engine-B Generic Wellbeing Instrument Contract & Framework."""

from datetime import date
import pytest
from app.ml.wellbeing_framework import (
    ATTENTION_ROUTINE,
    ATTENTION_UNAVAILABLE,
    BaseInstrumentAdapter,
    DerivedWellbeingResult,
    GLOBAL_INSTRUMENT_REGISTRY,
    GenericUnactivatedAdapter,
    InstrumentItemSpec,
    InstrumentRegistry,
    RawResponseValidationResult,
    STATUS_AVAILABLE,
    STATUS_NOT_ACTIVATED,
    TREND_INSUFFICIENT_HISTORY,
)


def test_unregistered_instrument_defaults_to_unactivated():
    """Unregistered or unapproved instrument must return unactivated adapter."""
    registry = InstrumentRegistry()
    adapter = registry.get("SOME_UNKNOWN_INSTRUMENT", "1.0")

    assert isinstance(adapter, GenericUnactivatedAdapter)
    assert adapter.is_activated is False
    assert adapter.instrument_id == "SOME_UNKNOWN_INSTRUMENT"

    val = adapter.validate_responses({"q1": 1})
    assert val.is_valid is False
    assert any("not canonically activated" in err for err in val.errors)

    res = adapter.derive_result({"q1": 1}, assessment_date=date(2026, 10, 1))
    assert res.status == STATUS_NOT_ACTIVATED
    assert res.attention_category == ATTENTION_UNAVAILABLE
    assert res.summary_scores == {}
    # Ensure raw answers are NOT inside derived result
    d = res.to_dict()
    assert "q1" not in d
    assert "answers" not in d


def test_generic_mock_instrument_adapter_implementation():
    """Demonstrates that the framework hosts generic non-clinical instruments cleanly."""

    class MockOperationalCheckAdapter(BaseInstrumentAdapter):
        @property
        def instrument_id(self) -> str:
            return "OPERATIONAL_READINESS_CHECK"

        @property
        def instrument_version(self) -> str:
            return "1.0"

        @property
        def scoring_version(self) -> str:
            return "v1-deterministic"

        @property
        def is_activated(self) -> bool:
            return True

        def get_item_specs(self):
            return [
                InstrumentItemSpec("rest_perceived", "Perceived rest adequacy", "int", 1, 5, is_required=True),
                InstrumentItemSpec("workload_perceived", "Perceived shift pace", "int", 1, 5, is_required=True),
            ]

        def validate_responses(self, answers):
            specs = {s.item_id: s for s in self.get_item_specs()}
            missing = [k for k, s in specs.items() if s.is_required and k not in answers]
            unknown = [k for k in answers if k not in specs]
            errors = []
            for k, v in answers.items():
                if k in specs:
                    s = specs[k]
                    if not (s.min_value <= v <= s.max_value):
                        errors.append(f"{k} out of range")
            is_valid = len(missing) == 0 and len(errors) == 0
            completeness = (len(specs) - len(missing)) / len(specs) if specs else 0.0
            return RawResponseValidationResult(
                is_valid=is_valid,
                errors=errors,
                missing_items=missing,
                unknown_items=unknown,
                completeness_ratio=completeness,
            )

        def derive_result(self, answers, assessment_date, prior_results=None):
            val = self.validate_responses(answers)
            if not val.is_valid:
                return DerivedWellbeingResult(
                    instrument_id=self.instrument_id,
                    instrument_version=self.instrument_version,
                    scoring_version=self.scoring_version,
                    assessment_date=assessment_date,
                    status="INVALID_RESPONSE",
                    notes="; ".join(val.errors),
                )
            # Simple non-clinical average score
            avg_score = (answers["rest_perceived"] + answers["workload_perceived"]) / 2.0
            return DerivedWellbeingResult(
                instrument_id=self.instrument_id,
                instrument_version=self.instrument_version,
                scoring_version=self.scoring_version,
                assessment_date=assessment_date,
                status=STATUS_AVAILABLE,
                summary_scores={"average_rating": avg_score},
                attention_category=ATTENTION_ROUTINE,
                confidence_score=val.completeness_ratio,
            )

    registry = InstrumentRegistry()
    mock_adapter = MockOperationalCheckAdapter()
    registry.register(mock_adapter)

    retrieved = registry.get("OPERATIONAL_READINESS_CHECK", "1.0")
    assert retrieved.is_activated is True

    # Valid response
    res = retrieved.derive_result({"rest_perceived": 4, "workload_perceived": 3}, date(2026, 10, 1))
    assert res.status == STATUS_AVAILABLE
    assert res.summary_scores["average_rating"] == 3.5
    assert res.attention_category == ATTENTION_ROUTINE
    # Zero raw answer leakage in dictionary serialization
    res_dict = res.to_dict()
    assert "rest_perceived" not in res_dict
    assert "workload_perceived" not in res_dict


def test_derived_result_serialization_strictly_omits_raw_answers():
    """Verify DerivedWellbeingResult does not contain raw answers payload."""
    res = DerivedWellbeingResult(
        instrument_id="GENERIC_CHECK",
        instrument_version="1.0",
        scoring_version="v1",
        assessment_date=date(2026, 10, 1),
        status=STATUS_AVAILABLE,
        summary_scores={"derived_index": 72.5},
        attention_category=ATTENTION_ROUTINE,
    )
    d = res.to_dict()
    assert "answers" not in d
    assert "answers_json" not in d
    assert d["summary_scores"] == {"derived_index": 72.5}
    assert d["status"] == STATUS_AVAILABLE


def test_task_b07_raw_response_validation_boundaries():
    """Verify Task B07 raw response validation boundaries."""
    from app.ml.wellbeing_framework import validate_raw_responses_against_spec

    specs = [
        InstrumentItemSpec(item_id="q1", item_label="Item 1", value_type="int", min_value=0, max_value=4, is_required=True),
        InstrumentItemSpec(item_id="q2", item_label="Item 2", value_type="int", min_value=0, max_value=4, is_required=True),
        InstrumentItemSpec(item_id="q3", item_label="Item 3", value_type="choice", allowed_choices=["YES", "NO"], is_required=False),
    ]

    # Case 1: Missing required item
    res_missing = validate_raw_responses_against_spec(specs, {"q1": 2})
    assert res_missing.is_valid is False
    assert "q2" in res_missing.missing_items
    assert res_missing.completeness_ratio == 0.5

    # Case 2: Unknown item
    res_unknown = validate_raw_responses_against_spec(specs, {"q1": 2, "q2": 3, "unregistered_field": "val"})
    assert res_unknown.is_valid is False
    assert "unregistered_field" in res_unknown.unknown_items

    # Case 3: Out of range (value > max_value)
    res_oor = validate_raw_responses_against_spec(specs, {"q1": 5, "q2": 2})
    assert res_oor.is_valid is False
    assert any("exceeds maximum allowed 4" in err for err in res_oor.errors)

    # Case 4: Type mismatch (string given for int)
    res_type = validate_raw_responses_against_spec(specs, {"q1": "invalid_str", "q2": 2})
    assert res_type.is_valid is False
    assert any("must be numeric" in err for err in res_type.errors)

    # Case 5: Boolean given for int
    res_bool = validate_raw_responses_against_spec(specs, {"q1": True, "q2": 2})
    assert res_bool.is_valid is False
    assert any("must be numeric" in err for err in res_bool.errors)

    # Case 6: Non-finite value
    res_nan = validate_raw_responses_against_spec(specs, {"q1": float("nan"), "q2": 2})
    assert res_nan.is_valid is False
    assert any("non-finite" in err for err in res_nan.errors)

    # Case 7: Invalid choice
    res_choice = validate_raw_responses_against_spec(specs, {"q1": 2, "q2": 2, "q3": "MAYBE"})
    assert res_choice.is_valid is False
    assert any("not in allowed choices" in err for err in res_choice.errors)

    # Case 8: Perfectly valid
    res_valid = validate_raw_responses_against_spec(specs, {"q1": 2, "q2": 3, "q3": "YES"})
    assert res_valid.is_valid is True
    assert len(res_valid.errors) == 0
    assert res_valid.completeness_ratio == 1.0


def test_task_b09_derived_result_engine_unactivated_and_truthful():
    """Verify Task B09: Derived result engine handles unactivated instruments truthfully without fabricating scores."""
    from app.ml.wellbeing_framework import GenericUnactivatedAdapter, STATUS_NOT_ACTIVATED, ATTENTION_UNAVAILABLE

    adapter = GenericUnactivatedAdapter(instrument_id="UNAPPROVED_QUESTIONNAIRE", instrument_version="1.0")
    today = date(2026, 10, 4)

    # Submitting arbitrary answers to an unactivated adapter
    derived = adapter.derive_result(
        answers={"q1": 3, "q2": 4},
        assessment_date=today,
    )

    # 1. Truthful explicit state
    assert derived.status == STATUS_NOT_ACTIVATED
    assert derived.attention_category == ATTENTION_UNAVAILABLE
    assert derived.confidence_score == 0.0

    # 2. Absolutely NO fabricated scores
    assert derived.summary_scores == {}

    # 3. Raw answers strictly omitted from derived object
    d = derived.to_dict()
    assert "q1" not in d
    assert "q2" not in d
    assert "answers" not in d
    assert "answers_json" not in d
    assert d["status"] == STATUS_NOT_ACTIVATED


def test_task_b16_private_wellbeing_trend_engine():
    """Verify Task B16 trend engine handles insufficient history, instrument changes, and stable/improving/declining trends."""
    from app.ml.wellbeing_framework import (
        compute_private_wellbeing_trend,
        DerivedWellbeingResult,
        STATUS_AVAILABLE,
        STATUS_NOT_ACTIVATED,
        TREND_STABLE,
        TREND_IMPROVING,
        TREND_DECLINING,
        TREND_INSUFFICIENT_HISTORY,
    )

    d1 = date(2026, 9, 1)
    d2 = date(2026, 9, 15)
    d3 = date(2026, 10, 1)

    # 1. Single assessment -> INSUFFICIENT_HISTORY
    res1 = DerivedWellbeingResult("INST_A", "1.0", "v1", d1, STATUS_AVAILABLE, {"recovery_score": 60.0})
    trend, diag = compute_private_wellbeing_trend([res1])
    assert trend == TREND_INSUFFICIENT_HISTORY
    assert "INSUFFICIENT_ASSESSMENTS" in diag["reason"]

    # 2. Incomparable instruments (INST_A -> INST_B) -> INSUFFICIENT_HISTORY across boundary
    res2_diff = DerivedWellbeingResult("INST_B", "1.0", "v1", d2, STATUS_AVAILABLE, {"recovery_score": 75.0})
    trend, diag = compute_private_wellbeing_trend([res1, res2_diff])
    assert trend == TREND_INSUFFICIENT_HISTORY
    assert "INSTRUMENT_BOUNDARY_INCOMPARABLE" in diag["reason"]

    # 3. Two homogeneous assessments improving
    res2_same = DerivedWellbeingResult("INST_A", "1.0", "v1", d2, STATUS_AVAILABLE, {"recovery_score": 70.0})
    trend, diag = compute_private_wellbeing_trend([res1, res2_same])
    assert trend == TREND_IMPROVING
    assert diag["delta"] == 10.0

    # 4. Declining trend
    res3_decline = DerivedWellbeingResult("INST_A", "1.0", "v1", d3, STATUS_AVAILABLE, {"recovery_score": 50.0})
    trend, diag = compute_private_wellbeing_trend([res2_same, res3_decline])
    assert trend == TREND_DECLINING
    assert diag["delta"] == -20.0

    # 5. Stable trend within tolerance (delta = 1.0 <= 2.0)
    res3_stable = DerivedWellbeingResult("INST_A", "1.0", "v1", d3, STATUS_AVAILABLE, {"recovery_score": 71.0})
    trend, diag = compute_private_wellbeing_trend([res2_same, res3_stable], tolerance=2.0)
    assert trend == TREND_STABLE
    assert diag["delta"] == 1.0

    # 6. Unactivated assessment returns explicit INSTRUMENT_NOT_ACTIVATED
    res_invalid = DerivedWellbeingResult("INST_A", "1.0", "v1", d3, STATUS_NOT_ACTIVATED, {})
    trend, diag = compute_private_wellbeing_trend([res1, res_invalid])
    assert trend == STATUS_NOT_ACTIVATED

    # 7. Legacy ungoverned assessments cannot generate governed trend
    from app.ml.wellbeing_framework import TREND_INSUFFICIENT_GOVERNED_HISTORY
    res_legacy1 = DerivedWellbeingResult("LEGACY", "1.0", "v1", d1, STATUS_AVAILABLE, {"score": 50.0}, is_governed=False, processing_version="legacy")
    res_legacy2 = DerivedWellbeingResult("LEGACY", "1.0", "v1", d2, STATUS_AVAILABLE, {"score": 60.0}, is_governed=False, processing_version="legacy")
    trend_leg, diag_leg = compute_private_wellbeing_trend([res_legacy1, res_legacy2])
    assert trend_leg == TREND_INSUFFICIENT_GOVERNED_HISTORY
    assert "LEGACY_UNGOVERNED_HISTORY" in diag_leg["reason"]
