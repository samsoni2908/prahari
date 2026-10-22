import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import AuditEvent, PolicyConfig


class AuditRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_event(
        self,
        actor_user_id: Optional[uuid.UUID],
        actor_role: Optional[str],
        action: str,
        resource_type: str,
        resource_id: Optional[uuid.UUID] = None,
        result: str = "SUCCESS",
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        actor = self.session.info.get("actor")
        if actor:
            actor_user_id = uuid.UUID(actor["user_id"])
            actor_role = actor["role"]
        # Free-form reasons can contain notes, credentials, scores or narratives.
        # Keep the action/resource identifiers; permit only bounded governance IDs.
        reason = None
        allowed = {
            "version_id", "policy_version", "model_version", "reason_code",
            "request_id", "source_hash", "policy_hash", "rate_key",
            "scenario_id", "scenario_version", "expected_revision",
            "decision", "status", "idempotency_key_hash", "request_hash", "actor_role",
            "approval_id", "child_scenario_id", "action_digest", "unit_id",
            "implementation_id", "replay_clock",
            "dataset_type", "row_count", "source_timestamp",
        }
        metadata = {key: value for key, value in (metadata or {}).items() if key in allowed and isinstance(value, (str, int, bool)) and len(str(value)) <= 120}
        event = AuditEvent(
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            result=result,
            reason=reason,
            metadata_json=metadata,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def find_create_receipt_by_idempotency_hash(self, unit_id: uuid.UUID, idempotency_key_hash: str) -> Optional[AuditEvent]:
        stmt = (
            select(AuditEvent)
            .where(
                AuditEvent.action.in_(["SCENARIO_CREATED", "DRAFT_SCENARIO_CREATED"]),
                AuditEvent.metadata_json["idempotency_key_hash"].astext == idempotency_key_hash,
                AuditEvent.result == "SUCCESS",
            )
            .order_by(AuditEvent.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_decision_receipt_by_idempotency_hash(self, scenario_id: uuid.UUID, idempotency_key_hash: str) -> Optional[AuditEvent]:
        stmt = (
            select(AuditEvent)
            .where(
                AuditEvent.resource_id == scenario_id,
                AuditEvent.action.in_(["SCENARIO_APPROVED", "SCENARIO_REJECTED", "SCENARIO_SUPERSEDED"]),
                AuditEvent.metadata_json["idempotency_key_hash"].astext == idempotency_key_hash,
                AuditEvent.result == "SUCCESS",
            )
            .order_by(AuditEvent.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_events(self, limit: int = 50, offset: int = 0) -> List[AuditEvent]:
        stmt = select(AuditEvent).order_by(AuditEvent.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_policies(self) -> List[PolicyConfig]:
        stmt = select(PolicyConfig).order_by(PolicyConfig.policy_key)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
