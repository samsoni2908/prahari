"""Audited named access; no analytics/private fields in identity search results."""
import hashlib
import json
import uuid
from datetime import datetime, timezone
from fastapi import HTTPException
from app.models import SupportRequest, WelfareCaseAction
from app.repositories.audit_repository import AuditRepository
from app.repositories.welfare_intake_repository import WelfareIntakeRepository
from app.schemas.welfare_intake import NamedIdentity, NamedSearchResult, OpenedCase
from app.security.scope import require_unit
from app.services.notification_service import NotificationService


class WelfareIntakeService:
    def __init__(self, session):
        self.session = session
        self.actor = session.info.get("actor", {})
        self.repo = WelfareIntakeRepository(session)
        self.audit = AuditRepository(session)

    def scope(self):
        if self.actor.get("role") != "WELFARE_OFFICER":
            raise HTTPException(403, "CASE_HANDLING_ROLE_REQUIRED")
        return require_unit(self.actor)

    async def search(self, request):
        rows = await self.repo.search(self.scope(), request.field, request.query, request.limit)
        await self.audit.log_event(None, None, "CASE_IDENTITY_SEARCH", "personnel",
            metadata={"reason_code": "CASE_HANDLING"})
        # Never persist the supplied name/code or free-text purpose in audit logs.
        return NamedSearchResult(items=[NamedIdentity(**row) for row in rows])

    async def open(self, request, key):
        unit = self.scope()
        if not 8 <= len(key) <= 128:
            raise HTTPException(422, "IDEMPOTENCY_KEY_REQUIRED")
        actor_id = uuid.UUID(self.actor["user_id"])
        key_hash = hashlib.sha256((str(actor_id) + ":welfare-open:" + key).encode()).hexdigest()
        await self.repo.lock_request(key_hash)
        person = await self.repo.lock_person(request.personnel_id, unit)
        if person is None:
            raise HTTPException(404, "PERSONNEL_NOT_FOUND")
        request_hash = hashlib.sha256(json.dumps(request.model_dump(mode="json"), sort_keys=True,
            separators=(",", ":")).encode()).hexdigest()
        prior = await self.repo.prior(person.id, key_hash)
        if prior:
            if prior.request_hash != request_hash:
                raise HTTPException(409, "IDEMPOTENCY_CONFLICT")
            if prior.assigned_to_user_id != actor_id:
                raise HTTPException(404, "CASE_NOT_FOUND")
            # Original immutable creation response, irrespective of later workflow state.
            return OpenedCase(id=prior.id, status="ASSIGNED", assigned_to_me=True, created_at=prior.created_at)
        now = datetime.now(timezone.utc)
        case = SupportRequest(id=uuid.uuid4(), personnel_id=person.id, request_type=request.request_type,
            status="ASSIGNED", priority=request.priority, assigned_to_user_id=actor_id,
            request_text=request.personnel_visible_reason, request_key_hash=key_hash,
            request_hash=request_hash, created_at=now, updated_at=now)
        self.session.add(case)
        await self.session.flush()
        action = WelfareCaseAction(id=uuid.uuid4(), case_id=case.id, actor_user_id=actor_id,
            action_type="ASSIGN", visibility="OFFICER", case_status="ASSIGNED",
            assigned_to_user_id=actor_id, idempotency_key=key_hash, request_hash=request_hash,
            created_at=now)
        self.session.add(action)
        await self.session.flush()
        await self.audit.log_event(actor_id, "WELFARE_OFFICER", "CASE_OPENED", "support_requests", case.id,
            metadata={"idempotency_key_hash": key_hash, "request_hash": request_hash, "reason_code": "CASE_HANDLING"})
        await NotificationService(self.session).emit("CASE_ASSIGNED", actor_id, case.id, str(action.id))
        return OpenedCase(id=case.id, status="ASSIGNED", assigned_to_me=True, created_at=now)
