"""External-action safety on the explicit Stage-4 disposable PostgreSQL database."""

from datetime import datetime, timedelta, timezone
import asyncio
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.models import (
    Duty, LeaveRecord, Outcome, Personnel, PolicyConfig, RestRecord,
    RosterAssignment, RosterScenario, ScenarioImplementation, ShiftRequirement, Staffing,
)
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.personnel_repository import PersonnelRepository
from app.repositories.scenario_repository import ScenarioRepository
from app.repositories.unit_repository import UnitRepository
from app.services.implementation_service import ImplementationService
from app.services.scenario_service import ScenarioService
from app.services.verify_service import VerifyService, _adherence_summary, _hash_rows
from tests.test_stage4b_balance_decision import (
    TEST_DB_URL, DEMO_COMMANDER_USER_ID, DEMO_CUTOFF, DEMO_UNIT_ID,
)


async def _scenario(session):
    session.info["actor"] = {
        "user_id": str(DEMO_COMMANDER_USER_ID),
        "role": "COMMANDER",
        "unit_id": str(DEMO_UNIT_ID),
    }
    svc = ScenarioService(
        ScenarioRepository(session), UnitRepository(session),
        AnalyticsRepository(session), PersonnelRepository(session),
        AuditRepository(session),
    )
    created = await svc.create_what_if_scenario(
        DEMO_UNIT_ID, DEMO_COMMANDER_USER_ID,
        scenario_name="Stage-5 disposable external-action proof " + str(uuid.uuid4()),
        cutoff=DEMO_CUTOFF,
    )
    assert created["status"] == "FEASIBLE"
    sid = uuid.UUID(created["id"])
    accepted = await svc.record_decision(
        sid, DEMO_COMMANDER_USER_ID, "ACCEPT",
        "Reviewed operational roster proposal",
        expected_revision=created["expected_revision"],
        idempotency_key="accept-" + str(uuid.uuid4()),
    )
    assert accepted["status"] == "APPROVED"
    governed = await svc.get_scenario(sid)
    scenario = (await session.execute(select(RosterScenario).where(RosterScenario.id == sid))).scalar_one()
    actual = [
        {"shift_id": item["shift_id"], "personnel_id": item["personnel_id"]}
        for item in scenario.proposed_snapshot_json["assignments"]
    ]
    return sid, uuid.UUID(accepted["approval_id"]), governed["expected_revision"], actual


