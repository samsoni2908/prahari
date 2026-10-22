import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Approval, Outcome, RosterScenario, ScenarioChange, ScenarioImplementation


class ScenarioRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_scenario(self, scenario: RosterScenario) -> RosterScenario:
        self.session.add(scenario)
        await self.session.flush()
        return scenario

    async def get_by_id(self, scenario_id: uuid.UUID) -> Optional[RosterScenario]:
        stmt = select(RosterScenario).where(RosterScenario.id == scenario_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_unit(self, unit_id: uuid.UUID) -> List[RosterScenario]:
        stmt = (
            select(RosterScenario)
            .where(RosterScenario.unit_id == unit_id)
            .order_by(RosterScenario.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_idempotency_key_hash(self, unit_id: uuid.UUID, key_hash: str) -> Optional[RosterScenario]:
        stmt = (
            select(RosterScenario)
            .where(
                RosterScenario.unit_id == unit_id,
                RosterScenario.current_snapshot_json["context"]["idempotency_key_hash"].astext == key_hash,
            )
            .order_by(RosterScenario.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_changes(self, scenario_id: uuid.UUID) -> List[ScenarioChange]:
        stmt = (
            select(ScenarioChange)
            .where(ScenarioChange.scenario_id == scenario_id)
            .order_by(ScenarioChange.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def add_change(self, change: ScenarioChange) -> ScenarioChange:
        self.session.add(change)
        await self.session.flush()
        return change

    async def record_approval(self, approval: Approval) -> Approval:
        self.session.add(approval)
        await self.session.flush()
        return approval

    async def latest_approval(self, scenario_id):
        stmt = select(Approval).where(Approval.scenario_id == scenario_id).order_by(Approval.decided_at.desc(), Approval.id).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def record_outcome(self, outcome: Outcome) -> Outcome:
        self.session.add(outcome)
        await self.session.flush()
        return outcome

    async def lock_scenario(self, scenario_id):
        return (await self.session.execute(select(RosterScenario).where(RosterScenario.id == scenario_id).with_for_update())).scalar_one_or_none()

    async def get_approval(self, approval_id, scenario_id):
        return (await self.session.execute(select(Approval).where(Approval.id == approval_id, Approval.scenario_id == scenario_id))).scalar_one_or_none()

    async def get_implementation(self, implementation_id, scenario_id):
        return (await self.session.execute(select(ScenarioImplementation).where(ScenarioImplementation.id == implementation_id, ScenarioImplementation.scenario_id == scenario_id))).scalar_one_or_none()

    async def implementation_for_approval(self, approval_id):
        return (await self.session.execute(select(ScenarioImplementation).where(ScenarioImplementation.approval_id == approval_id))).scalar_one_or_none()

    async def save_implementation(self, record):
        self.session.add(record)
        await self.session.flush()
        return record
