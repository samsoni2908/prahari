"""Tests for Task B08: Private Raw Storage & Privacy Isolation."""

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock
import pytest
from app.ml.wellbeing_framework import (
    BaseInstrumentAdapter,
    DerivedWellbeingResult,
    GLOBAL_INSTRUMENT_REGISTRY,
    InstrumentItemSpec,
    STATUS_AVAILABLE,
    ATTENTION_ROUTINE,
)
from app.models import Personnel, WellbeingConsent, WellbeingPrivate, WellbeingResult
from app.repositories.wellbeing_repository import WellbeingRepository
from app.repositories.audit_repository import AuditRepository
from app.services.personnel_service import PersonnelService
from fastapi import HTTPException


class MockActiveInstrumentAdapter(BaseInstrumentAdapter):
    @property
    def instrument_id(self) -> str:
        return "TEST_GENERIC_ACTIVE_CHECK"

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
            InstrumentItemSpec(item_id="fatigue", item_label="Perceived fatigue", value_type="int", min_value=1, max_value=5, is_required=True),
            InstrumentItemSpec(item_id="sleep_quality", item_label="Sleep quality", value_type="int", min_value=1, max_value=5, is_required=True),
        ]

    def derive_result(self, answers, assessment_date, prior_results=None):
        avg_val = (answers["fatigue"] + answers["sleep_quality"]) / 2.0
        return DerivedWellbeingResult(
            instrument_id=self.instrument_id,
            instrument_version=self.instrument_version,
            scoring_version=self.scoring_version,
            assessment_date=assessment_date,
            status=STATUS_AVAILABLE,
            summary_scores={"recovery_index": avg_val * 20.0},
            attention_category=ATTENTION_ROUTINE,
            confidence_score=1.0,
        )


