"""Recipient-safe notifications with live resource reauthorization."""

from datetime import datetime, timezone
import hashlib
import uuid

from fastapi import HTTPException
from sqlalchemy import select, text

from app.models import AuditEvent, Notification, Outcome, Personnel, RosterScenario, SupportRequest, User


TEMPLATES = {
    "CASE_ASSIGNED": ("CASE_ASSIGNED", "A support case has been assigned to you.", "support_requests"),
    "CASE_UPDATED": ("CASE_UPDATED", "Your support case has an update.", "support_requests"),
    "CASE_CLOSED": ("CASE_CLOSED", "Your support case has been closed.", "support_requests"),
    "VERIFY_AVAILABLE": ("VERIFY_AVAILABLE", "An operational outcome is ready for review.", "outcomes"),
}


class NotificationService:
    def __init__(self, session):
        self.session = session

    async def _authorized(self, recipient, resource_type, resource_id):
        if not recipient or not recipient.is_active:
            return False
        if resource_type == "support_requests":
            row = (await self.session.execute(select(SupportRequest, Personnel.unit_id).join(
                Personnel, Personnel.id == SupportRequest.personnel_id,
            ).where(SupportRequest.id == resource_id))).first()
            if not row:
                return False
            case, unit_id = row
            return ((recipient.role == "PERSONNEL" and recipient.personnel_id == case.personnel_id)
                    or (recipient.role == "WELFARE_OFFICER" and recipient.id == case.assigned_to_user_id
                        and recipient.unit_id == unit_id))
        if resource_type == "outcomes":
            row = (await self.session.execute(select(RosterScenario.unit_id).join(
                Outcome, Outcome.scenario_id == RosterScenario.id,
            ).where(Outcome.id == resource_id))).scalar_one_or_none()
            return recipient.role == "COMMANDER" and row is not None and recipient.unit_id == row
        return False

    async def _resource_authorized(self, user_id, resource_type, resource_id):
        actor = self.session.info.get("actor")
        self.session.info["actor"] = None
        try:
            recipient = (await self.session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
            return await self._authorized(recipient, resource_type, resource_id)
        finally:
            self.session.info["actor"] = actor

    async def emit(self, event_type, recipient_user_id, resource_id, event_revision):
        if event_type not in TEMPLATES or not event_revision or len(event_revision) > 120:
            raise HTTPException(422, "Unsupported notification event")
        kind, message, resource_type = TEMPLATES[event_type]
        if not await self._resource_authorized(recipient_user_id, resource_type, resource_id):
            return None
        dedupe_key = hashlib.sha256((str(recipient_user_id) + ":" + event_type + ":" +
                                     str(resource_id) + ":" + event_revision).encode()).hexdigest()
        await self.session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {
            "key": int.from_bytes(bytes.fromhex(dedupe_key)[:8], "big", signed=True),
        })
        actor = self.session.info.get("actor")
        self.session.info["actor"] = None
        try:
            prior = (await self.session.execute(select(Notification).where(
                Notification.recipient_user_id == recipient_user_id,
                Notification.dedupe_key == dedupe_key,
            ))).scalar_one_or_none()
        finally:
            self.session.info["actor"] = actor
        if prior:
            return prior
        row = Notification(
            id=uuid.uuid4(), recipient_user_id=recipient_user_id,
            notification_type=kind, message=message,
            resource_type=resource_type, resource_id=resource_id,
            dedupe_key=dedupe_key,
        )
        self.session.info["_notification_event"] = True
        try:
            self.session.add(row)
            await self.session.flush()
        finally:
            self.session.info.pop("_notification_event", None)
        return row

    async def emit_case_owner(self, event_type, case_id, event_revision):
        actor = self.session.info.get("actor")
        self.session.info["actor"] = None
        try:
            recipient_id = (await self.session.execute(select(AuditEvent.actor_user_id).where(
                AuditEvent.resource_type == "support_requests", AuditEvent.resource_id == case_id,
                AuditEvent.action == "SUPPORT_REQUEST_SUBMITTED", AuditEvent.actor_role == "PERSONNEL",
                AuditEvent.result == "SUCCESS",
            ).order_by(AuditEvent.created_at).limit(1))).scalar_one_or_none()
            if recipient_id is None:
                # Officer-opened cases have no Personnel submission receipt.
                # Notify only the currently bound active owner; emit reauthorizes it.
                recipient_id = (await self.session.execute(select(User.id).join(
                    SupportRequest, SupportRequest.personnel_id == User.personnel_id,
                ).where(SupportRequest.id == case_id, User.role == "PERSONNEL",
                        User.is_active.is_(True)))).scalar_one_or_none()
        finally:
            self.session.info["actor"] = actor
        return await self.emit(event_type, recipient_id, case_id, event_revision) if recipient_id else None

    async def _visible_rows(self):
        actor = self.session.info.get("actor") or {}
        if not actor.get("user_id"):
            raise HTTPException(401, "Authentication required")
        rows = list((await self.session.execute(select(Notification).where(
            Notification.recipient_user_id == uuid.UUID(actor["user_id"]),
        ).order_by(Notification.created_at.desc(), Notification.id.desc()))).scalars())
        visible = []
        for row in rows:
            if row.resource_type and row.resource_id and await self._resource_authorized(
                row.recipient_user_id, row.resource_type, row.resource_id,
            ):
                visible.append(row)
        return visible

    @staticmethod
    def _project(row):
        return {
            "id": str(row.id), "type": row.notification_type,
            "message": row.message, "resource_type": row.resource_type,
            "resource_id": str(row.resource_id),
            "created_at": row.created_at.isoformat(),
            "read_at": row.read_at.isoformat() if row.read_at else None,
        }

    async def list(self):
        return [self._project(row) for row in await self._visible_rows()]

    async def unread_count(self):
        return sum(row.read_at is None for row in await self._visible_rows())

    async def detail(self, notification_id):
        return next((self._project(row) for row in await self._visible_rows()
                     if row.id == notification_id), None)

    async def mark_read(self, notification_id):
        row = next((row for row in await self._visible_rows() if row.id == notification_id), None)
        if row is None:
            raise HTTPException(404, "Notification not found")
        if row.read_at is None:
            row.read_at = datetime.now(timezone.utc)
            await self.session.flush()
        return self._project(row)
