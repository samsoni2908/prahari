import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Personnel, PostingHistory


class PersonnelRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, personnel_id: uuid.UUID) -> Optional[Personnel]:
        stmt = select(Personnel).where(Personnel.id == personnel_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_pseudo_id(self, pseudo_id: str) -> Optional[Personnel]:
        stmt = select(Personnel).where(Personnel.pseudo_id == pseudo_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_unit(self, unit_id: uuid.UUID) -> List[Personnel]:
        stmt = select(Personnel).where(Personnel.unit_id == unit_id).order_by(Personnel.rank_or_grade, Personnel.pseudo_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_posting_history(self, personnel_id: uuid.UUID) -> List[PostingHistory]:
        stmt = (
            select(PostingHistory)
            .where(PostingHistory.personnel_id == personnel_id)
            .order_by(PostingHistory.posting_start_date.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search(
        self,
        query: Optional[str] = None,
        unit_id: Optional[uuid.UUID] = None,
        limit: int = 100,
        offset: int = 0,
        include_name: bool = False,
    ) -> List[Personnel]:
        stmt = select(Personnel)
        if unit_id:
            stmt = stmt.where(Personnel.unit_id == unit_id)
        if query:
            q_clean = "%" + query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            predicate = (
                (Personnel.pseudo_id.ilike(q_clean))
                | (Personnel.rank_or_grade.ilike(q_clean))
                | (Personnel.role_title.ilike(q_clean))
                | (Personnel.personnel_code.ilike(q_clean))
            )
            if include_name and self.session.info.get("actor", {}).get("role") == "ADMIN":
                predicate = predicate | Personnel.full_name.ilike(q_clean)
            stmt = stmt.where(predicate)
        stmt = stmt.order_by(Personnel.rank_or_grade, Personnel.pseudo_id).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
