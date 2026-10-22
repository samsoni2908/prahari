"""Master writes, retry and stale revisions on rollback PostgreSQL fixtures."""
import uuid
from datetime import date
import pytest
from fastapi import HTTPException
from tests.test_ingestion_functional import import_session
from app.schemas.master_data import UnitCreate, UnitPatch, PersonnelCreate, SkillCreate, PersonSkillInput, PostingInput
from app.services.master_data_service import MasterDataService


@pytest.mark.asyncio
async def test_master_create_retry_revision_hierarchy_and_references(import_session):
    session, _ = import_session
    svc = MasterDataService(session)
    code = str(uuid.uuid4())
    body = UnitCreate(unit_code=code, unit_name="Rollback unit", unit_type="TEST", sanctioned_strength=5)
    created = await svc.create("units", body, "master-unit-001")
    assert created == await svc.create("units", body, "master-unit-001")
    unit_id = uuid.UUID(created["id"])
    updated = await svc.update("units", unit_id, UnitPatch(expected_revision=created["revision"], unit_name="Changed unit"))
    assert updated["unit_name"] == "Changed unit"
    with pytest.raises(HTTPException) as stale:
        await svc.update("units", unit_id, UnitPatch(expected_revision=created["revision"], unit_name="Stale"))
    assert stale.value.status_code == 409
    with pytest.raises(HTTPException) as cyclic:
        await svc.update("units", unit_id, UnitPatch(expected_revision=updated["revision"], parent_unit_id=unit_id))
    assert cyclic.value.status_code == 422
    person = await svc.create("personnel", PersonnelCreate(personnel_code=code, pseudo_id=code,
        full_name="Rollback person", unit_id=unit_id, rank_or_grade="TEST", role_title="TEST"), "master-person-001")
    person_id = uuid.UUID(person["id"])
    skill = await svc.create("skills", SkillCreate(skill_code=code, skill_name="Rollback skill"), "master-skill-001")
    reference = PersonSkillInput(skill_id=uuid.UUID(skill["id"]), proficiency_level=3, valid_from=date(2026,1,1))
    added = await svc.add_reference("person_skills", person_id, reference, "master-reference-001")
    assert added == await svc.add_reference("person_skills", person_id, reference, "master-reference-001")
    assert len((await svc.references("person_skills", person_id))["items"]) == 1
    posting = PostingInput(unit_id=unit_id, posting_start_date=date(2026,1,1), posting_type="DEMO")
    await svc.add_reference("posting_history", person_id, posting, "master-posting-001")
    with pytest.raises(HTTPException) as overlap:
        await svc.add_reference("posting_history", person_id, posting, "master-posting-002")
    assert overlap.value.status_code == 409


@pytest.mark.asyncio
async def test_master_idempotency_conflict_and_role(import_session):
    session, person = import_session
    svc = MasterDataService(session)
    body = SkillCreate(skill_code=str(uuid.uuid4()), skill_name="Original")
    await svc.create("skills", body, "master-conflict-001")
    with pytest.raises(HTTPException) as conflict:
        await svc.create("skills", body.model_copy(update={"skill_name":"Changed"}), "master-conflict-001")
    assert conflict.value.status_code == 409
    session.info["actor"] = {**svc.actor, "role":"COMMANDER", "unit_id":str(person.unit_id)}
    with pytest.raises(HTTPException) as denied:
        await MasterDataService(session).detail("personnel", person.id)
    assert denied.value.status_code == 403
