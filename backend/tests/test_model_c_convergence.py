"""Tests for PRAHARI Model-C Governed Evidence Convergence Engine.

Validates truthful-state semantics, domain separation, and privacy firewalls.
Canonical Specification: docs/ml.md §§ 20–23, 25; rules.md; prd.md.
"""

from datetime import date
import pytest

from app.ml.convergence import (
    CONVERGENCE_FRAMEWORK_VERSION,
    CONVERGENCE_RULES_VERSION,
    SOURCE_AVAILABLE,
    SOURCE_INSUFFICIENT_HISTORY,
    SOURCE_MODEL_UNAVAILABLE,
    SOURCE_NOT_ACTIVATED,
    SOURCE_NOT_SHARED,
    SOURCE_PROCESSING_ERROR,
    SOURCE_UNAVAILABLE,
    STATE_CONVERGENCE_UNAVAILABLE,
    STATE_CONVERGING_EVIDENCE,
    STATE_NO_ELEVATED_EVIDENCE,
    STATE_OPERATIONAL_EVIDENCE_ONLY,
    STATE_PRIVATE_EVIDENCE_ONLY,
    EvidenceConvergenceResult,
    OperationalEvidenceSource,
    PrivateWellbeingEvidenceSource,
    evaluate_evidence_convergence,
)


def test_case_1_op_low_and_b_not_shared_emits_operational_only():
    """TRUTHFUL-STATE TEST 1:

    When A is routine/LOW and B is NOT_SHARED, convergence MUST NOT emit
    NO_ELEVATED_EVIDENCE because Source B was never evaluated.
    It MUST emit OPERATIONAL_EVIDENCE_ONLY with operational_attention == 'LOW'.
    """
    src_a = OperationalEvidenceSource(
        status=SOURCE_AVAILABLE,
        is_elevated=False,
        operational_attention="LOW",
        risk_score=15.0,
        drivers=["routine duty cycle"],
    )
    src_b = PrivateWellbeingEvidenceSource(
        status=SOURCE_NOT_SHARED,
        is_declining_or_elevated=False,
        is_governed=True,
        is_shared=False,
    )

    result = evaluate_evidence_convergence(src_a, src_b, evaluation_date=date(2026, 10, 5))

    assert result.convergence_state == STATE_OPERATIONAL_EVIDENCE_ONLY
    assert result.convergence_state != STATE_NO_ELEVATED_EVIDENCE
    assert result.operational_attention == "LOW"
    assert result.operational_status == SOURCE_AVAILABLE
    assert result.private_status == SOURCE_NOT_SHARED
    assert not result.is_operational_elevated
    assert not result.is_private_elevated
    assert "Private wellbeing evidence is not shared and is not penalized" in result.explanation or "was not evaluated" in result.explanation


def test_case_2_op_low_and_b_unactivated_emits_operational_only():
    """TRUTHFUL-STATE TEST 2:

    When A is routine/LOW and B is INSTRUMENT_NOT_ACTIVATED, convergence MUST emit
    OPERATIONAL_EVIDENCE_ONLY with operational_attention == 'LOW'.
    """
    src_a = OperationalEvidenceSource(
        status=SOURCE_AVAILABLE,
        is_elevated=False,
        operational_attention="LOW",
        risk_score=12.0,
    )
    src_b = PrivateWellbeingEvidenceSource(
        status=SOURCE_NOT_ACTIVATED,
        is_declining_or_elevated=False,
        is_governed=True,
        is_shared=False,
    )

    result = evaluate_evidence_convergence(src_a, src_b, evaluation_date=date(2026, 10, 5))

    assert result.convergence_state == STATE_OPERATIONAL_EVIDENCE_ONLY
    assert result.convergence_state != STATE_NO_ELEVATED_EVIDENCE
    assert result.operational_attention == "LOW"
    assert result.private_status == SOURCE_NOT_ACTIVATED


def test_case_3_op_high_and_b_not_shared_emits_operational_only():
    """TRUTHFUL-STATE TEST 3:

    When A is elevated/HIGH and B is NOT_SHARED, convergence MUST emit
    OPERATIONAL_EVIDENCE_ONLY with operational_attention == 'HIGH'.
    """
    src_a = OperationalEvidenceSource(
        status=SOURCE_AVAILABLE,
        is_elevated=True,
        operational_attention="HIGH",
        risk_score=78.5,
        drivers=["consecutive night shifts", "recovery deficit"],
    )
    src_b = PrivateWellbeingEvidenceSource(
        status=SOURCE_NOT_SHARED,
        is_declining_or_elevated=False,
        is_governed=True,
        is_shared=False,
    )

    result = evaluate_evidence_convergence(src_a, src_b, evaluation_date=date(2026, 10, 5))

    assert result.convergence_state == STATE_OPERATIONAL_EVIDENCE_ONLY
    assert result.operational_attention == "HIGH"
    assert result.is_operational_elevated is True
    assert result.private_status == SOURCE_NOT_SHARED
    assert "consecutive night shifts" in result.explanation


