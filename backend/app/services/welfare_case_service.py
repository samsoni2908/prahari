"""Governed support-case actions on the existing append-only action table."""

from datetime import date, datetime, timezone
import hashlib
import json
import uuid

from fastapi import HTTPException
from sqlalchemy import select, text

from app.models import Personnel, SupportRequest, User, WelfareCaseAction
from app.repositories.audit_repository import AuditRepository
from app.services.notification_service import NotificationService
from app.security.scope import require_unit


ACTION_TYPES = frozenset({
    "CONTACT_ATTEMPT", "DISCUSSION", "WORKLOAD_REVIEW", "REFERRAL",
    "FOLLOW_UP", "ASSIGN", "REASSIGN", "STATUS_CHANGE", "CLOSE",
})
TRANSITIONS = {
    "OPEN": {"ASSIGNED", "WITHDRAWN"},
    "ASSIGNED": {"IN_PROGRESS", "CLOSED", "WITHDRAWN"},
    "IN_PROGRESS": {"CLOSED", "WITHDRAWN"},
}


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _key(value):
    if not value or not 8 <= len(value.strip()) <= 200:
        raise HTTPException(422, "Idempotency-Key required")
    return value.strip()


def _project(action):
    return {
        "id": str(action.id), "case_id": str(action.case_id),
        "action_type": action.action_type, "note": action.note,
        "visibility": action.visibility, "case_status": action.case_status,
        "follow_up_date": action.follow_up_date.isoformat() if action.follow_up_date else None,
        "created_at": action.created_at.isoformat(),
    }


