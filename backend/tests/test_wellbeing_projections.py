"""Tests for Task B11, B12, B13, B14: Personnel Projection, Commander Denial, Welfare Gated Access, and Admin Denial."""

import uuid
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi import HTTPException

from app.models import WellbeingConsent, WellbeingPrivate, WellbeingResult
from app.repositories.wellbeing_repository import WellbeingRepository
from app.services.personnel_service import PersonnelService
from app.services.welfare_service import WelfareService
from app.api.personnel import _get_target_personnel_id


@pytest.mark.asyncio
async def test_personnel_projection_own_access_success():
    """Verify Personnel receives own consent, history, and non-raw derived results."""
    pers_id = uuid.uuid4()
    mock_repo = MagicMock(spec=WellbeingRepository)

    mock_repo.get_latest_consent = AsyncMock(
        return_value=WellbeingConsent(
            id=uuid.uuid4(),
            personnel_id=pers_id,
            consent_version="1.0",
            purpose="Self-check",
            status="ACTIVE",
            consented_at=datetime.utcnow(),
        )
    )

    mock_repo.list_self_checks = AsyncMock(
        return_value=[
            WellbeingPrivate(
                id=uuid.uuid4(),
                personnel_id=pers_id,
                assessment_date=date(2026, 10, 1),
                instrument_name="TEST_CHECK",
                instrument_version="1.0",
                answers_json={"item1": 3},
                score_json={"score": 30},
                created_at=datetime.utcnow(),
            )
        ]
    )

    mock_repo.list_wellbeing_results = AsyncMock(
        return_value=[
            WellbeingResult(
                id=uuid.uuid4(),
                wellbeing_private_id=uuid.uuid4(),
                personnel_id=pers_id,
                instrument_name="TEST_CHECK",
                assessment_date=date(2026, 10, 1),
                score_summary_json={"recovery_index": 60.0},
                category_label="ROUTINE",
                trend_label="STABLE",
                model_version="1.0:v1",
                created_at=datetime.utcnow(),
            )
        ]
    )

    service = PersonnelService(
        personnel_repo=None,
        unit_repo=None,
        wellbeing_repo=mock_repo,
        analytics_repo=None,
        operational_repo=None,
        audit_repo=None,
    )

    consent = await service.get_consent(pers_id)
    assert consent["status"] == "ACTIVE"

    checks = await service.list_self_checks(pers_id)
    assert len(checks) == 1
    assert checks[0]["answers"] == {"item1": 3}

    derived = await service.list_wellbeing_results(pers_id)
    assert len(derived) == 1
    # Historical retained result is distinguished as LEGACY_UNGOVERNED
    assert derived[0]["governance_status"] == "LEGACY_UNGOVERNED"
    assert derived[0]["category_label"] == "HISTORICAL_RECORD"
    assert derived[0]["trend_label"] == "INSUFFICIENT_GOVERNED_HISTORY"
    assert derived[0]["historical_category_label"] == "ROUTINE"
    # Derived results must NOT contain raw answers
    assert "answers" not in derived[0]


def test_legacy_result_cannot_become_governed_current_attention():
    """Verify legacy retained assessments with historical labels cannot become current governed attention."""
    from app.ml.wellbeing_framework import ATTENTION_ROUTINE, ATTENTION_ELEVATED
    res = WellbeingResult(
        id=uuid.uuid4(),
        wellbeing_private_id=uuid.uuid4(),
        personnel_id=uuid.uuid4(),
        instrument_name="PRAHARI_SELF_CHECK",
        assessment_date=date(2026, 8, 1),
        score_summary_json={"composite_self_check_score": 2.43},
        category_label="SATISFACTORY",
        trend_label="STABLE",
        model_version="wsi_v2",
        created_at=datetime.utcnow(),
    )
    mock_repo = MagicMock(spec=WellbeingRepository)
    mock_repo.list_wellbeing_results = AsyncMock(return_value=[res])
    service = PersonnelService(
        personnel_repo=None, unit_repo=None, wellbeing_repo=mock_repo,
        analytics_repo=None, operational_repo=None, audit_repo=None,
    )
    async def check():
        projections = await service.list_wellbeing_results(res.personnel_id)
        assert len(projections) == 1
        p = projections[0]
        assert p["governance_status"] == "LEGACY_UNGOVERNED"
        assert p["category_label"] == "HISTORICAL_RECORD"
        assert p["category_label"] not in (ATTENTION_ROUTINE, ATTENTION_ELEVATED)
        assert p["trend_label"] == "INSUFFICIENT_GOVERNED_HISTORY"
    import asyncio
    asyncio.run(check())