def test_case_4_both_available_and_both_routine_emits_no_elevated():
    """TRUTHFUL-STATE TEST 4:

    NO_ELEVATED_EVIDENCE is emitted ONLY when BOTH sources are actually
    available, governed, shared, and neither is elevated.
    """
    src_a = OperationalEvidenceSource(
        status=SOURCE_AVAILABLE,
        is_elevated=False,
        operational_attention="LOW",
        risk_score=18.0,
    )
    src_b = PrivateWellbeingEvidenceSource(
        status=SOURCE_AVAILABLE,
        is_declining_or_elevated=False,
        is_governed=True,
        is_shared=True,
        attention_category="ROUTINE",
    )

    result = evaluate_evidence_convergence(src_a, src_b, evaluation_date=date(2026, 10, 5))

    assert result.convergence_state == STATE_NO_ELEVATED_EVIDENCE
    assert result.operational_attention == "LOW"
    assert not result.is_operational_elevated
    assert not result.is_private_elevated


def test_case_5_both_available_and_both_elevated_emits_converging():
    """TRUTHFUL-STATE TEST 5:

    CONVERGING_EVIDENCE requires BOTH sources available, governed, shared,
    and both elevated.
    """
    src_a = OperationalEvidenceSource(
        status=SOURCE_AVAILABLE,
        is_elevated=True,
        operational_attention="HIGH",
        risk_score=82.0,
        drivers=["high duty load", "night duty concentration"],
    )
    src_b = PrivateWellbeingEvidenceSource(
        status=SOURCE_AVAILABLE,
        is_declining_or_elevated=True,
        is_governed=True,
        is_shared=True,
        attention_category="ELEVATED_ATTENTION",
    )

    result = evaluate_evidence_convergence(src_a, src_b, evaluation_date=date(2026, 10, 5))

    assert result.convergence_state == STATE_CONVERGING_EVIDENCE
    assert result.is_operational_elevated is True
    assert result.is_private_elevated is True
    assert "Converging evidence" in result.explanation


def test_case_6_both_available_op_elevated_private_routine():
    """Case: A elevated, B available & routine -> OPERATIONAL_EVIDENCE_ONLY."""
    src_a = OperationalEvidenceSource(
        status=SOURCE_AVAILABLE,
        is_elevated=True,
        operational_attention="HIGH",
        risk_score=75.0,
        drivers=["consecutive duties"],
    )
    src_b = PrivateWellbeingEvidenceSource(
        status=SOURCE_AVAILABLE,
        is_declining_or_elevated=False,
        is_governed=True,
        is_shared=True,
    )

    result = evaluate_evidence_convergence(src_a, src_b, evaluation_date=date(2026, 10, 5))

    assert result.convergence_state == STATE_OPERATIONAL_EVIDENCE_ONLY
    assert result.operational_attention == "HIGH"
    assert result.is_operational_elevated is True
    assert result.is_private_elevated is False


def test_case_7_both_available_op_routine_private_elevated():
    """Case: A routine, B available & elevated -> PRIVATE_EVIDENCE_ONLY."""
    src_a = OperationalEvidenceSource(
        status=SOURCE_AVAILABLE,
        is_elevated=False,
        operational_attention="LOW",
        risk_score=20.0,
    )
    src_b = PrivateWellbeingEvidenceSource(
        status=SOURCE_AVAILABLE,
        is_declining_or_elevated=True,
        is_governed=True,
        is_shared=True,
        attention_category="ELEVATED_ATTENTION",
    )

    result = evaluate_evidence_convergence(src_a, src_b, evaluation_date=date(2026, 10, 5))

    assert result.convergence_state == STATE_PRIVATE_EVIDENCE_ONLY
    assert result.operational_attention == "LOW"
    assert result.is_operational_elevated is False
    assert result.is_private_elevated is True


def test_case_8_both_sources_unavailable_emits_convergence_unavailable():
    """Case: Neither source available -> CONVERGENCE_UNAVAILABLE."""
    src_a = OperationalEvidenceSource(status=SOURCE_MODEL_UNAVAILABLE)
    src_b = PrivateWellbeingEvidenceSource(status=SOURCE_UNAVAILABLE)

    result = evaluate_evidence_convergence(src_a, src_b, evaluation_date=date(2026, 10, 5))

    assert result.convergence_state == STATE_CONVERGENCE_UNAVAILABLE
    assert "Insufficient evidence" in result.explanation


