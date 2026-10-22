"""Minimal master create/update, immutable retry receipt and revision protection."""
import hashlib
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from app.repositories.master_data_repository import MASTERS, MasterDataRepository
from app.repositories.audit_repository import AuditRepository


def master_view(row):
    result={}
    for column in row.__table__.columns:
        value=getattr(row,column.name)
        if isinstance(value,(uuid.UUID,datetime)):
            value=value.isoformat() if isinstance(value,datetime) else str(value)
        elif isinstance(value,Decimal):
            value=float(value)
        elif hasattr(value,"isoformat"):
            value=value.isoformat()
        result[column.name]=value
    result["revision"]=hashlib.sha256(json.dumps(result,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
    return result


class MasterDataService:
    def __init__(self,session):
        self.session=session
        self.repo=MasterDataRepository(session)
        self.audit=AuditRepository(session)
        self.actor=session.info.get("actor") or {}

    def authorize(self):
        if self.actor.get("role")!="ADMIN":
            raise HTTPException(403,"ADMIN_REQUIRED")

    async def detail(self,kind,identifier):
        self.authorize()
        row=await self.repo.get(kind,identifier)
        if row is None:
            raise HTTPException(404,"MASTER_NOT_FOUND")
        return master_view(row)

    async def skills(self,limit,offset):
        self.authorize()
        rows=await self.repo.skills(limit+1,offset)
        return {"items":[master_view(row) for row in rows[:limit]],"next_offset":offset+limit if len(rows)>limit else None}

    async def references(self,kind,person_id):
        await self.detail("personnel",person_id)
        return {"items":[master_view(row) for row in await self.repo.references(kind,person_id)],"next_offset":None}

    async def add_reference(self,kind,person_id,body,key):
        from app.models import PersonSkill,PostingHistory
        self.authorize()
        digest=hashlib.sha256((self.actor["user_id"]+":"+kind+":"+key).encode()).hexdigest()
        payload_hash=hashlib.sha256((str(person_id)+body.model_dump_json()).encode()).hexdigest()
        await self.repo.lock_key(digest)
        prior=await self.repo.receipt(kind,uuid.UUID(self.actor["user_id"]),digest)
        if prior:
            if prior.metadata_json["request_hash"]!=payload_hash:
                raise HTTPException(409,"IDEMPOTENCY_CONFLICT")
            return {"id":str(prior.resource_id),"status":"CREATED","revision":prior.metadata_json["expected_revision"]}
        person=await self.repo.get("personnel",person_id,lock=True)
        if not person:
            raise HTTPException(404,"PERSONNEL_NOT_FOUND")
        data=body.model_dump()
        if kind=="person_skills":
            skill=await self.repo.get("skills",data["skill_id"])
            if not skill or not skill.is_active:
                raise HTTPException(422,"SKILL_UNAVAILABLE")
            if data["valid_until"] and data["valid_until"]<data["valid_from"]:
                raise HTTPException(422,"INVALID_SKILL_DATES")
            row=PersonSkill(personnel_id=person_id,**data)
            identifier=person_id
        else:
            if not await self.repo.get("units",data["unit_id"]):
                raise HTTPException(422,"UNIT_NOT_FOUND")
            if data["posting_end_date"] and data["posting_end_date"]<data["posting_start_date"]:
                raise HTTPException(422,"INVALID_POSTING_DATES")
            from datetime import date
            for prior_posting in await self.repo.references(kind,person_id,limit=10000):
                if (prior_posting.posting_start_date<=(data["posting_end_date"] or date.max)
                        and data["posting_start_date"]<=(prior_posting.posting_end_date or date.max)):
                    raise HTTPException(409,"POSTING_OVERLAP")
            row=PostingHistory(id=uuid.uuid4(),personnel_id=person_id,created_at=datetime.now(timezone.utc),**data)
            identifier=row.id
        try:
            async with self.session.begin_nested():
                self.session.add(row)
                await self.session.flush()
                revision=master_view(row)["revision"]
                await self.audit.log_event(None,None,"MASTER_CREATED",kind,identifier,metadata={
                    "idempotency_key_hash":digest,"request_hash":payload_hash,"expected_revision":revision})
        except IntegrityError:
            raise HTTPException(409,"REFERENCE_CONFLICT") from None
        return {"id":str(identifier),"status":"CREATED","revision":revision}

    async def validate_references(self,kind,data,identifier=None):
        if kind=="personnel" and "unit_id" in data:
            if not await self.repo.get("units",data["unit_id"]):
                raise HTTPException(422,"UNIT_NOT_FOUND")
        if kind=="units" and data.get("parent_unit_id"):
            parent=data["parent_unit_id"]
            visited={identifier} if identifier else set()
            while parent:
                if parent in visited:
                    raise HTTPException(422,"UNIT_HIERARCHY_CYCLE")
                visited.add(parent)
                row=await self.repo.get("units",parent,lock=True)
                if row is None:
                    raise HTTPException(422,"PARENT_UNIT_NOT_FOUND")
                parent=row.parent_unit_id

    async def create(self,kind,body,key):
        self.authorize()
        digest=hashlib.sha256((self.actor["user_id"]+":"+kind+":"+key).encode()).hexdigest()
        payload_hash=hashlib.sha256(body.model_dump_json().encode()).hexdigest()
        await self.repo.lock_key(digest)
        actor_id=uuid.UUID(self.actor["user_id"])
        prior=await self.repo.receipt(kind,actor_id,digest)
        if prior:
            if prior.metadata_json["request_hash"]!=payload_hash:
                raise HTTPException(409,"IDEMPOTENCY_CONFLICT")
            return {"id":str(prior.resource_id),"status":"CREATED","revision":prior.metadata_json["expected_revision"]}
        data=body.model_dump()
        await self.validate_references(kind,data)
        row=MASTERS[kind](id=uuid.uuid4(),**data)
        now=datetime.now(timezone.utc)
        for name in ("created_at","updated_at"):
            if hasattr(row,name):
                setattr(row,name,now)
        try:
            async with self.session.begin_nested():
                self.session.add(row)
                await self.session.flush()
                view=master_view(row)
                await self.audit.log_event(None,None,"MASTER_CREATED",kind,row.id,metadata={
                    "idempotency_key_hash":digest,"request_hash":payload_hash,"expected_revision":view["revision"]})
        except IntegrityError:
            raise HTTPException(409,"MASTER_IDENTIFIER_CONFLICT") from None
        return {"id":str(row.id),"status":"CREATED","revision":view["revision"]}

    async def update(self,kind,identifier,body):
        self.authorize()
        # Serialize all hierarchy edits before acquiring target/ancestor row locks.
        if kind=="units":
            await self.repo.lock_key(hashlib.sha256(b"prahari:unit-hierarchy").hexdigest())
        row=await self.repo.get(kind,identifier,lock=True)
        if row is None:
            raise HTTPException(404,"MASTER_NOT_FOUND")
        if master_view(row)["revision"]!=body.expected_revision:
            raise HTTPException(409,"STALE_REVISION")
        data=body.model_dump(exclude_unset=True,exclude={"expected_revision"})
        for name,value in data.items():
            if value is None and not row.__table__.c[name].nullable:
                raise HTTPException(422,"NULL_MASTER_FIELD")
        await self.validate_references(kind,data,identifier)
        try:
            async with self.session.begin_nested():
                for name,value in data.items():
                    setattr(row,name,value)
                row.updated_at=datetime.now(timezone.utc)
                await self.session.flush()
                await self.audit.log_event(None,None,"MASTER_UPDATED",kind,row.id)
        except IntegrityError:
            raise HTTPException(409,"MASTER_IDENTIFIER_CONFLICT") from None
        return master_view(row)
