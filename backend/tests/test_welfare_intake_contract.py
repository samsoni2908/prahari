"""Purpose-scoped identity and case-open contracts with rollback-only PostgreSQL."""
import uuid
import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from app.config import settings
from app.models import Personnel, User, SupportRequest, WelfareCaseAction, AuditEvent
from app.schemas.welfare_intake import NamedSearch, OpenCase
from app.services.welfare_intake_service import WelfareIntakeService


@pytest_asyncio.fixture
async def intake_session():
    engine = create_async_engine(settings.DATABASE_URL, hide_parameters=True)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        async with AsyncSession(bind=connection, expire_on_commit=False) as session:
            officer = (await session.execute(select(User).where(User.role == "WELFARE_OFFICER",
                User.is_active.is_(True), User.unit_id.is_not(None)).limit(1))).scalar_one()
            person = (await session.execute(select(Personnel).where(Personnel.unit_id == officer.unit_id).limit(1))).scalar_one()
            session.info["actor"] = {"user_id": str(officer.id), "role": officer.role, "unit_id": str(officer.unit_id)}
            yield session, person
        if transaction.is_active:
            await transaction.rollback()
    await engine.dispose()


@pytest.mark.asyncio
async def test_identity_search_is_bounded_and_private_field_free(intake_session):
    session, person = intake_session
    service = WelfareIntakeService(session)
    result = await service.search(NamedSearch(field="service_code", query=person.personnel_code,
        purpose_reason="Human support case handling", limit=1))
    assert len(result.items) == 1 and result.items[0].id == person.id
    assert set(result.items[0].model_dump()) == {"id", "full_name", "personnel_code", "pseudo_id"}
    events = (await session.execute(select(AuditEvent).where(AuditEvent.action == "CASE_IDENTITY_SEARCH"))).scalars().all()
    assert events and all(person.personnel_code not in str(event.metadata_json) for event in events)
    actor = session.info["actor"]
    session.info["actor"] = {**actor, "unit_id": str(uuid.uuid4())}
    assert not (await WelfareIntakeService(session).search(NamedSearch(field="service_code",
        query=person.personnel_code, purpose_reason="Human support case handling"))).items
    session.info["actor"] = {**actor, "role": "COMMANDER"}
    with pytest.raises(HTTPException) as denied:
        await WelfareIntakeService(session).search(NamedSearch(field="name", query="Any name", purpose_reason="Human support case handling"))
    assert denied.value.status_code == 403


@pytest.mark.asyncio
async def test_case_open_replay_collision_and_assignment(intake_session):
    session, person = intake_session
    service = WelfareIntakeService(session)
    body = OpenCase(personnel_id=person.id, request_type="LEAVE_ASSISTANCE",
        personnel_visible_reason="Discuss recovery opportunity and leave support.")
    created = await service.open(body, "case-open-0001")
    assert await service.open(body, "case-open-0001") == created
    case = (await session.execute(select(SupportRequest).where(SupportRequest.id == created.id))).scalar_one()
    assert str(case.assigned_to_user_id) == service.actor["user_id"]
    actions = (await session.execute(select(WelfareCaseAction).where(WelfareCaseAction.case_id == case.id))).scalars().all()
    assert len(actions) == 1 and actions[0].action_type == "ASSIGN"
    assert created.model_dump().keys() == {"id", "status", "assigned_to_me", "created_at"}
    with pytest.raises(HTTPException) as collision:
        await service.open(body.model_copy(update={"priority": "URGENT"}), "case-open-0001")
    assert collision.value.status_code == 409
    with pytest.raises(HTTPException) as hidden:
        await service.open(body.model_copy(update={"personnel_id": uuid.uuid4()}), "case-open-0002")
    assert hidden.value.status_code == 404