@pytest.mark.parametrize(
    "b_status",
    [
        SOURCE_NOT_SHARED,
        SOURCE_NOT_ACTIVATED,
        SOURCE_INSUFFICIENT_HISTORY,
        SOURCE_MODEL_UNAVAILABLE,
        SOURCE_PROCESSING_ERROR,
        SOURCE_UNAVAILABLE,
    ],
)
def test_truthful_state_no_elevated_never_emitted_when_b_unavailable(b_status: str):
    """TRUTHFUL-STATE INVARIANT:

    Regardless of whether A is LOW, MEDIUM, or HIGH, if B is unshared,
    unactivated, insufficient, or unavailable, NO_ELEVATED_EVIDENCE must NEVER
    be emitted.
    """
    for op_att, is_elev in [("LOW", False), ("MEDIUM", True), ("HIGH", True)]:
        src_a = OperationalEvidenceSource(
            status=SOURCE_AVAILABLE,
            is_elevated=is_elev,
            operational_attention=op_att,
        )
        src_b = PrivateWellbeingEvidenceSource(
            status=b_status,
            is_declining_or_elevated=False,
            is_governed=True,
            is_shared=False,
        )

        res = evaluate_evidence_convergence(src_a, src_b)
        assert res.convergence_state != STATE_NO_ELEVATED_EVIDENCE
        assert res.convergence_state == STATE_OPERATIONAL_EVIDENCE_ONLY
        assert res.operational_attention == op_att


def test_commander_projection_strict_privacy_firewall():
    """Commander projection MUST NOT reveal private wellbeing presence,

    status, convergence state, or private evidence existence.
    """
    src_a = OperationalEvidenceSource(
        status=SOURCE_AVAILABLE,
        is_elevated=True,
        operational_attention="HIGH",
        drivers=["overtime"],
    )
    src_b = PrivateWellbeingEvidenceSource(
        status=SOURCE_AVAILABLE,
        is_declining_or_elevated=True,
        is_governed=True,
        is_shared=True,
    )

    conv_res = evaluate_evidence_convergence(src_a, src_b)
    cmd_proj = conv_res.to_commander_projection()

    # Commander receives ONLY operational indicators
    assert "operational_evidence" in cmd_proj
    assert "private_wellbeing_evidence" not in cmd_proj
    assert "private_status" not in cmd_proj
    assert "convergence_state" not in cmd_proj
    assert cmd_proj["operational_evidence"]["operational_attention"] == "HIGH"
    assert cmd_proj["operational_evidence"]["drivers"] == ["overtime"]


def test_welfare_projection_masks_unshared_private_evidence():
    """Welfare projection requires case authorization and masks private evidence

    when is_shared=False.
    """
    src_a = OperationalEvidenceSource(
        status=SOURCE_AVAILABLE,
        is_elevated=False,
        operational_attention="LOW",
    )
    src_b = PrivateWellbeingEvidenceSource(
        status=SOURCE_NOT_SHARED,
        is_declining_or_elevated=False,
        is_governed=True,
        is_shared=False,
    )

    conv_res = evaluate_evidence_convergence(src_a, src_b)

    # Unauthorized case -> None
    assert conv_res.to_welfare_projection(is_case_authorized=False, is_shared=False) is None

    # Authorized case but unshared -> masks private evidence
    welfare_proj = conv_res.to_welfare_projection(is_case_authorized=True, is_shared=False)
    assert welfare_proj is not None
    assert welfare_proj["convergence_state"] == STATE_OPERATIONAL_EVIDENCE_ONLY
    assert welfare_proj["operational_attention"] == "LOW"
    assert welfare_proj["private_wellbeing_evidence"]["status"] == SOURCE_NOT_SHARED
    assert welfare_proj["private_wellbeing_evidence"]["is_elevated"] is None


def test_personnel_projection_includes_self_private_status():
    """Personnel self-projection includes both operational indicators and own

    private wellbeing status.
    """
    src_a = OperationalEvidenceSource(
        status=SOURCE_AVAILABLE,
        is_elevated=False,
        operational_attention="LOW",
    )
    src_b = PrivateWellbeingEvidenceSource(
        status=SOURCE_NOT_ACTIVATED,
        is_declining_or_elevated=False,
        is_governed=True,
        is_shared=False,
    )

    conv_res = evaluate_evidence_convergence(src_a, src_b)
    p_proj = conv_res.to_personnel_projection()

    assert p_proj["convergence_state"] == STATE_OPERATIONAL_EVIDENCE_ONLY
    assert p_proj["operational_attention"] == "LOW"
    assert p_proj["operational_evidence"]["status"] == SOURCE_AVAILABLE
    assert p_proj["private_wellbeing_evidence"]["status"] == SOURCE_NOT_ACTIVATED


def test_admin_projection_governance_metadata_only():
    """Admin projection returns governance metadata only, without case data."""
    src_a = OperationalEvidenceSource(status=SOURCE_AVAILABLE)
    src_b = PrivateWellbeingEvidenceSource(status=SOURCE_NOT_SHARED)

    conv_res = evaluate_evidence_convergence(src_a, src_b)
    adm_proj = conv_res.to_admin_projection()

    assert adm_proj["framework_version"] == CONVERGENCE_FRAMEWORK_VERSION
    assert adm_proj["rules_version"] == CONVERGENCE_RULES_VERSION
    assert "operational_evidence" not in adm_proj
    assert "private_wellbeing_evidence" not in adm_proj