class WelfareCaseService:
    def __init__(self, session):
        self.session = session
        self.audit = AuditRepository(session)

    def _actor(self, role="WELFARE_OFFICER"):
        actor = self.session.info.get("actor") or {}
        if actor.get("role") != role:
            raise HTTPException(403, "Case action not permitted")
        return actor

    async def _receipt(self, case_id, actor_id, key_hash, request_hash):
        prior = (await self.session.execute(select(WelfareCaseAction).where(
            WelfareCaseAction.case_id == case_id,
            WelfareCaseAction.actor_user_id == actor_id,
            WelfareCaseAction.idempotency_key == key_hash,
        ))).scalar_one_or_none()
        if prior and prior.request_hash != request_hash:
            raise HTTPException(409, "Idempotency key already used with different payload")
        return prior

    async def claim(self, case_id, reason, idempotency_key):
        actor = self._actor()
        unit = require_unit(actor)
        actor_id = uuid.UUID(actor["user_id"])
        reason = reason.strip()
        if not 5 <= len(reason) <= 500:
            raise HTTPException(422, "Bounded assignment reason required")
        key_hash = _digest({"case": str(case_id), "actor": str(actor_id), "key": _key(idempotency_key)})
        request_hash = _digest({"action": "ASSIGN", "reason": reason})
        await self.session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {
            "key": int.from_bytes(bytes.fromhex(key_hash)[:8], "big", signed=True),
        })
        # The queue projection is pseudonymous; this one-case internal scope
        # permits a row lock only when the case is unassigned or already ours.
        self.session.info["actor"] = {**actor, "_claim_case": str(case_id)}
        try:
            case = (await self.session.execute(select(SupportRequest).where(
                SupportRequest.id == case_id,
            ).with_for_update())).scalar_one_or_none()
            if not case:
                raise HTTPException(404, "Case not found")
            person = (await self.session.execute(select(Personnel).where(
                Personnel.id == case.personnel_id,
            ))).scalar_one_or_none()
            officer = (await self.session.execute(select(User).where(User.id == actor_id))).scalar_one_or_none()
            if (not person or person.unit_id != unit or not officer or not officer.is_active
                    or officer.role != "WELFARE_OFFICER" or officer.unit_id != unit):
                raise HTTPException(404, "Case not found")
            if case.status not in ("OPEN", "ASSIGNED"):
                raise HTTPException(409, "Case cannot be assigned")
            prior = await self._receipt(case_id, actor_id, key_hash, request_hash)
            if prior:
                return {"id": str(case.id), "status": case.status, "assigned_to_me": True, "replay_safe": True}
            if case.assigned_to_user_id is not None:
                raise HTTPException(409, "Case already assigned")
            case.assigned_to_user_id = actor_id
            case.status = "ASSIGNED"
            assignment = WelfareCaseAction(
                case_id=case_id, actor_user_id=actor_id,
                action_type="ASSIGN", note=reason, visibility="OFFICER",
                case_status="ASSIGNED", assigned_to_user_id=actor_id,
                idempotency_key=key_hash, request_hash=request_hash,
            )
            self.session.add(assignment)
            await self.session.flush()
        finally:
            self.session.info["actor"] = actor
        await self.audit.log_event(actor_id, "WELFARE_OFFICER", "CASE_ASSIGNED", "support_requests", case_id)
        await NotificationService(self.session).emit("CASE_ASSIGNED", actor_id, case_id, str(assignment.id))
        return {"id": str(case_id), "status": "ASSIGNED", "assigned_to_me": True, "replay_safe": False}

    async def action(self, case_id, action_type, note, visibility, follow_up_date,
                     case_status, idempotency_key):
        actor = self._actor()
        actor_id = uuid.UUID(actor["user_id"])
        action_type = action_type.strip().upper()
        visibility = visibility.strip().upper()
        note = note.strip() if note is not None else None
        if action_type not in ACTION_TYPES - {"ASSIGN", "REASSIGN"}:
            raise HTTPException(422, "Unsupported case action")
        if visibility not in ("PERSONNEL", "OFFICER"):
            raise HTTPException(422, "Invalid action visibility")
        if note is not None and len(note) > 2000:
            raise HTTPException(422, "Case note too long")
        if action_type == "CLOSE" and (visibility != "PERSONNEL" or not note or len(note) < 5):
            raise HTTPException(422, "Closure requires separate Personnel-visible outcome note")
        if action_type == "FOLLOW_UP" and (not follow_up_date or follow_up_date < date.today()):
            raise HTTPException(422, "Future follow-up date required")
        if follow_up_date and follow_up_date < date.today():
            raise HTTPException(422, "Past follow-up date invalid")
        key_hash = _digest({"case": str(case_id), "actor": str(actor_id), "key": _key(idempotency_key)})
        request_hash = _digest({"action": action_type, "note": note, "visibility": visibility,
                                "follow_up_date": follow_up_date, "case_status": case_status})
        await self.session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {
            "key": int.from_bytes(bytes.fromhex(key_hash)[:8], "big", signed=True),
        })
        case = (await self.session.execute(select(SupportRequest).where(
            SupportRequest.id == case_id,
        ).with_for_update())).scalar_one_or_none()
        if not case:
            raise HTTPException(404, "Case not found")
        prior = await self._receipt(case_id, actor_id, key_hash, request_hash)
        if prior:
            return {**_project(prior), "replay_safe": True}
        if case.status not in ("ASSIGNED", "IN_PROGRESS"):
            raise HTTPException(409, "Case is not active")
        next_status = "CLOSED" if action_type == "CLOSE" else (case_status or case.status)
        if next_status != case.status and next_status not in TRANSITIONS.get(case.status, set()):
            raise HTTPException(409, "Invalid case transition")
        if next_status == "CLOSED" and action_type != "CLOSE":
            raise HTTPException(422, "Use CLOSE with visible outcome note")
        action = WelfareCaseAction(
            case_id=case_id, actor_user_id=actor_id,
            action_type=action_type, note=note, visibility=visibility,
            follow_up_date=follow_up_date, case_status=next_status,
            assigned_to_user_id=actor_id, idempotency_key=key_hash,
            request_hash=request_hash,
        )
        self.session.add(action)
        case.status = next_status
        if follow_up_date:
            case.follow_up_date = follow_up_date
        if next_status == "CLOSED":
            case.closed_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.audit.log_event(actor_id, "WELFARE_OFFICER", "CASE_ACTION_RECORDED", "support_requests", case_id,
                                   metadata={"status": next_status})
        if visibility == "PERSONNEL":
            await NotificationService(self.session).emit_case_owner(
                "CASE_CLOSED" if next_status == "CLOSED" else "CASE_UPDATED", case_id, str(action.id),
            )
        return {**_project(action), "replay_safe": False}

    async def reassign(self, case_id, target_officer_id, reason, idempotency_key):
        actor = self._actor()
        unit = require_unit(actor)
        actor_id = uuid.UUID(actor["user_id"])
        reason = reason.strip()
        if not 5 <= len(reason) <= 500:
            raise HTTPException(422, "Bounded reassignment reason required")
        key_hash = _digest({"case": str(case_id), "actor": str(actor_id), "key": _key(idempotency_key)})
        request_hash = _digest({"action": "REASSIGN", "target": str(target_officer_id), "reason": reason})
        await self.session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {
            "key": int.from_bytes(bytes.fromhex(key_hash)[:8], "big", signed=True),
        })
        # A completed reassignment removes the previous officer's case scope.
        # Only their own immutable receipt remains replayable.
        self.session.info["actor"] = None
        try:
            prior = (await self.session.execute(select(WelfareCaseAction).where(
                WelfareCaseAction.case_id == case_id,
                WelfareCaseAction.actor_user_id == actor_id,
                WelfareCaseAction.idempotency_key == key_hash,
                WelfareCaseAction.action_type == "REASSIGN",
            ))).scalar_one_or_none()
        finally:
            self.session.info["actor"] = actor
        if prior:
            if prior.request_hash != request_hash:
                raise HTTPException(409, "Idempotency key already used with different payload")
            return {"id": str(case_id), "status": prior.case_status,
                    "assigned_to_user_id": str(prior.assigned_to_user_id), "replay_safe": True}
        case = (await self.session.execute(select(SupportRequest).where(
            SupportRequest.id == case_id,
        ).with_for_update())).scalar_one_or_none()
        if not case:
            raise HTTPException(404, "Case not found")
        if case.status not in ("ASSIGNED", "IN_PROGRESS") or case.assigned_to_user_id != actor_id:
            raise HTTPException(409, "Case is not assigned to actor")
        if target_officer_id == actor_id:
            raise HTTPException(422, "Choose a different officer")
        self.session.info["actor"] = None
        try:
            target = (await self.session.execute(select(User).where(User.id == target_officer_id))).scalar_one_or_none()
        finally:
            self.session.info["actor"] = actor
        if not target or not target.is_active or target.role != "WELFARE_OFFICER" or target.unit_id != unit:
            raise HTTPException(404, "Target officer not found")
        action = WelfareCaseAction(
            case_id=case_id, actor_user_id=actor_id, action_type="REASSIGN",
            note=reason, visibility="OFFICER", case_status=case.status,
            assigned_to_user_id=target_officer_id,
            idempotency_key=key_hash, request_hash=request_hash,
        )
        self.session.info["actor"] = {**actor, "_reassign_case": str(case_id)}
        try:
            case.assigned_to_user_id = target_officer_id
            self.session.add(action)
            await self.session.flush()
        finally:
            self.session.info["actor"] = actor
        await self.audit.log_event(actor_id, "WELFARE_OFFICER", "CASE_REASSIGNED",
                                   "support_requests", case_id)
        await NotificationService(self.session).emit("CASE_ASSIGNED", target_officer_id, case_id, str(action.id))
        return {"id": str(case_id), "status": case.status,
                "assigned_to_user_id": str(target_officer_id), "replay_safe": False}

    async def list_actions(self, case_id):
        actor = self.session.info.get("actor") or {}
        if actor.get("role") not in ("PERSONNEL", "WELFARE_OFFICER"):
            raise HTTPException(403, "Case actions unavailable")
        case = (await self.session.execute(select(SupportRequest).where(
            SupportRequest.id == case_id,
        ))).scalar_one_or_none()
        if not case:
            raise HTTPException(404, "Case not found")
        rows = list((await self.session.execute(select(WelfareCaseAction).where(
            WelfareCaseAction.case_id == case_id,
        ).order_by(WelfareCaseAction.created_at, WelfareCaseAction.id))).scalars())
        return [_project(row) for row in rows]

    async def set_priority(self, case_id, priority, reason, idempotency_key):
        actor = self._actor()
        actor_id = uuid.UUID(actor["user_id"])
        priority = priority.strip().upper()
        reason = reason.strip()
        if priority not in ("NORMAL", "URGENT") or not 5 <= len(reason) <= 500:
            raise HTTPException(422, "Manual priority and bounded human reason required")
        key_hash = _digest({"case": str(case_id), "actor": str(actor_id), "key": _key(idempotency_key)})
        request_hash = _digest({"action": "PRIORITY", "priority": priority, "reason": reason})
        await self.session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {
            "key": int.from_bytes(bytes.fromhex(key_hash)[:8], "big", signed=True),
        })
        case = (await self.session.execute(select(SupportRequest).where(
            SupportRequest.id == case_id,
        ).with_for_update())).scalar_one_or_none()
        if not case:
            raise HTTPException(404, "Case not found")
        prior = await self._receipt(case_id, actor_id, key_hash, request_hash)
        if prior:
            return {"id": str(case_id), "priority": priority, "replay_safe": True}
        if case.status not in ("ASSIGNED", "IN_PROGRESS"):
            raise HTTPException(409, "Case is not active")
        case.priority = priority
        action = WelfareCaseAction(
            case_id=case_id, actor_user_id=actor_id,
            action_type="STATUS_CHANGE", note="Manual priority " + priority + ": " + reason,
            visibility="OFFICER", case_status=case.status,
            assigned_to_user_id=actor_id, idempotency_key=key_hash,
            request_hash=request_hash,
        )
        self.session.add(action)
        await self.session.flush()
        await self.audit.log_event(actor_id, "WELFARE_OFFICER", "CASE_PRIORITY_CHANGED",
                                   "support_requests", case_id, metadata={"status": priority})
        return {"id": str(case_id), "priority": priority, "replay_safe": False}

    async def withdraw(self, case_id, reason_code):
        actor = self._actor("PERSONNEL")
        if reason_code not in ("NO_LONGER_NEEDED", "REQUEST_CANCELLED"):
            raise HTTPException(422, "Controlled withdrawal reason required")
        case = (await self.session.execute(select(SupportRequest).where(
            SupportRequest.id == case_id,
        ).with_for_update())).scalar_one_or_none()
        if not case or str(case.personnel_id) != actor.get("personnel_id"):
            raise HTTPException(404, "Case not found")
        if case.status == "WITHDRAWN":
            return {"id": str(case_id), "status": "WITHDRAWN", "replay_safe": True}
        if case.status not in ("OPEN", "ASSIGNED", "IN_PROGRESS"):
            raise HTTPException(409, "Case cannot be withdrawn")
        case.status = "WITHDRAWN"
        case.assigned_to_user_id = None
        case.closed_at = datetime.now(timezone.utc)
        await self.audit.log_event(uuid.UUID(actor["user_id"]), "PERSONNEL", "CASE_WITHDRAWN",
                                   "support_requests", case_id, metadata={"reason_code": reason_code})
        return {"id": str(case_id), "status": "WITHDRAWN", "replay_safe": False}