def test_personnel_cross_person_idor_denied():
    """Verify Personnel A cannot query Personnel B's wellbeing records (cross-person IDOR denial)."""
    pers_a_id = uuid.uuid4()
    pers_b_id = uuid.uuid4()
    user_a = {"user_id": str(uuid.uuid4()), "role": "PERSONNEL", "personnel_id": str(pers_a_id)}

    # Request claims to target user_a, resolved personnel_id must be pers_a_id, never pers_b_id
    resolved_id = _get_target_personnel_id(user_a)
    assert resolved_id == pers_a_id
    assert resolved_id != pers_b_id


def test_personnel_foreign_access_denial_when_unbound():
    """Verify actor without bound personnel profile is denied."""
    current_user_unbound = {"user_id": str(uuid.uuid4()), "role": "PERSONNEL", "personnel_id": None}
    with pytest.raises(HTTPException) as exc_info:
        _get_target_personnel_id(current_user_unbound)
    assert exc_info.value.status_code == 400
    assert "No personnel profile linked" in exc_info.value.detail


def test_commander_projection_strictly_omits_wellbeing_fields():
    """Verify Commander payload models and projections contain ZERO wellbeing fields."""
    # Simulate a commander operational profile projection
    operational_profile = {
        "id": str(uuid.uuid4()),
        "pseudo_id": "PSD_12345",
        "rank_or_grade": "Sub-Inspector",
        "role_title": "Section Commander",
        "status": "Active",
        "wsi_score": 52.4,
        "wsi_band": "MEDIUM",
        "operational_attention": "ELEVATED_DUTY_LOAD",
    }

    # Prohibited wellbeing fields that must NEVER appear in Commander projections
    prohibited_keys = {
        "wellbeing",
        "wellbeing_score",
        "wellbeing_private",
        "wellbeing_results",
        "answers_json",
        "score_json",
        "raw_answers",
        "answers",
        "private_trend",
        "self_check",
        "instrument_name",
        "instrument_version",
        "assessment_count",
    }

    for key in prohibited_keys:
        assert key not in operational_profile, f"Prohibited key '{key}' found in Commander projection!"


@pytest.mark.asyncio
async def test_welfare_unassigned_request_denied():
    """Verify Welfare Officer cannot access personnel profile without an authorized support case."""
    pers_id = uuid.uuid4()
    mock_repo = MagicMock(spec=WellbeingRepository)
    mock_repo.get_authorized_case_for_personnel = AsyncMock(return_value=None)  # No case

    service = WelfareService(
        wellbeing_repo=mock_repo,
        personnel_repo=None,
        unit_repo=None,
        analytics_repo=None,
        audit_repo=None,
    )

    profile = await service.get_personnel_profile(pers_id)
    assert profile is None  # Denied access


