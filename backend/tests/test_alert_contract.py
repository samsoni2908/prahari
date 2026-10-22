"""Live PostgreSQL alert actions with rollback-only fixtures; no retained changes."""
import uuid
from datetime import datetime, timezone
import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from app.config import settings
from app.models import Alert, User, AuditEvent
from app.services.alert_service import AlertService, project
from app.schemas.alerts import AlertAction


@pytest_asyncio.fixture
async def alert_session():
    engine = create_async_engine(settings.DATABASE_URL, hide_parameters=True)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        async with AsyncSession(bind=connection, expire_on_commit=False) as session:
            officer = (await session.execute(select(User).where(User.role == "COMMANDER", User.is_active.is_(True), User.unit_id.is_not(None)).limit(1))).scalar_one()
            row = Alert(id=uuid.uuid4(), unit_id=officer.unit_id, alert_type="OPERATIONAL_MODEL_A_HIGH",
                severity="HIGH", source_type="MODEL_A", status="OPEN",
                message="Sustained elevated operational workload/recovery attention.", created_at=datetime.now(timezone.utc))
            session.add(row)
            await session.flush()
            session.info["actor"] = {"user_id": str(officer.id), "role": officer.role, "unit_id": str(officer.unit_id)}
            yield session, row
        if transaction.is_active:
            await transaction.rollback()
    await engine.dispose()


@pytest.mark.asyncio
async def test_alert_actions_replay_and_stale_revision(alert_session):
    session, row = alert_session
    service = AlertService(session)
    body = AlertAction(expected_revision=project(row).revision, reason_code="REVIEW_STARTED")
    acknowledged = await service.action(row.id, body, "ack-key-0001", "ACKNOWLEDGED")
    assert acknowledged.status == "ACKNOWLEDGED"
    replay = await service.action(row.id, body, "ack-key-0001", "ACKNOWLEDGED")
    assert replay == acknowledged
    with pytest.raises(HTTPException) as stale:
        await service.action(row.id, body, "ack-key-0002", "RESOLVED")
    assert stale.value.status_code == 409
    resolved = await service.action(row.id, AlertAction(expected_revision=acknowledged.revision,
        reason_code="REVIEW_COMPLETE"), "resolve-0001", "RESOLVED")
    assert resolved.status == "RESOLVED" and resolved.resolved_at.tzinfo is not None
    # An old acknowledge replay retains the original response after later resolution.
    assert await service.action(row.id, body, "ack-key-0001", "ACKNOWLEDGED") == acknowledged
    events = (await session.execute(select(AuditEvent).where(AuditEvent.resource_id == row.id))).scalars().all()
    assert len(events) == 2
    assert all("reason_code" in event.metadata_json for event in events)
    assert "personnel_id" not in resolved.model_dump() and "source_id" not in resolved.model_dump()


@pytest.mark.asyncio
async def test_alert_action_collision_and_foreign_scope(alert_session):
    session, row = alert_session
    service = AlertService(session)
    body = AlertAction(expected_revision=project(row).revision, reason_code="REVIEW_STARTED")
    await service.action(row.id, body, "ack-key-0001", "ACKNOWLEDGED")
    with pytest.raises(HTTPException) as collision:
        await service.action(row.id, body.model_copy(update={"reason_code": "DIFFERENT_REASON"}), "ack-key-0001", "ACKNOWLEDGED")
    assert collision.value.status_code == 409
    session.info["actor"] = {**service.actor, "unit_id": str(uuid.uuid4())}
    with pytest.raises(HTTPException) as hidden:
        await AlertService(session).action(row.id, body, "ack-key-0002", "ACKNOWLEDGED")
    assert hidden.value.status_code == 404
    session.info["actor"] = {**service.actor, "role": "ADMIN"}
    with pytest.raises(HTTPException) as denied:
        await AlertService(session).list()
    assert denied.value.status_code == 403


@pytest.mark.asyncio
async def test_alert_cursor_bounds_and_serialization(alert_session):
    session, row = alert_session
    service = AlertService(session)
    cursor = service.encode_cursor(row, "OPEN")
    assert service.decode_cursor(cursor, "OPEN") == (row.created_at, row.id)
    for invalid in ("garbage", cursor + "!", cursor):
        with pytest.raises(HTTPException) as rejected:
            service.decode_cursor(invalid, "RESOLVED")
        assert rejected.value.status_code == 400
    with pytest.raises(HTTPException) as rejected:
        await service.list(201)
    assert rejected.value.status_code == 422
    view = project(row)
    assert view.model_validate_json(view.model_dump_json()) == view
