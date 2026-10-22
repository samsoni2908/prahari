import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Staffing, Unit


class UnitRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_active_units(self) -> List[Unit]:
        stmt = select(Unit).where(Unit.is_active == True).order_by(Unit.unit_code)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, unit_id: uuid.UUID) -> Optional[Unit]:
        stmt = select(Unit).where(Unit.id == unit_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_units(self, limit=100, offset=0, query=None, is_active=None):
        stmt = select(Unit)
        if is_active is not None:
            stmt = stmt.where(Unit.is_active == is_active)
        if query:
            literal = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            stmt = stmt.where(Unit.unit_name.ilike("%"+literal+"%") | Unit.unit_code.ilike("%"+literal+"%"))
        return list((await self.session.execute(stmt.order_by(Unit.unit_code, Unit.id).offset(offset).limit(limit))).scalars())

    async def get_latest_staffing(self, unit_id: uuid.UUID) -> Optional[Staffing]:
        stmt = (
            select(Staffing)
            .where(Staffing.unit_id == unit_id)
            .order_by(Staffing.record_date.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