@pytest.mark.asyncio
async def test_unactivated_instrument_submission_raises_503():
    """Submitting with an unapproved/unactivated instrument raises 503 INSTRUMENT_NOT_ACTIVATED."""
    pers_id = uuid.uuid4()
    mock_repo = MagicMock(spec=WellbeingRepository)
    mock_repo.get_latest_consent = AsyncMock(
        return_value=WellbeingConsent(
            personnel_id=pers_id,
            consent_version="1.0",
            purpose="General Wellbeing",
            status="ACTIVE",
        )
    )

    mock_audit = MagicMock(spec=AuditRepository)
    mock_audit.log_event = AsyncMock()

    service = PersonnelService(
        personnel_repo=None,
        unit_repo=None,
        wellbeing_repo=mock_repo,
        analytics_repo=None,
        operational_repo=None,
        audit_repo=mock_audit,
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.submit_self_check(
            personnel_id=pers_id,
            answers={"q1": 1},
            instrument_name="UNAPPROVED_QUESTIONNAIRE",
        )
    assert exc_info.value.status_code == 503
    assert "INSTRUMENT_NOT_ACTIVATED" in exc_info.value.detail


@pytest.mark.asyncio
async def test_submission_without_active_consent_raises_403():
    """Submitting without active consent raises 403 CONSENT_REQUIRED."""
    pers_id = uuid.uuid4()
    mock_repo = MagicMock(spec=WellbeingRepository)
    mock_repo.get_latest_consent = AsyncMock(return_value=None)  # No consent

    mock_audit = MagicMock(spec=AuditRepository)
    mock_audit.log_event = AsyncMock()

    service = PersonnelService(
        personnel_repo=None,
        unit_repo=None,
        wellbeing_repo=mock_repo,
        analytics_repo=None,
        operational_repo=None,
        audit_repo=mock_audit,
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.submit_self_check(
            personnel_id=pers_id,
            answers={"fatigue": 2, "sleep_quality": 3},
            instrument_name="TEST_GENERIC_ACTIVE_CHECK",
        )
    assert exc_info.value.status_code == 403
    assert "CONSENT_REQUIRED" in exc_info.value.detail


@pytest.mark.asyncio
async def test_invalid_responses_raise_422():
    """Invalid responses (missing required item or out of range) raise 422."""
    pers_id = uuid.uuid4()
    mock_repo = MagicMock(spec=WellbeingRepository)
    mock_repo.get_latest_consent = AsyncMock(
        return_value=WellbeingConsent(
            personnel_id=pers_id,
            consent_version="1.0",
            purpose="General Wellbeing",
            status="ACTIVE",
        )
    )

    adapter = MockActiveInstrumentAdapter()
    GLOBAL_INSTRUMENT_REGISTRY.register(adapter)

    mock_audit = MagicMock(spec=AuditRepository)
    mock_audit.log_event = AsyncMock()

    service = PersonnelService(
        personnel_repo=None,
        unit_repo=None,
        wellbeing_repo=mock_repo,
        analytics_repo=None,
        operational_repo=None,
        audit_repo=mock_audit,
    )

    # Missing sleep_quality
    with pytest.raises(HTTPException) as exc_info:
        await service.submit_self_check(
            personnel_id=pers_id,
            answers={"fatigue": 2},
            instrument_name="TEST_GENERIC_ACTIVE_CHECK",
        )
    assert exc_info.value.status_code == 422
    assert "INVALID_RESPONSE" in exc_info.value.detail
    assert "sleep_quality" in exc_info.value.detail

    # Out of range (fatigue = 99 > 5)
    with pytest.raises(HTTPException) as exc_info2:
        await service.submit_self_check(
            personnel_id=pers_id,
            answers={"fatigue": 99, "sleep_quality": 3},
            instrument_name="TEST_GENERIC_ACTIVE_CHECK",
        )
    assert exc_info2.value.status_code == 422
    assert "exceeds maximum" in exc_info2.value.detail


@pytest.mark.asyncio
async def test_valid_submission_stores_strictly_in_private_and_derived():
    """Valid submission persists raw in wellbeing_private and derived in wellbeing_results."""
    pers_id = uuid.uuid4()
    stored_private = []
    stored_derived = []

    mock_repo = MagicMock(spec=WellbeingRepository)
    mock_repo.get_latest_consent = AsyncMock(
        return_value=WellbeingConsent(
            personnel_id=pers_id,
            consent_version="1.0",
            purpose="General Wellbeing",
            status="ACTIVE",
        )
    )

    async def fake_submit_self_check(check: WellbeingPrivate):
        stored_private.append(check)
        return check

    async def fake_record_result(res: WellbeingResult):
        stored_derived.append(res)
        return res

    mock_repo.submit_self_check = AsyncMock(side_effect=fake_submit_self_check)
    mock_repo.record_wellbeing_result = AsyncMock(side_effect=fake_record_result)

    adapter = MockActiveInstrumentAdapter()
    GLOBAL_INSTRUMENT_REGISTRY.register(adapter)

    mock_audit = MagicMock(spec=AuditRepository)
    mock_audit.log_event = AsyncMock()

    service = PersonnelService(
        personnel_repo=None,
        unit_repo=None,
        wellbeing_repo=mock_repo,
        analytics_repo=None,
        operational_repo=None,
        audit_repo=mock_audit,
    )

    answers = {"fatigue": 3, "sleep_quality": 4}
    res = await service.submit_self_check(
        personnel_id=pers_id,
        answers=answers,
        instrument_name="TEST_GENERIC_ACTIVE_CHECK",
    )

    # 1. Check returned safe projection
    assert "id" in res
    assert res["status"] == STATUS_AVAILABLE
    assert res["category_label"] == ATTENTION_ROUTINE
    # Zero raw answer leakage in projection
    assert "fatigue" not in res
    assert "sleep_quality" not in res
    assert "answers" not in res

    # 2. Verify raw storage in private record
    assert len(stored_private) == 1
    priv = stored_private[0]
    assert priv.personnel_id == pers_id
    assert priv.answers_json == {"fatigue": 3, "sleep_quality": 4}

    # 3. Verify non-raw storage in derived record
    assert len(stored_derived) == 1
    der = stored_derived[0]
    assert der.personnel_id == pers_id
    assert der.score_summary_json["summary_scores"] == {"recovery_index": 70.0}
    assert der.score_summary_json["instrument_id"] == "TEST_GENERIC_ACTIVE_CHECK"
    assert der.score_summary_json["scoring_version"] == "v1-deterministic"
    assert der.score_summary_json["processing_version"] == "v1.0-governed"
    assert der.model_version == "1.0:v1-deterministic"
    assert der.category_label == ATTENTION_ROUTINE
    # Zero raw answers in derived record
    assert not hasattr(der, "answers_json")

    # 4. Verify audit event logged with zero raw answers
    mock_audit.log_event.assert_awaited_once()
    _, kwargs = mock_audit.log_event.call_args
    assert kwargs["action"] == "SELF_CHECK_SUBMITTED"
    assert kwargs["resource_type"] == "wellbeing_private"
    assert "answers" not in kwargs


@pytest.mark.asyncio
async def test_rejected_unactivated_submission_creates_zero_rows():
    """Verify that when no approved instrument adapter is active, submission is rejected and creates ZERO rows."""
    pers_id = uuid.uuid4()
    mock_repo = MagicMock(spec=WellbeingRepository)
    mock_repo.get_latest_consent = AsyncMock(
        return_value=WellbeingConsent(
            personnel_id=pers_id,
            consent_version="1.0",
            purpose="General Wellbeing",
            status="ACTIVE",
        )
    )

    stored_private = []
    stored_derived = []

    async def fake_submit(check):
        stored_private.append(check)
        return check

    async def fake_record(res):
        stored_derived.append(res)
        return res

    mock_repo.submit_self_check = AsyncMock(side_effect=fake_submit)
    mock_repo.record_wellbeing_result = AsyncMock(side_effect=fake_record)

    mock_audit = MagicMock(spec=AuditRepository)
    mock_audit.log_event = AsyncMock()

    service = PersonnelService(
        personnel_repo=None, unit_repo=None, wellbeing_repo=mock_repo,
        analytics_repo=None, operational_repo=None, audit_repo=mock_audit,
    )

    # Counts before attempt
    count_private_before = len(stored_private)
    count_derived_before = len(stored_derived)

    with pytest.raises(HTTPException) as exc_info:
        await service.submit_self_check(
            personnel_id=pers_id,
            answers={"item1": 4, "item2": 5},
            instrument_name="GENERIC_UNACTIVATED",
        )

    assert exc_info.value.status_code == 503
    assert "INSTRUMENT_NOT_ACTIVATED" in exc_info.value.detail

    # Counts after rejected attempt MUST be unchanged (0 == 0)
    count_private_after = len(stored_private)
    count_derived_after = len(stored_derived)
    assert count_private_before == count_private_after == 0
    assert count_derived_before == count_derived_after == 0
    mock_audit.log_event.assert_not_called()