@pytest.mark.asyncio
async def test_implemented_is_immutable_and_pending_without_source_mutation():
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    try:
        async with factory() as session:
            sid, aid, revision, actual = await _scenario(session)
            baseline = {
                model.__tablename__: await session.scalar(select(func.count()).select_from(model))
                for model in (Duty, LeaveRecord, RosterAssignment)
            }
            service = ImplementationService(session)
            u = DEMO_CUTOFF + timedelta(days=1)
            clock = u + timedelta(hours=1)
            result = await service.record(
                sid, aid, "IMPLEMENTED", revision, "implementation-" + str(sid),
                u, actual, "SYNTHETIC-EXTERNAL-REF", None, clock,
            )
            assert result["result"] == "IMPLEMENTED"
            assert result["implementation_id"]
            assert (await VerifyService(session).get(sid))["workflow_status"] == "PENDING"
            assert await session.scalar(select(func.count()).select_from(Outcome).where(Outcome.implementation_id == uuid.UUID(result["implementation_id"]))) == 1
            assert await session.scalar(select(func.count()).select_from(ScenarioImplementation).where(ScenarioImplementation.scenario_id == sid)) == 1
            replay = await service.record(
                sid, aid, "IMPLEMENTED", revision, "implementation-" + str(sid),
                u, actual, "SYNTHETIC-EXTERNAL-REF", None, clock,
            )
            assert replay["replay_safe"] and replay["implementation_id"] == result["implementation_id"]
            with pytest.raises(HTTPException) as collision:
                await service.record(
                    sid, aid, "IMPLEMENTED", revision, "implementation-" + str(sid),
                    u, actual, "CHANGED-REF", None, clock,
                )
            assert collision.value.status_code == 409
            assert baseline == {
                model.__tablename__: await session.scalar(select(func.count()).select_from(model))
                for model in (Duty, LeaveRecord, RosterAssignment)
            }
            await session.rollback()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_explicit_as_approved_attestation_derives_actual_assignments():
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    try:
        async with factory() as session:
            sid, aid, revision, actual = await _scenario(session)
            service = ImplementationService(session)
            effective = DEMO_CUTOFF + timedelta(days=1)
            clock = effective + timedelta(hours=1)
            with pytest.raises(HTTPException) as conflict:
                await service.record(
                    sid, aid, "IMPLEMENTED", revision, "attestation-conflict-" + str(sid),
                    effective, actual, "SYNTHETIC-EXTERNAL-REF", None, clock,
                    confirm_approved_assignments=True,
                )
            assert conflict.value.status_code == 422
            recorded = await service.record(
                sid, aid, "IMPLEMENTED", revision, "attestation-" + str(sid),
                effective, None, "SYNTHETIC-EXTERNAL-REF", None, clock,
                confirm_approved_assignments=True,
            )
            assert recorded["result"] == "IMPLEMENTED"
            implementation = await session.scalar(select(ScenarioImplementation).where(ScenarioImplementation.scenario_id == sid))
            assert implementation.actual_assignments_json["commander_confirmed_as_approved"] is True
            assert len(implementation.actual_assignments_json["assignments"]) == len(actual)
            await session.rollback()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_implementation_rejects_mismatch_and_not_implemented_has_no_record():
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    try:
        async with factory() as session:
            sid, aid, revision, actual = await _scenario(session)
            service = ImplementationService(session)
            u = DEMO_CUTOFF + timedelta(days=1)
            clock = u + timedelta(hours=1)
            with pytest.raises(HTTPException) as mismatch:
                await service.record(
                    sid, aid, "IMPLEMENTED", revision, "mismatch-" + str(sid),
                    u, actual[1:], "SYNTHETIC-EXTERNAL-REF", None, clock,
                )
            assert mismatch.value.status_code == 409
            with pytest.raises(HTTPException) as stale:
                await service.record(
                    sid, aid, "IMPLEMENTED", "rev-sha256-stale", "stale-" + str(sid),
                    u, actual, "SYNTHETIC-EXTERNAL-REF", None, clock,
                )
            assert stale.value.status_code == 409
            # A cancelled external action remains recordable even after the
            # source roster has changed; only IMPLEMENTED needs live parity.
            session.info["actor"] = None
            shift = (await session.execute(select(ShiftRequirement).where(
                ShiftRequirement.unit_id == DEMO_UNIT_ID,
            ).limit(1))).scalar_one()
            shift.source_revision = "SYNTHETIC_STAGE5_CHANGED"
            await session.flush()
            session.info["actor"] = {
                "user_id": str(DEMO_COMMANDER_USER_ID), "role": "COMMANDER",
                "unit_id": str(DEMO_UNIT_ID),
            }
            with pytest.raises(HTTPException) as changed:
                await service.record(
                    sid, aid, "IMPLEMENTED", revision, "changed-" + str(sid),
                    u, actual, "SYNTHETIC-EXTERNAL-REF", None, clock,
                )
            assert changed.value.status_code == 409
            assert changed.value.detail == "SOURCE_CHANGED"
            result = await service.record(
                sid, aid, "NOT_IMPLEMENTED", revision,
                "not-implemented-" + str(sid), reason_code="EXTERNAL_ACTION_NOT_TAKEN",
            )
            assert result["result"] == "NOT_IMPLEMENTED"
            assert result["implementation_id"] is None
            assert await session.scalar(select(func.count()).select_from(ScenarioImplementation).where(ScenarioImplementation.scenario_id == sid)) == 0
            assert await session.scalar(select(func.count()).select_from(Outcome).where(Outcome.scenario_id == sid)) == 0
            await session.rollback()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_implementation_requires_current_approval_and_unit_commander():
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    try:
        async with factory() as session:
            sid, aid, revision, actual = await _scenario(session)
            service = ImplementationService(session)
            effective = DEMO_CUTOFF + timedelta(days=1)
            args = (sid, aid, "IMPLEMENTED", revision, "role-test", effective,
                    actual, "SYNTHETIC-EXTERNAL-REF", None, effective + timedelta(hours=1))
            actor = dict(session.info["actor"])
            for role in ("PERSONNEL", "WELFARE_OFFICER", "ADMIN"):
                session.info["actor"] = {**actor, "role": role}
                with pytest.raises(HTTPException) as denied:
                    await service.record(*args)
                assert denied.value.status_code == 403
            session.info["actor"] = {**actor, "unit_id": str(uuid.uuid4())}
            with pytest.raises(HTTPException) as wrong_unit:
                await service.record(*args)
            assert wrong_unit.value.status_code == 404
            session.info["actor"] = actor
            scenario = (await session.execute(select(RosterScenario).where(RosterScenario.id == sid))).scalar_one()
            for status in ("FEASIBLE", "REJECTED", "SUPERSEDED"):
                scenario.status = status
                with pytest.raises(HTTPException) as denied:
                    await service.record(*args)
                assert denied.value.status_code == 409
            scenario.status = "APPROVED"
            with pytest.raises(HTTPException) as future:
                await service.record(
                    sid, aid, "IMPLEMENTED", revision, "future-test",
                    DEMO_CUTOFF + timedelta(days=20), actual,
                    "SYNTHETIC-EXTERNAL-REF", None,
                    DEMO_CUTOFF + timedelta(days=20, hours=1),
                )
            assert future.value.status_code in (409, 422)
            await session.rollback()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("second_result", ["IMPLEMENTED", "NOT_IMPLEMENTED"])
