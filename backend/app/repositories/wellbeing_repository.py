import uuid
from datetime import date
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Personnel, SupportRequest, WellbeingConsent, WellbeingPrivate, WellbeingResult
from app.security.scope import require_unit


class WellbeingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # Consent
    async def get_latest_consent(self, personnel_id: uuid.UUID) -> Optional[WellbeingConsent]:
        stmt = (
            select(WellbeingConsent)
            .where(WellbeingConsent.personnel_id == personnel_id)
            .order_by(WellbeingConsent.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def record_consent(self, consent: WellbeingConsent) -> WellbeingConsent:
        self.session.add(consent)
        await self.session.flush()
        return consent

    # Private self-checks (Guarded by PostgreSQL RLS)
    async def list_self_checks(self, personnel_id: uuid.UUID, limit: int = 20) -> List[WellbeingPrivate]:
        stmt = (
            select(WellbeingPrivate)
            .where(WellbeingPrivate.personnel_id == personnel_id)
            .order_by(WellbeingPrivate.assessment_date.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def submit_self_check(self, check: WellbeingPrivate) -> WellbeingPrivate:
        self.session.add(check)
        await self.session.flush()
        return check

    async def record_wellbeing_result(self, result: WellbeingResult) -> WellbeingResult:
        self.session.add(result)
        await self.session.flush()
        return result

    async def list_wellbeing_results(self, personnel_id: uuid.UUID, limit: int = 20) -> List[WellbeingResult]:
        stmt = (
            select(WellbeingResult)
            .where(WellbeingResult.personnel_id == personnel_id)
            .order_by(WellbeingResult.assessment_date.desc(), WellbeingResult.created_at.desc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_latest_wellbeing_result(self, personnel_id: uuid.UUID) -> Optional[WellbeingResult]:
        stmt = (
            select(WellbeingResult)
            .where(WellbeingResult.personnel_id == personnel_id)
            .order_by(WellbeingResult.assessment_date.desc(), WellbeingResult.created_at.desc())
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    # Support Requests
    async def list_support_requests_for_personnel(self, personnel_id: uuid.UUID) -> List[SupportRequest]:
        stmt = (
            select(SupportRequest)
            .where(SupportRequest.personnel_id == personnel_id)
            .order_by(SupportRequest.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_all_support_requests(self, status_filter: Optional[str] = None) -> List[SupportRequest]:
        stmt = select(SupportRequest).order_by(SupportRequest.created_at.desc())
        if status_filter:
            stmt = stmt.where(SupportRequest.status == status_filter)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_support_request_by_id(self, request_id: uuid.UUID) -> Optional[SupportRequest]:
        stmt = select(SupportRequest).where(SupportRequest.id == request_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def lock_support_request(self, request_id):
        stmt = select(SupportRequest).where(SupportRequest.id == request_id).with_for_update()
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create_support_request(self, req: SupportRequest) -> SupportRequest:
        self.session.add(req)
        await self.session.flush()
        return req

    async def get_authorized_case_for_personnel(self, personnel_id):
        stmt = select(SupportRequest).where(SupportRequest.personnel_id == personnel_id, SupportRequest.status != "WITHDRAWN").order_by(SupportRequest.created_at.desc()).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_queue(self, status_filter=None, limit=100, offset=0, query=None, assigned_to_me=False):
        actor = self.session.info.get("actor", {})
        unit = require_unit(actor)
        stmt = select(SupportRequest.id, Personnel.pseudo_id, SupportRequest.request_type, SupportRequest.status, SupportRequest.created_at).join(Personnel, Personnel.id == SupportRequest.personnel_id).where(Personnel.unit_id == unit).order_by(SupportRequest.created_at.desc(), SupportRequest.id).offset(offset).limit(limit)
        if status_filter:
            stmt = stmt.where(SupportRequest.status == status_filter)
        if assigned_to_me:
            stmt = stmt.where(SupportRequest.assigned_to_user_id == uuid.UUID(actor["user_id"]))
        if query:
            literal = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            stmt = stmt.where(Personnel.pseudo_id.ilike("%" + literal + "%"))
        return [dict(row) for row in (await self.session.execute(stmt.execution_options(welfare_queue=True))).mappings()]

    async def search_operational_personnel(self, query=None, unit_id=None):
        unit = require_unit(self.session.info.get("actor", {}), unit_id)
        stmt = select(Personnel).where(Personnel.unit_id == unit).order_by(Personnel.pseudo_id).limit(200)
        if query:
            stmt = stmt.where(Personnel.pseudo_id.ilike("%" + query + "%"))
        return list((await self.session.execute(stmt)).scalars())
