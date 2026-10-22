"""Human operational review actions; never mutate duties or private wellbeing."""
import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone
from uuid import UUID
from fastapi import HTTPException
from app.config import settings
from app.repositories.alert_repository import AlertRepository
from app.repositories.audit_repository import AuditRepository
from app.schemas.alerts import AlertPage, AlertView


def revision(row):
    return hashlib.sha256(json.dumps([str(row.id), row.status,
        row.resolved_at.isoformat() if row.resolved_at else None], separators=(",", ":")).encode()).hexdigest()


def project(row):
    return AlertView(id=row.id, alert_type=row.alert_type, severity=row.severity,
        status=row.status, message=row.message, created_at=row.created_at,
        resolved_at=row.resolved_at, revision=revision(row))


class AlertService:
    def __init__(self, session):
        self.session = session
        self.repo = AlertRepository(session)
        self.audit = AuditRepository(session)
        self.actor = session.info.get("actor", {})

    def scope(self):
        if self.actor.get("role") not in ("COMMANDER", "WELFARE_OFFICER") or not self.actor.get("unit_id"):
            raise HTTPException(403, "OPERATIONAL_ALERT_SCOPE_REQUIRED")
        return UUID(self.actor["unit_id"])

    def encode_cursor(self, row, state):
        payload = json.dumps([str(self.scope()), state, row.created_at.isoformat(), str(row.id)], separators=(",", ":")).encode()
        signature = hmac.new(settings.SECRET_KEY.encode(), payload, hashlib.sha256).digest()
        return base64.urlsafe_b64encode(signature + payload).decode().rstrip("=")

    def decode_cursor(self, cursor, state):
        try:
            if len(cursor) > 1024:
                raise ValueError()
            raw = base64.b64decode(cursor + "=" * (-len(cursor) % 4), altchars=b"-_", validate=True)
            signature, payload = raw[:32], raw[32:]
            expected = hmac.new(settings.SECRET_KEY.encode(), payload, hashlib.sha256).digest()
            if not hmac.compare_digest(signature, expected):
                raise ValueError()
            unit, filter_state, when, identifier = json.loads(payload)
            moment = datetime.fromisoformat(when)
            if unit != str(self.scope()) or filter_state != state or moment.tzinfo is None:
                raise ValueError()
            return moment, UUID(identifier)
        except (ValueError, TypeError, UnicodeError):
            raise HTTPException(400, "INVALID_CURSOR") from None

    async def list(self, limit=50, cursor=None, state=None):
        unit = self.scope()
        if not 1 <= limit <= 200:
            raise HTTPException(422, "INVALID_LIMIT")
        after = self.decode_cursor(cursor, state) if cursor else None
        rows = await self.repo.list(unit, limit, after, state)
        return AlertPage(items=[project(row) for row in rows[:limit]],
            next_cursor=self.encode_cursor(rows[limit-1], state) if len(rows) > limit else None)

    async def action(self, identifier, body, key, target):
        unit = self.scope()
        row = await self.repo.lock(identifier, unit)
        if row is None:
            raise HTTPException(404, "ALERT_NOT_FOUND")
        actor_id = UUID(self.actor["user_id"])
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        request_hash = hashlib.sha256(json.dumps([target, body.expected_revision, body.reason_code], separators=(",", ":")).encode()).hexdigest()
        receipt = await self.repo.receipt(identifier, actor_id, key_hash)
        if receipt:
            if receipt.metadata_json.get("request_hash") != request_hash:
                raise HTTPException(409, "IDEMPOTENCY_CONFLICT")
            # Return the immutable original action result, even if subsequently resolved.
            snapshot = receipt.metadata_json
            return AlertView(id=row.id, alert_type=row.alert_type, severity=row.severity,
                status=snapshot["status"], message=row.message, created_at=row.created_at,
                resolved_at=datetime.fromisoformat(snapshot["action_digest"]) if target == "RESOLVED" else None,
                revision=snapshot["expected_revision"])
        if revision(row) != body.expected_revision:
            raise HTTPException(409, "STALE_REVISION")
        if row.status == "RESOLVED" or (target == "ACKNOWLEDGED" and row.status != "OPEN"):
            raise HTTPException(409, "INVALID_ALERT_STATE")
        row.status = target
        if target == "RESOLVED":
            row.resolved_at = datetime.now(timezone.utc)
        await self.session.flush()
        view = project(row)
        await self.audit.log_event(actor_id, self.actor["role"], "ALERT_" + target,
            "alerts", row.id, metadata={"idempotency_key_hash": key_hash,
                "request_hash": request_hash, "reason_code": body.reason_code,
                "status": target, "expected_revision": view.revision,
                "action_digest": row.resolved_at.isoformat() if row.resolved_at else "ACKNOWLEDGED"})
        return view
