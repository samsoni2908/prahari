"""Allowlisted source persistence and safe audit-based import/job receipts."""
from sqlalchemy import select, text
from app import models

SOURCE_MODELS = {model.__tablename__: model for model in
    (models.Duty, models.RestRecord, models.LeaveRecord, models.Deployment, models.Training, models.Staffing)}


class IngestionRepository:
    def __init__(self, session):
        self.session = session

    async def lock(self, digest):
        await self.session.execute(text("SELECT pg_advisory_xact_lock(:key)"),
            {"key": int.from_bytes(bytes.fromhex(digest)[:8], "big", signed=True)})

    async def receipt(self, identifier, action, actor_id=None):
        statement = select(models.AuditEvent).where(models.AuditEvent.resource_type == "operational_import",
            models.AuditEvent.resource_id == identifier, models.AuditEvent.action == action)
        if actor_id:
            statement = statement.where(models.AuditEvent.actor_user_id == actor_id)
        return (await self.session.execute(statement.order_by(models.AuditEvent.created_at.desc()).limit(1))).scalar_one_or_none()

    async def foreign_ids(self, column, identifiers):
        foreign = next(iter(column.foreign_keys))
        return set((await self.session.execute(select(foreign.column).where(foreign.column.in_(identifiers)))).scalars())

    async def existing(self, kind, identifiers):
        model = SOURCE_MODELS[kind]
        return set((await self.session.execute(select(model.id).where(model.id.in_(identifiers)))).scalars())

    async def overlaps(self, kind, row):
        model = SOURCE_MODELS[kind]
        if kind == "duties":
            query = select(model.id).where(model.personnel_id == row["personnel_id"],
                model.start_at < row["end_at"], model.end_at > row["start_at"])
        elif kind in ("rest_records", "staffing"):
            subject = model.personnel_id if kind == "rest_records" else model.unit_id
            key = "personnel_id" if kind == "rest_records" else "unit_id"
            query = select(model.id).where(subject == row[key], model.record_date == row["record_date"])
        else:
            return False
        return (await self.session.execute(query.limit(1))).first() is not None

    async def history(self, limit, offset, jobs=False, dataset_type=None, status=None):
        actions = ("OPERATIONAL_MANUAL_BATCH", "OPERATIONAL_SCHEDULED_BATCH", "OPERATIONAL_PARTIAL_FAILURE") if jobs else ("IMPORT_VALIDATED", "IMPORT_REJECTED", "IMPORT_COMMITTED")
        query = select(models.AuditEvent).where(models.AuditEvent.action.in_(actions))
        if dataset_type:
            query = query.where(models.AuditEvent.metadata_json["dataset_type"].astext == dataset_type)
        if status:
            query = query.where(models.AuditEvent.action == "IMPORT_"+status)
        return list((await self.session.execute(query.order_by(models.AuditEvent.created_at.desc(), models.AuditEvent.id.desc()).offset(offset).limit(limit))).scalars())
