import uuid
from datetime import date
from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Deployment, Duty, LeaveRecord, RestRecord, Training


class OperationalRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_recent_duties(self, personnel_id: uuid.UUID, limit: int = 30) -> List[Duty]:
        stmt = (
            select(Duty)
            .where(Duty.personnel_id == personnel_id)
            .order_by(Duty.duty_date.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_recent_rest_records(self, personnel_id: uuid.UUID, limit: int = 30) -> List[RestRecord]:
        stmt = (
            select(RestRecord)
            .where(RestRecord.personnel_id == personnel_id)
            .order_by(RestRecord.record_date.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_recent_leaves(self, personnel_id: uuid.UUID, limit: int = 10) -> List[LeaveRecord]:
        stmt = (
            select(LeaveRecord)
            .where(LeaveRecord.personnel_id == personnel_id)
            .order_by(LeaveRecord.start_date.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_deployments(self, personnel_id: uuid.UUID) -> List[Deployment]:
        stmt = (
            select(Deployment)
            .where(Deployment.personnel_id == personnel_id)
            .order_by(Deployment.start_date.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_training_records(self, personnel_id: uuid.UUID, limit: int = 30) -> List[Training]:
        stmt = (
            select(Training)
            .where(Training.personnel_id == personnel_id)
            .order_by(Training.start_date.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
