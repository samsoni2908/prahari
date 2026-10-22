"""Necessary Admin master writes; no welfare analytics or private fields."""
from uuid import UUID
from fastapi import APIRouter, Depends, Header, Query
from app.security.deps import get_db_with_rls, require_roles
from app.schemas.master_data import UnitCreate, UnitPatch, PersonnelCreate, PersonnelPatch, SkillCreate, PersonSkillInput, PostingInput
from app.services.master_data_service import MasterDataService, master_view

router=APIRouter(prefix="/api/v1/admin",tags=["master-data"],dependencies=[Depends(require_roles("ADMIN"))])


@router.post("/units",status_code=201)
async def create_unit(body:UnitCreate,key:str=Header(...,alias="Idempotency-Key",min_length=8,max_length=128),
    db=Depends(get_db_with_rls,scope="function")):
    return await MasterDataService(db).create("units",body,key)


@router.get("/units/{identifier}")
async def unit_detail(identifier:UUID,db=Depends(get_db_with_rls,scope="function")):
    return await MasterDataService(db).detail("units",identifier)


@router.patch("/units/{identifier}")
async def update_unit(identifier:UUID,body:UnitPatch,db=Depends(get_db_with_rls,scope="function")):
    return await MasterDataService(db).update("units",identifier,body)


@router.post("/personnel",status_code=201)
async def create_person(body:PersonnelCreate,key:str=Header(...,alias="Idempotency-Key",min_length=8,max_length=128),
    db=Depends(get_db_with_rls,scope="function")):
    return await MasterDataService(db).create("personnel",body,key)


@router.get("/personnel/{identifier}")
async def person_detail(identifier:UUID,db=Depends(get_db_with_rls,scope="function")):
    return await MasterDataService(db).detail("personnel",identifier)


@router.patch("/personnel/{identifier}")
async def update_person(identifier:UUID,body:PersonnelPatch,db=Depends(get_db_with_rls,scope="function")):
    return await MasterDataService(db).update("personnel",identifier,body)


@router.post("/skills",status_code=201)
async def create_skill(body:SkillCreate,key:str=Header(...,alias="Idempotency-Key",min_length=8,max_length=128),
    db=Depends(get_db_with_rls,scope="function")):
    return await MasterDataService(db).create("skills",body,key)


@router.get("/skills")
async def list_skills(limit:int=Query(100,ge=1,le=200),offset:int=Query(0,ge=0),db=Depends(get_db_with_rls,scope="function")):
    return await MasterDataService(db).skills(limit,offset)


@router.get("/personnel/{identifier}/skills")
async def person_skills(identifier:UUID,db=Depends(get_db_with_rls,scope="function")):
    return await MasterDataService(db).references("person_skills",identifier)


@router.post("/personnel/{identifier}/skills",status_code=201)
async def assign_skill(identifier:UUID,body:PersonSkillInput,key:str=Header(...,alias="Idempotency-Key",min_length=8,max_length=128),
    db=Depends(get_db_with_rls,scope="function")):
    return await MasterDataService(db).add_reference("person_skills",identifier,body,key)


@router.get("/personnel/{identifier}/postings")
async def postings(identifier:UUID,db=Depends(get_db_with_rls,scope="function")):
    return await MasterDataService(db).references("posting_history",identifier)


@router.post("/personnel/{identifier}/postings",status_code=201)
async def record_posting(identifier:UUID,body:PostingInput,key:str=Header(...,alias="Idempotency-Key",min_length=8,max_length=128),
    db=Depends(get_db_with_rls,scope="function")):
    return await MasterDataService(db).add_reference("posting_history",identifier,body,key)
