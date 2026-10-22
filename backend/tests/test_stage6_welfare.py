"""Stage-6 welfare writes run only on the explicit Stage-4 disposable DB."""

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.models import Personnel, SupportRequest, Unit, User, WelfareCaseAction, WellbeingPrivate
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.operational_repository import OperationalRepository
from app.repositories.personnel_repository import PersonnelRepository
from app.repositories.unit_repository import UnitRepository
from app.repositories.wellbeing_repository import WellbeingRepository
from app.services.personnel_service import PersonnelService
from app.services.welfare_case_service import WelfareCaseService
from app.services.notification_service import NotificationService
from app.services.personnel_transfer_service import PersonnelTransferService
from app.security.password import hash_password
from tests.test_stage4b_balance_decision import (
    TEST_DB_URL, DEMO_PERSONNEL_USER_ID, DEMO_ADMIN_USER_ID,
)


@pytest.mark.asyncio
async def test_support_request_assignment_visibility_and_closure():
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    try:
        async with factory() as session:
            person_user = (await session.execute(select(User).where(
                User.id == DEMO_PERSONNEL_USER_ID,
            ))).scalar_one()
            assert person_user.personnel_id
            unit_id = person_user.unit_id
            welfare_user = (await session.execute(select(User).where(
                User.role == "WELFARE_OFFICER", User.unit_id == unit_id,
                User.is_active.is_(True),
            ).limit(1))).scalar_one()
            commander_user = (await session.execute(select(User).where(
                User.role == "COMMANDER", User.unit_id == unit_id,
                User.is_active.is_(True),
            ).limit(1))).scalar_one()
            target_officer = User(
                username="stage6_reassign_" + uuid.uuid4().hex,
                password_hash=hash_password("synthetic-disposable-only"),
                role="WELFARE_OFFICER", unit_id=unit_id, is_active=True,
            )
            session.add(target_officer)
            await session.flush()
            session.info["actor"] = {
                "user_id": str(person_user.id), "role": "PERSONNEL",
                "personnel_id": str(person_user.personnel_id), "unit_id": str(unit_id),
            }
            personnel = PersonnelService(
                PersonnelRepository(session), UnitRepository(session),
                WellbeingRepository(session), AnalyticsRepository(session),
                OperationalRepository(session), AuditRepository(session),
            )
            key = "case-" + str(uuid.uuid4())
            created = await personnel.create_support_request(
                person_user.personnel_id, "LEAVE_ASSISTANCE", "MEDIUM",
                "Please arrange a private leave discussion", key,
            )
            case_id = uuid.UUID(created["id"])
            assert created["status"] == "OPEN" and created["priority"] == "NORMAL"
            replay = await personnel.create_support_request(
                person_user.personnel_id, "LEAVE_ASSISTANCE", "MEDIUM",
                "Please arrange a private leave discussion", key,
            )
            assert replay["replay_safe"] and replay["id"] == created["id"]
            with pytest.raises(HTTPException) as collision:
                await personnel.create_support_request(
                    person_user.personnel_id, "LEAVE_ASSISTANCE", "MEDIUM",
                    "Please arrange a different private discussion", key,
                )
            assert collision.value.status_code == 409

            for role in ("COMMANDER", "WELFARE_OFFICER", "ADMIN"):
                session.info["actor"] = {
                    "user_id": str({"WELFARE_OFFICER": welfare_user.id,
                                    "COMMANDER": commander_user.id,
                                    "ADMIN": DEMO_ADMIN_USER_ID}[role]),
                    "role": role, "unit_id": str(unit_id) if role != "ADMIN" else None,
                }
                assert (await session.execute(select(WellbeingPrivate).limit(1))).scalar_one_or_none() is None
                if role in ("COMMANDER", "ADMIN"):
                    assert (await session.execute(select(SupportRequest).where(
                        SupportRequest.id == case_id,
                    ))).scalar_one_or_none() is None

            service = WelfareCaseService(session)
            session.info["actor"] = {
                "user_id": str(welfare_user.id), "role": "WELFARE_OFFICER",
                "unit_id": str(unit_id),
            }
            assigned = await service.claim(case_id, "Review requested support", "assign-" + str(case_id))
            assert assigned["status"] == "ASSIGNED"
            assert (await service.claim(case_id, "Review requested support", "assign-" + str(case_id)))["replay_safe"]
            priority = await service.set_priority(
                case_id, "URGENT", "Personnel requested a prompt human response",
                "priority-" + str(case_id),
            )
            assert priority["priority"] == "URGENT"
            assert (await service.set_priority(
                case_id, "URGENT", "Personnel requested a prompt human response",
                "priority-" + str(case_id),
            ))["replay_safe"]
            welfare_notices = await NotificationService(session).list()
            assert len(welfare_notices) == 1
            assert "private leave discussion" not in str(welfare_notices).lower()
            with pytest.raises(HTTPException) as arbitrary_template:
                await NotificationService(session).emit(
                    "ARBITRARY_MESSAGE", welfare_user.id, case_id, "bad-event",
                )
            assert arbitrary_template.value.status_code == 422
            private = await service.action(
                case_id, "DISCUSSION", "Confidential officer context", "OFFICER",
                None, "IN_PROGRESS", "private-" + str(case_id),
            )
            moved_case = await service.reassign(
                case_id, target_officer.id, "Current officer handing over case",
                "reassign-" + str(case_id),
            )
            assert moved_case["assigned_to_user_id"] == str(target_officer.id)
            assert (await service.reassign(
                case_id, target_officer.id, "Current officer handing over case",
                "reassign-" + str(case_id),
            ))["replay_safe"]
            with pytest.raises(HTTPException) as old_officer:
                await service.list_actions(case_id)
            assert old_officer.value.status_code == 404
            session.info["actor"] = {
                "user_id": str(target_officer.id), "role": "WELFARE_OFFICER",
                "unit_id": str(unit_id),
            }
            visible = await service.action(
                case_id, "FOLLOW_UP", "We will follow up shortly", "PERSONNEL",
                __import__("datetime").date.today(), None, "visible-" + str(case_id),
            )
            assert private["visibility"] == "OFFICER" and visible["visibility"] == "PERSONNEL"
            with pytest.raises(HTTPException) as empty_close:
                await service.action(case_id, "CLOSE", None, "PERSONNEL", None, None, "bad-close-" + str(case_id))
            assert empty_close.value.status_code == 422
            closed = await service.action(
                case_id, "CLOSE", "Requested support has been completed", "PERSONNEL",
                None, None, "close-" + str(case_id),
            )
            assert closed["case_status"] == "CLOSED"
            assert (await session.execute(select(SupportRequest).where(
                SupportRequest.id == case_id,
            ))).scalar_one().status == "CLOSED"
            await AuditRepository(session).log_event(
                target_officer.id, "WELFARE_OFFICER", "CASE_CONTENT_ACCESS",
                "support_requests", case_id,
            )
            session.info["actor"] = {
                "user_id": str(person_user.id), "role": "PERSONNEL",
                "personnel_id": str(person_user.personnel_id), "unit_id": str(unit_id),
            }
            own_actions = await service.list_actions(case_id)
            assert {row["visibility"] for row in own_actions} == {"PERSONNEL"}
            assert "Confidential officer context" not in str(own_actions)
            privacy_history = await personnel.get_privacy_history(person_user.personnel_id)
            assert any(row["action"] == "CASE_CONTENT_ACCESS" and
                       row["actor_role"] == "WELFARE_OFFICER" for row in privacy_history)
            assert len((await session.execute(select(WelfareCaseAction).where(
                WelfareCaseAction.case_id == case_id,
            ))).scalars().all()) == len(own_actions)
            notices = await NotificationService(session).list()
            assert len(notices) == 2
            assert await NotificationService(session).unread_count() == 2
            assert "Confidential officer context" not in str(notices)
            marked = await NotificationService(session).mark_read(uuid.UUID(notices[0]["id"]))
            assert marked["read_at"]
            assert await NotificationService(session).unread_count() == 1
            assert (await NotificationService(session).mark_read(uuid.UUID(notices[0]["id"])))["read_at"] == marked["read_at"]
            second = await personnel.create_support_request(
                person_user.personnel_id, "FAMILY_PERSONAL", "NORMAL",
                "Please open a separate new family support case", "second-" + str(uuid.uuid4()),
            )
            session.info["actor"] = {
                "user_id": str(welfare_user.id), "role": "WELFARE_OFFICER", "unit_id": str(unit_id),
            }
            await service.claim(uuid.UUID(second["id"]), "Assign new request", "assign-" + second["id"])
            session.info["actor"] = None
            other_unit = (await session.execute(select(Unit.id).where(Unit.id != unit_id).limit(1))).scalar_one()
            session.info["actor"] = {
                "user_id": str(DEMO_ADMIN_USER_ID), "role": "ADMIN", "unit_id": None,
            }
            moved = await PersonnelTransferService(session).transfer(
                person_user.personnel_id, other_unit, "UNIT_TRANSFER",
            )
            assert moved["withdrawn_cases"] == 1
            session.info["actor"] = None
            transferred = (await session.execute(select(SupportRequest).where(
                SupportRequest.id == uuid.UUID(second["id"]),
            ))).scalar_one()
            assert transferred.status == "WITHDRAWN"
            assert transferred.assigned_to_user_id is None
            session.info["actor"] = {
                "user_id": str(welfare_user.id), "role": "WELFARE_OFFICER", "unit_id": str(unit_id),
            }
            assert await NotificationService(session).list() == []
            await session.rollback()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_owner_withdraw_and_cross_scope_denials():
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    try:
        async with factory() as session:
            owner = (await session.execute(select(User).where(User.id == DEMO_PERSONNEL_USER_ID))).scalar_one()
            other_person = (await session.execute(select(User).where(
                User.role == "PERSONNEL", User.personnel_id != owner.personnel_id,
                User.is_active.is_(True),
            ).limit(1))).scalar_one()
            other_officer = (await session.execute(select(User).where(
                User.role == "WELFARE_OFFICER", User.unit_id != owner.unit_id,
                User.is_active.is_(True),
            ).limit(1))).scalar_one()
            session.info["actor"] = {
                "user_id": str(owner.id), "role": "PERSONNEL",
                "personnel_id": str(owner.personnel_id), "unit_id": str(owner.unit_id),
            }
            personnel = PersonnelService(
                PersonnelRepository(session), UnitRepository(session),
                WellbeingRepository(session), AnalyticsRepository(session),
                OperationalRepository(session), AuditRepository(session),
            )
            created = await personnel.create_support_request(
                owner.personnel_id, "LEAVE_ASSISTANCE", "NORMAL",
                "Please review my private leave request", "withdraw-" + str(uuid.uuid4()),
            )
            case_id = uuid.UUID(created["id"])
            service = WelfareCaseService(session)
            session.info["actor"] = {
                "user_id": str(other_person.id), "role": "PERSONNEL",
                "personnel_id": str(other_person.personnel_id), "unit_id": str(other_person.unit_id),
            }
            with pytest.raises(HTTPException) as cross_person:
                await service.list_actions(case_id)
            assert cross_person.value.status_code == 404
            with pytest.raises(HTTPException) as cross_withdraw:
                await service.withdraw(case_id, "REQUEST_CANCELLED")
            assert cross_withdraw.value.status_code == 404
            session.info["actor"] = {
                "user_id": str(other_officer.id), "role": "WELFARE_OFFICER",
                "unit_id": str(other_officer.unit_id),
            }
            with pytest.raises(HTTPException) as cross_unit:
                await service.claim(case_id, "Review this request", "cross-" + str(case_id))
            assert cross_unit.value.status_code == 404
            session.info["actor"] = {"user_id": str(DEMO_ADMIN_USER_ID), "role": "ADMIN"}
            with pytest.raises(HTTPException) as admin:
                await service.claim(case_id, "Review this request", "admin-" + str(case_id))
            assert admin.value.status_code == 403
            session.info["actor"] = {
                "user_id": str(owner.id), "role": "PERSONNEL",
                "personnel_id": str(owner.personnel_id), "unit_id": str(owner.unit_id),
            }
            assert (await service.withdraw(case_id, "REQUEST_CANCELLED"))["status"] == "WITHDRAWN"
            assert (await service.withdraw(case_id, "REQUEST_CANCELLED"))["replay_safe"]
            await session.rollback()
    finally:
        await engine.dispose()
