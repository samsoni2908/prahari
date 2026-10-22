"""Administrative unit transfer with immediate old-unit case revocation."""

from datetime import datetime, timezone
import uuid

from fastapi import HTTPException
from sqlalchemy import select

from app.models import Personnel, SupportRequest, Unit, User
from app.repositories.audit_repository import AuditRepository


class PersonnelTransferService:
    def __init__(self, session):
        self.session = session
        self.audit = AuditRepository(session)

    async def transfer(self, personnel_id, target_unit_id, reason_code):
        actor = self.session.info.get("actor") or {}
        if actor.get("role") != "ADMIN":
            raise HTTPException(403, "Administrative transfer required")
        if reason_code != "UNIT_TRANSFER":
            raise HTTPException(422, "UNIT_TRANSFER reason required")
        person = (await self.session.execute(select(Personnel).where(
            Personnel.id == personnel_id,
        ).with_for_update())).scalar_one_or_none()
        target = (await self.session.execute(select(Unit).where(
            Unit.id == target_unit_id,
        ))).scalar_one_or_none()
        if not person or not target or not target.is_active:
            raise HTTPException(404, "Personnel or unit not found")
        if person.unit_id == target_unit_id:
            return {"personnel_id": str(personnel_id), "unit_id": str(target_unit_id),
                    "withdrawn_cases": 0, "replay_safe": True}
        previous_unit = person.unit_id
        self.session.info["actor"] = {**actor, "_unit_transfer": str(personnel_id)}
        try:
            cases = list((await self.session.execute(select(SupportRequest).where(
                SupportRequest.personnel_id == personnel_id,
            ).with_for_update())).scalars())
            withdrawn = 0
            for case in cases:
                if case.status in ("OPEN", "ASSIGNED", "IN_PROGRESS"):
                    case.status = "WITHDRAWN"
                    case.closed_at = datetime.now(timezone.utc)
                    withdrawn += 1
                case.assigned_to_user_id = None
            person.unit_id = target_unit_id
            accounts = list((await self.session.execute(select(User).where(
                User.personnel_id == personnel_id, User.role == "PERSONNEL",
            ).with_for_update())).scalars())
            for account in accounts:
                account.unit_id = target_unit_id
            await self.session.flush()
        finally:
            self.session.info["actor"] = actor
        for case in cases:
            await self.audit.log_event(
                uuid.UUID(actor["user_id"]), "ADMIN", "CASE_UNIT_TRANSFER",
                "support_requests", case.id,
                metadata={"reason_code": "UNIT_TRANSFER"},
            )
        await self.audit.log_event(
            uuid.UUID(actor["user_id"]), "ADMIN", "PERSONNEL_UNIT_TRANSFER",
            "personnel", personnel_id,
            metadata={"reason_code": "UNIT_TRANSFER", "unit_id": str(target_unit_id)},
        )
        return {"personnel_id": str(personnel_id), "previous_unit_id": str(previous_unit),
                "unit_id": str(target_unit_id), "withdrawn_cases": withdrawn,
                "replay_safe": False}