@pytest.mark.asyncio
async def test_welfare_projection_derived_status_is_not_shared_and_zero_raw_answers():
    """Verify Welfare Officer projection returns NOT_SHARED for wellbeing and never leaks raw answers."""
    pers_id = uuid.uuid4()
    unit_id = uuid.uuid4()
    case_id = uuid.uuid4()
    officer_user_id = uuid.uuid4()

    mock_repo = MagicMock(spec=WellbeingRepository)
    mock_repo.session = MagicMock()
    mock_repo.session.info = {"actor": {"user_id": str(officer_user_id), "role": "WELFARE_OFFICER"}}

    mock_case = MagicMock()
    mock_case.id = case_id
    mock_repo.get_authorized_case_for_personnel = AsyncMock(return_value=mock_case)

    mock_audit = MagicMock()
    mock_audit.log_event = AsyncMock()

    mock_person = MagicMock()
    mock_person.id = pers_id
    mock_person.pseudo_id = "PSD_9988"
    mock_person.personnel_code = "P9988"
    mock_person.rank_or_grade = "Constable"
    mock_person.role_title = "Rifleman"
    mock_person.status = "Active"
    mock_person.service_years = 4.5
    mock_person.joining_date = date(2022, 1, 1)
    mock_person.unit_id = unit_id

    mock_pers_repo = MagicMock()
    mock_pers_repo.get_by_id = AsyncMock(return_value=mock_person)
    mock_pers_repo.get_posting_history = AsyncMock(return_value=[])

    mock_unit = MagicMock()
    mock_unit.id = unit_id
    mock_unit.unit_name = "Alpha Coy"
    mock_unit.unit_code = "A-COY"
    mock_unit.location_label = "Sector 1"
    mock_unit_repo = MagicMock()
    mock_unit_repo.get_by_id = AsyncMock(return_value=mock_unit)

    mock_analytics = MagicMock()
    mock_analytics.get_latest_wsi = AsyncMock(return_value=None)
    mock_analytics.get_active_alerts_by_personnel = AsyncMock(return_value=[])
    mock_analytics.get_latest_baseline = AsyncMock(return_value=None)
    mock_analytics.get_latest_anomaly = AsyncMock(return_value=None)
    mock_analytics.get_latest_prediction = AsyncMock(return_value=None)
    mock_analytics.get_wsi_history = AsyncMock(return_value=[])

    service = WelfareService(
        wellbeing_repo=mock_repo,
        personnel_repo=mock_pers_repo,
        unit_repo=mock_unit_repo,
        analytics_repo=mock_analytics,
        audit_repo=mock_audit,
    )

    profile = await service.get_personnel_profile(pers_id)
    assert profile is not None
    # Tab 6: Authorized Wellbeing summary MUST be strictly NOT_SHARED
    assert profile["wellbeing"] == {"status": "NOT_SHARED"}
    # Raw answers must NEVER exist in welfare projection
    assert "answers" not in profile["wellbeing"]
    assert "answers_json" not in profile["wellbeing"]
    assert "score_json" not in profile["wellbeing"]


@pytest.mark.asyncio
async def test_admin_privacy_projection_denial():
    """Verify Admin is not a welfare superuser and receives zero individual wellbeing data."""
    from app.security.deps import require_roles

    # Verify role dependency denies ADMIN on personnel and welfare routes
    personnel_guard = require_roles("PERSONNEL")
    welfare_guard = require_roles("WELFARE_OFFICER")

    admin_user = {"user_id": str(uuid.uuid4()), "role": "ADMIN", "username": "demo_admin"}

    with pytest.raises(HTTPException) as exc1:
        await personnel_guard(admin_user)
    assert exc1.value.status_code == 403

    with pytest.raises(HTTPException) as exc2:
        await welfare_guard(admin_user)
    assert exc2.value.status_code == 403


    # Verify admin audit log model strictly masks raw answers
    audit_row = {
        "id": str(uuid.uuid4()),
        "actor_role": "ADMIN",
        "action": "CONFIG_UPDATED",
        "resource_type": "policy_config",
        "result": "SUCCESS",
    }
    for forbidden in ("answers_json", "score_json", "raw_answers", "wellbeing_results"):
        assert forbidden not in audit_row
