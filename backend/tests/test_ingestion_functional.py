"""Admin source intake against PostgreSQL; all source/audit fixture writes roll back."""
import uuid
from datetime import datetime, timezone
from unittest.mock import patch
import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from app.config import settings
from app.models import Personnel, User, Training, AuditEvent
from app.schemas.ingestion import ImportInput, ImportCommit
from app.services.ingestion_service import IngestionService


@pytest_asyncio.fixture
async def import_session():
    engine=create_async_engine(settings.DATABASE_URL, hide_parameters=True)
    async with engine.connect() as connection:
        transaction=await connection.begin()
        async with AsyncSession(bind=connection, expire_on_commit=False) as session:
            admin=(await session.execute(select(User).where(User.role=="ADMIN", User.is_active.is_(True)).limit(1))).scalar_one()
            person=(await session.execute(select(Personnel).limit(1))).scalar_one()
            session.info["actor"]={"user_id":str(admin.id),"role":"ADMIN"}
            yield session,person
        if transaction.is_active:
            await transaction.rollback()
    await engine.dispose()


def source(person, suffix="", hours="8"):
    return ImportInput(dataset_type="training", source_timestamp=datetime(2026,1,3,tzinfo=timezone.utc),
        csv_data="personnel_id,training_name,start_date,end_date,hours,status\n"+
        f"{person.id},Rollback training{suffix},2026-01-01,2026-01-02,{hours},COMPLETED\n")


@pytest.mark.asyncio
async def test_validate_commit_replay_hash_and_history(import_session):
    session,person=import_session
    svc=IngestionService(session)
    body=source(person)
    validated=await svc.validate(body)
    assert validated.status=="VALIDATED" and not validated.errors
    session.info["actor"]={**svc.actor,"_operational_import":"training"}
    assert not (await session.execute(select(Training).where(Training.training_name=="Rollback training"))).scalars().all()
    session.info["actor"]=svc.actor
    commit=ImportCommit(**body.model_dump(),checksum=validated.checksum,expected_revision=validated.revision)
    result=await svc.commit(validated.id,commit,"import-key-001")
    assert result.status=="COMMITTED" and result.row_count==1
    assert result==await svc.commit(validated.id,commit,"import-key-001")
    session.info["actor"]={**svc.actor,"_operational_import":"training"}
    rows=(await session.execute(select(Training).where(Training.training_name=="Rollback training"))).scalars().all()
    assert len(rows)==1 and rows[0].created_at.tzinfo is not None
    session.info["actor"]=svc.actor
    events=(await session.execute(select(AuditEvent).where(AuditEvent.resource_id==validated.id))).scalars().all()
    assert len(events)==2 and events[-1].metadata_json["source_hash"]==validated.checksum
    assert "Rollback training" not in str([e.metadata_json for e in events])


@pytest.mark.asyncio
async def test_invalid_rows_validation_required_and_scope(import_session):
    session,person=import_session
    svc=IngestionService(session)
    bad=source(person,hours="-9")
    rejected=await svc.validate(bad)
    assert rejected.status=="REJECTED" and rejected.errors[0].row==2
    with pytest.raises(HTTPException) as not_validated:
        await svc.commit(rejected.id,ImportCommit(**bad.model_dump(),checksum=rejected.checksum,
            expected_revision=rejected.revision),"import-key-002")
    assert not_validated.value.status_code==409
    invalid_fk=source(person).model_copy(update={"csv_data":source(person).csv_data.replace(str(person.id),str(uuid.uuid4()))})
    assert any(e.code=="FOREIGN_KEY_NOT_FOUND" for e in (await svc.validate(invalid_fk)).errors)
    session.info["actor"]={**svc.actor,"role":"COMMANDER"}
    with pytest.raises(HTTPException) as denied:
        await IngestionService(session).validate(source(person))
    assert denied.value.status_code==403


@pytest.mark.asyncio
async def test_no_partial_commit_when_audit_fails(import_session):
    session,person=import_session
    svc=IngestionService(session)
    body=source(person," audit failure")
    validation=await svc.validate(body)
    commit=ImportCommit(**body.model_dump(),checksum=validation.checksum,expected_revision=validation.revision)
    with patch.object(svc.audit,"log_event",side_effect=RuntimeError("injected audit failure")):
        with pytest.raises(RuntimeError):
            await svc.commit(validation.id,commit,"import-key-003")
    session.info["actor"]={**svc.actor,"_operational_import":"training"}
    assert not (await session.execute(select(Training.id).where(Training.training_name=="Rollback training audit failure"))).all()


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["duties", "rest_records", "leave_records", "deployments", "training", "staffing"])
async def test_all_supported_operational_source_imports(import_session, kind):
    from app.schemas.master_data import UnitCreate, PersonnelCreate
    from app.services.master_data_service import MasterDataService
    session, _ = import_session
    master = MasterDataService(session)
    code = str(uuid.uuid4())
    unit = await master.create("units", UnitCreate(unit_code=code, unit_name="Rollback intake", unit_type="TEST", sanctioned_strength=5), "source-unit-001")
    person = await master.create("personnel", PersonnelCreate(personnel_code=code, pseudo_id=code,
        full_name="Rollback intake", unit_id=uuid.UUID(unit["id"]), rank_or_grade="TEST", role_title="TEST"), "source-person-001")
    rows = {
        "duties": {"personnel_id":person["id"],"unit_id":unit["id"],"duty_date":"2026-01-01",
            "start_at":"2026-01-01T08:00:00Z","end_at":"2026-01-01T16:00:00Z","hours":"8", "duty_type":"TEST", "shift_type":"DAY", "is_night":"false"},
        "rest_records": {"personnel_id":person["id"],"record_date":"2026-01-01", "rest_hours":"12", "rest_gap_hours":"16", "source":"TEST", "data_quality_status":"VALID"},
        "leave_records": {"personnel_id":person["id"],"leave_type":"TEST", "start_date":"2026-01-01", "end_date":"2026-01-02", "days":"2", "status":"COMPLETED", "actual_start_date":"2026-01-01", "actual_end_date":"2026-01-02"},
        "deployments": {"personnel_id":person["id"],"unit_id":unit["id"],"deployment_type":"TEST", "start_date":"2026-01-01", "end_date":"2026-01-02", "intensity_level":"2"},
        "training": {"personnel_id":person["id"],"training_name":"TEST", "start_date":"2026-01-01", "end_date":"2026-01-02", "hours":"8", "status":"COMPLETED"},
        "staffing": {"unit_id":unit["id"],"record_date":"2026-01-01", "sanctioned_strength":"5", "available_strength":"4", "required_strength":"5", "coverage_percent":"80"},
    }
    row = rows[kind]
    body = ImportInput(dataset_type=kind, source_timestamp=datetime(2026,1,3,tzinfo=timezone.utc),
        csv_data=",".join(row)+"\n"+",".join(row.values())+"\n")
    service = IngestionService(session)
    validation = await service.validate(body)
    assert validation.status == "VALIDATED", validation.errors
    result = await service.commit(validation.id, ImportCommit(**body.model_dump(), checksum=validation.checksum,
        expected_revision=validation.revision), "source-commit-001")
    assert result.status == "COMMITTED" and result.row_count == 1
