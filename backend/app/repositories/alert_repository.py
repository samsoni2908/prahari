"""Scoped operational alerts and safe action receipts in the caller's transaction."""
from sqlalchemy import select, and_, or_
from app.models import Alert, AuditEvent


class AlertRepository:
    def __init__(self, session):
        self.session = session

    async def list(self, unit_id, limit, after=None, state=None):
        query = select(Alert).where(Alert.unit_id == unit_id,
            Alert.source_type == "MODEL_A", Alert.severity == "HIGH",
            Alert.status.in_(("OPEN", "ACKNOWLEDGED", "RESOLVED")))
        if state:
            query = query.where(Alert.status == state)
        if after:
            when, identifier = after
            query = query.where(or_(Alert.created_at > when,
                and_(Alert.created_at == when, Alert.id > identifier)))
        return list((await self.session.execute(query.order_by(Alert.created_at, Alert.id).limit(limit + 1))).scalars())

    async def lock(self, alert_id, unit_id):
        query = select(Alert).where(Alert.id == alert_id, Alert.unit_id == unit_id,
            Alert.source_type == "MODEL_A", Alert.severity == "HIGH",
            Alert.status.in_(("OPEN", "ACKNOWLEDGED", "RESOLVED"))).with_for_update()
        return (await self.session.execute(query)).scalar_one_or_none()

    async def receipt(self, alert_id, actor_id, key_hash):
        return (await self.session.execute(select(AuditEvent).where(
            AuditEvent.resource_id == alert_id, AuditEvent.actor_user_id == actor_id,
            AuditEvent.action.in_(("ALERT_ACKNOWLEDGED", "ALERT_RESOLVED")),
            AuditEvent.metadata_json["idempotency_key_hash"].astext == key_hash,
        ))).scalar_one_or_none()
