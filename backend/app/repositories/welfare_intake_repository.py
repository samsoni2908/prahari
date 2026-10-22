"""Identity search and locked duplicate-safe case intake persistence."""
from sqlalchemy import select, text
from app.models import Personnel, SupportRequest


class WelfareIntakeRepository:
    def __init__(self, session):
        self.session = session

    async def search(self, unit, field, query, limit):
        column = {"name": Personnel.full_name, "service_code": Personnel.personnel_code,
            "pseudo_id": Personnel.pseudo_id}[field]
        # Search terms are literal; no caller-controlled SQL wildcard expansion.
        term = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        statement = select(Personnel.id, Personnel.full_name, Personnel.personnel_code, Personnel.pseudo_id).where(
            Personnel.unit_id == unit, column.ilike("%" + term + "%", escape="\\"),
        ).order_by(Personnel.full_name, Personnel.id).limit(limit)
        return list((await self.session.execute(statement)).mappings())

    async def lock_person(self, person_id, unit):
        return (await self.session.execute(select(Personnel).where(
            Personnel.id == person_id, Personnel.unit_id == unit,
        ).with_for_update())).scalar_one_or_none()

    async def prior(self, person_id, key_hash):
        return (await self.session.execute(select(SupportRequest).where(
            SupportRequest.request_key_hash == key_hash,
        ))).scalar_one_or_none()

    async def lock_request(self, key_hash):
        await self.session.execute(text("SELECT pg_advisory_xact_lock(:key)"),
            {"key": int.from_bytes(bytes.fromhex(key_hash)[:8], "big", signed=True)})