async def test_concurrent_terminal_actions_allow_one_winner(second_result):
    """Two independent transactions race on a uniquely named disposable scenario."""
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    try:
        async with factory() as session:
            sid, aid, revision, actual = await _scenario(session)
            await session.commit()

        async def attempt(result, suffix):
            async with factory() as session:
                session.info["actor"] = {
                    "user_id": str(DEMO_COMMANDER_USER_ID), "role": "COMMANDER",
                    "unit_id": str(DEMO_UNIT_ID),
                }
                effective = DEMO_CUTOFF + timedelta(days=1)
                try:
                    value = await ImplementationService(session).record(
                        sid, aid, result, revision, "race-" + suffix + "-" + str(sid),
                        effective if result == "IMPLEMENTED" else None,
                        actual if result == "IMPLEMENTED" else None,
                        "SYNTHETIC-EXTERNAL-REF" if result == "IMPLEMENTED" else None,
                        "ACTION_NOT_TAKEN" if result == "NOT_IMPLEMENTED" else None,
                        effective + timedelta(hours=1) if result == "IMPLEMENTED" else None,
                    )
                    await session.commit()
                    return value["result"]
                except HTTPException as exc:
                    await session.rollback()
                    return exc.status_code

        results = await asyncio.gather(
            attempt("IMPLEMENTED", "first"), attempt(second_result, "second")
        )
        assert results.count(409) == 1
        assert len([value for value in results if value in ("IMPLEMENTED", "NOT_IMPLEMENTED")]) == 1
        async with factory() as session:
            assert await session.scalar(select(func.count()).select_from(ScenarioImplementation).where(
                ScenarioImplementation.scenario_id == sid,
            )) <= 1
            assert await session.scalar(select(func.count()).select_from(Outcome).where(
                Outcome.scenario_id == sid,
            )) <= 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_historical_synthetic_verify_observation_and_review():
    """A labelled disposable fixture supplies explicit source coverage; retained rows are untouched."""
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    try:
        async with factory() as session:
            sid, aid, revision, actual = await _scenario(session)
            u = DEMO_CUTOFF + timedelta(days=1)
            action = await ImplementationService(session).record(
                sid, aid, "IMPLEMENTED", revision, "verify-" + str(sid),
                u, actual, "SYNTHETIC-EXTERNAL-REF", None, u + timedelta(hours=1),
            )
            verifier = VerifyService(session)
            pending = await verifier.observe(sid, u + timedelta(days=13))
            assert pending["workflow_status"] == "PENDING"
            assert pending["availability_status"] == "NOT_COMPUTED"
            missing = await verifier.observe(sid, u + timedelta(days=15))
            assert missing["workflow_status"] == "PENDING"
            assert missing["reason_code"] == "VERIFY_POLICY_UNAVAILABLE"

            # This fixture is explicit synthetic replay data and exists only
            # inside the disposable transaction. It supplies dated staffing
            # evidence, independent historical shift requirements and rest
            # observations where the old raw sample is sparse.
            session.info["actor"] = None
            people = list((await session.execute(select(Personnel).where(Personnel.unit_id == DEMO_UNIT_ID))).scalars())
            affected = {uuid.UUID(value) for value in (
                await session.scalar(select(Outcome.observed_metrics_json).where(
                    Outcome.implementation_id == uuid.UUID(action["implementation_id"])
                ))
            )["frozen_affected_personnel_ids"]}
            existing_staff = {
                row.record_date for row in (await session.execute(
                    select(Staffing).where(Staffing.unit_id == DEMO_UNIT_ID)
                )).scalars()
            }
            existing_shifts = {
                row.start_at.date() for row in (await session.execute(
                    select(ShiftRequirement).where(ShiftRequirement.unit_id == DEMO_UNIT_ID)
                )).scalars()
            }
            for day_offset in range(-14, 14):
                day = (u + timedelta(days=day_offset)).date()
                if day not in existing_staff:
                    session.add(Staffing(
                        id=uuid.uuid4(), unit_id=DEMO_UNIT_ID, record_date=day,
                        sanctioned_strength=32, available_strength=28,
                        required_strength=28, coverage_percent=100,
                        created_at=u,
                    ))
                if day not in existing_shifts:
                    start = datetime.combine(day, datetime.min.time(), timezone.utc) + timedelta(hours=8)
                    session.add(ShiftRequirement(
                        id=uuid.uuid4(), unit_id=DEMO_UNIT_ID,
                        start_at=start, end_at=start + timedelta(hours=8),
                        required_count=1, required_skills_json=[],
                        is_locked=False, source_revision="SYNTHETIC_STAGE5_REPLAY",
                        created_at=u,
                    ))
            await session.flush()
            for start, end in ((u - timedelta(days=14), u), (u, u + timedelta(days=14))):
                rows = await verifier._window_rows(DEMO_UNIT_ID, {person.id for person in people}, start, end)
                observed_people = {
                    row.personnel_id for row in rows["rest_records"]
                    if row.rest_hours is not None and row.rest_gap_hours is not None
                    and row.data_quality_status == "OBSERVED"
                }
                for person_id in affected - observed_people:
                    session.add(RestRecord(
                        id=uuid.uuid4(), personnel_id=person_id,
                        record_date=start.date(),
                        rest_hours=8, rest_gap_hours=12,
                        source="SYNTHETIC_STAGE5_REPLAY",
                        data_quality_status="OBSERVED", created_at=u,
                    ))
            await session.flush()
            session.add(PolicyConfig(
                id=uuid.uuid4(), policy_key="verify.policy.VERIFY_POLICY_V1_SYNTHETIC_DEMO",
                policy_value_json={"policy_name": "VERIFY_POLICY_V1_SYNTHETIC_DEMO", "observation_duration_days": 14},
                version="VERIFY_POLICY_V1_SYNTHETIC_DEMO", effective_from=u, created_at=u,
            ))
            claim = {
                "schema_version": "1.0", "dataset_version": "SYNTHETIC_STAGE5_REPLAY_FIXTURE_V1",
                "implementation_id": action["implementation_id"],
                "unit_id": str(DEMO_UNIT_ID), "effective_at": u.isoformat(),
                "zero_unknown_gaps": True,
            }
            for name, start, end in (
                ("before", u - timedelta(days=14), u),
                ("after", u, u + timedelta(days=14)),
            ):
                rows = await verifier._window_rows(DEMO_UNIT_ID, {person.id for person in people}, start, end)
                claim[name] = {
                    "start_at": start.isoformat(), "end_at": end.isoformat(),
                    "families": {
                        family: {"complete": True, "count": len(values), "hash": _hash_rows(values)}
                        for family, values in rows.items()
                    },
                }
            session.add(PolicyConfig(
                id=uuid.uuid4(), policy_key="verify.coverage." + action["implementation_id"],
                policy_value_json=claim, version="SOURCE_COVERAGE_POLICY_V1_SYNTHETIC_DEMO",
                effective_from=u, created_at=u,
            ))
            await session.flush()
            manifest = (await session.execute(select(PolicyConfig).where(
                PolicyConfig.policy_key == "verify.coverage." + action["implementation_id"],
            ))).scalar_one()
            broken = {**claim, "before": {**claim["before"], "families": {
                **claim["before"]["families"],
                "duties": {**claim["before"]["families"]["duties"], "count": -1},
            }}}
            manifest.policy_value_json = broken
            await session.flush()
            session.info["actor"] = {
                "user_id": str(DEMO_COMMANDER_USER_ID),
                "role": "COMMANDER",
                "unit_id": str(DEMO_UNIT_ID),
            }
            incomplete = await verifier.observe(sid, u + timedelta(days=15))
            assert incomplete["workflow_status"] == "PENDING"
            assert incomplete["availability_status"] == "INSUFFICIENT_HISTORY"
            session.info["actor"] = None
            manifest.policy_value_json = claim
            await session.flush()
            session.info["actor"] = {
                "user_id": str(DEMO_COMMANDER_USER_ID), "role": "COMMANDER",
                "unit_id": str(DEMO_UNIT_ID),
            }
            observed = await verifier.observe(sid, u + timedelta(days=15))
            assert observed["workflow_status"] == "OBSERVED"
            assert observed["availability_status"] == "VALID"
            assert observed["interpretation"].startswith("Observed operational indicators changed")
            assert observed["leave_followup"]["status"] == "PENDING"
            assert observed["wsi"]["status"] == "INSUFFICIENT_HISTORY"
            assert observed["wsi"]["value"] is None
            assert observed["adherence"]["status"] in ("VALID", "NOT_COMPUTED", "NOT_APPLICABLE")
            assert "frozen_affected_personnel_ids" not in observed
            measured = observed["before_metrics"]
            reviewed = await verifier.review(sid, observed["expected_revision"], "Operational indicators reviewed")
            assert reviewed["workflow_status"] == "REVIEWED"
            assert reviewed["before_metrics"] == measured
            assert "actor_user_id" not in reviewed["review"]
            assert "model_a" not in str(reviewed).casefold()
            unavailable_followup = await verifier.observe(sid, u + timedelta(days=31))
            assert unavailable_followup["leave_followup"]["status"] == "INSUFFICIENT_HISTORY"
            leave_rows = list((await session.execute(select(LeaveRecord).where(
                LeaveRecord.personnel_id.in_(affected),
                LeaveRecord.start_date <= (u + timedelta(days=30)).date(),
                LeaveRecord.end_date >= u.date(),
            ))).scalars())
            session.info["actor"] = None
            for row in leave_rows:
                row.planning_classification = "UNPLANNED"
                row.actual_start_date = u.date() + timedelta(days=1)
            await session.flush()
            session.add(PolicyConfig(
                id=uuid.uuid4(), policy_key="verify.leave.coverage." + action["implementation_id"],
                policy_value_json={"complete": True, "count": len(leave_rows), "hash": _hash_rows(leave_rows)},
                version="SOURCE_COVERAGE_POLICY_V1_SYNTHETIC_DEMO", effective_from=u, created_at=u,
            ))
            await session.flush()
            session.info["actor"] = {
                "user_id": str(DEMO_COMMANDER_USER_ID), "role": "COMMANDER",
                "unit_id": str(DEMO_UNIT_ID),
            }
            followup = await verifier.observe(sid, u + timedelta(days=31))
            assert followup["workflow_status"] == "REVIEWED"
            assert followup["before_metrics"] == measured
            assert followup["leave_followup"]["status"] == "COMPLETE"
            await session.rollback()
    finally:
        await engine.dispose()


def test_zero_change_adherence_is_not_a_fabricated_success():
    result = _adherence_summary(set(), 0, 0)
    assert result == {"status": "NOT_APPLICABLE", "numerator": 0, "denominator": 0, "ratio": None}
