"""Locked allowlisted master rows and actor-scoped creation receipts."""
from sqlalchemy import select, text
from app.models import Unit, Personnel, Skill, AuditEvent, PersonSkill, PostingHistory

MASTERS={"units":Unit,"personnel":Personnel,"skills":Skill}


class MasterDataRepository:
    def __init__(self, session):
        self.session=session

    async def lock_key(self, digest):
        await self.session.execute(text("SELECT pg_advisory_xact_lock(:key)"),
            {"key":int.from_bytes(bytes.fromhex(digest)[:8],"big",signed=True)})

    async def get(self, kind, identifier, lock=False):
        query=select(MASTERS[kind]).where(MASTERS[kind].id==identifier)
        return (await self.session.execute(query.with_for_update() if lock else query)).scalar_one_or_none()

    async def receipt(self, kind, actor, digest):
        return (await self.session.execute(select(AuditEvent).where(AuditEvent.action=="MASTER_CREATED",
            AuditEvent.resource_type==kind,AuditEvent.actor_user_id==actor,
            AuditEvent.metadata_json["idempotency_key_hash"].astext==digest))).scalar_one_or_none()

    async def skills(self,limit,offset):
        return list((await self.session.execute(select(Skill).order_by(Skill.skill_code,Skill.id)
            .offset(offset).limit(limit))).scalars())

    async def references(self,kind,person_id,limit=200):
        model=PersonSkill if kind=="person_skills" else PostingHistory
        return list((await self.session.execute(select(model).where(model.personnel_id==person_id)
            .order_by(*model.__table__.primary_key.columns).limit(limit))).scalars())
