import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from app.repositories.user_repository import UserRepository
from app.repositories.unit_repository import UnitRepository
from app.repositories.personnel_repository import PersonnelRepository
from app.repositories.audit_repository import AuditRepository
from app.security.password import verify_password
from app.security.jwt import create_access_token
from app.models import AuthSession
from app.config import settings
import hashlib
import hmac
import secrets
from sqlalchemy import select, func
from fastapi import HTTPException
from app.models import AuditEvent


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        unit_repo: UnitRepository,
        personnel_repo: PersonnelRepository,
        audit_repo: AuditRepository,
    ):
        self.user_repo = user_repo
        self.unit_repo = unit_repo
        self.personnel_repo = personnel_repo
        self.audit_repo = audit_repo

    @staticmethod
    def _refresh_hash(secret: str, user) -> str:
        scope = "\0".join((str(user.id), user.role or "", str(user.unit_id or ""), str(user.personnel_id or "")))
        return hashlib.sha256((secret + "\0" + scope).encode()).hexdigest()

    async def authenticate(self, username: str, password: str, client_address: str = "local") -> Optional[Dict[str, Any]]:
        rate_digest = hmac.new(settings.SECRET_KEY.encode(), (username.casefold() + "\0" + client_address).encode(), hashlib.sha256).digest()
        rate_key = rate_digest.hex()
        await self.user_repo.session.execute(select(func.pg_advisory_xact_lock(int.from_bytes(rate_digest[:8], "big", signed=True))))
        recent = datetime.now(timezone.utc) - timedelta(seconds=settings.LOGIN_WINDOW_SECONDS)
        attempts = (await self.user_repo.session.execute(select(func.count()).select_from(AuditEvent).where(AuditEvent.action.in_(["LOGIN_ATTEMPT", "LOGIN_SUCCESS"]), AuditEvent.created_at >= recent, AuditEvent.metadata_json["rate_key"].astext == rate_key))).scalar()
        if attempts >= settings.LOGIN_ATTEMPTS_PER_WINDOW:
            raise HTTPException(429, "Login temporarily unavailable")
        user = await self.user_repo.get_by_username(username)
        if not user or not user.is_active or user.role not in ("PERSONNEL", "COMMANDER", "WELFARE_OFFICER", "ADMIN"):
            await self.audit_repo.log_event(
                actor_user_id=None,
                actor_role=None,
                action="LOGIN_ATTEMPT",
                resource_type="auth",
                result="FAILURE",
                reason="Invalid credentials",
                metadata={"rate_key": rate_key},
            )
            await self.user_repo.session.commit()
            return None

        if not verify_password(password, user.password_hash):
            await self.audit_repo.log_event(
                actor_user_id=user.id,
                actor_role=user.role,
                action="LOGIN_ATTEMPT",
                resource_type="auth",
                resource_id=user.id,
                result="FAILURE",
                reason="Invalid credentials",
                metadata={"rate_key": rate_key},
            )
            await self.user_repo.session.commit()
            return None

        # Build token payload
        claims = {
            "sub": str(user.id),
            "user_id": str(user.id),
            "username": user.username,
            "role": user.role,
            "unit_id": str(user.unit_id) if user.unit_id else None,
            "personnel_id": str(user.personnel_id) if user.personnel_id else None,
        }
        jti = uuid.uuid4()
        now = datetime.now(timezone.utc)
        refresh_secret = secrets.token_urlsafe(48)
        self.user_repo.session.add(AuthSession(
            user_id=user.id, jti=jti, created_at=now, last_seen_at=now,
            expires_at=now + timedelta(hours=8),
            refresh_secret_hash=self._refresh_hash(refresh_secret, user),
        ))
        await self.user_repo.session.flush()
        access_token = create_access_token(
            subject=user.username,
            role=user.role,
            user_id=str(user.id),
            personnel_id=str(user.personnel_id) if user.personnel_id else None,
            unit_id=str(user.unit_id) if user.unit_id else None,
            session_jti=str(jti),
        )

        # Audit successful login
        await self.audit_repo.log_event(
            actor_user_id=user.id,
            actor_role=user.role,
            action="LOGIN_SUCCESS",
            resource_type="auth",
            resource_id=user.id,
            result="SUCCESS",
            metadata={"rate_key": rate_key},
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "session_jti": str(jti),
            "refresh_cookie": str(jti) + "." + refresh_secret,
            "user": {
                "id": str(user.id),
                "username": user.username,
                "role": user.role,
                "unit_id": str(user.unit_id) if user.unit_id else None,
                "personnel_id": str(user.personnel_id) if user.personnel_id else None,
            },
        }

    async def refresh(self, refresh_cookie: str) -> Dict[str, Any]:
        try:
            raw_jti, secret = refresh_cookie.split(".", 1)
            jti = uuid.UUID(raw_jti)
        except (AttributeError, ValueError):
            raise HTTPException(401, "Reauthentication required") from None
        if not 20 <= len(secret) <= 200:
            raise HTTPException(401, "Reauthentication required")
        session = (await self.user_repo.session.execute(
            select(AuthSession).where(AuthSession.jti == jti).with_for_update()
        )).scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if not session or session.revoked_at is not None or session.refresh_secret_hash is None:
            raise HTTPException(401, "Reauthentication required")
        if session.expires_at <= now or session.last_seen_at + timedelta(minutes=30) <= now:
            session.revoked_at = now
            session.revoke_reason = "SESSION_EXPIRED"
            await self.user_repo.session.commit()
            raise HTTPException(401, "Reauthentication required")
        user = await self.user_repo.get_by_id(session.user_id)
        if not user or not user.is_active or user.role not in ("PERSONNEL", "COMMANDER", "WELFARE_OFFICER", "ADMIN"):
            session.revoked_at = now
            session.revoke_reason = "ACCOUNT_CHANGED"
            await self.user_repo.session.commit()
            raise HTTPException(401, "Reauthentication required")
        supplied_hash = self._refresh_hash(secret, user)
        if not hmac.compare_digest(session.refresh_secret_hash, supplied_hash):
            session.revoked_at = now
            session.revoke_reason = "REFRESH_REPLAY_OR_SCOPE_CHANGE"
            await self.user_repo.session.commit()
            raise HTTPException(401, "Reauthentication required")
        next_secret = secrets.token_urlsafe(48)
        session.refresh_secret_hash = self._refresh_hash(next_secret, user)
        session.last_seen_at = now
        access_token = create_access_token(
            subject=user.username, role=user.role, user_id=str(user.id),
            personnel_id=str(user.personnel_id) if user.personnel_id else None,
            unit_id=str(user.unit_id) if user.unit_id else None,
            session_jti=str(jti),
        )
        await self.audit_repo.log_event(
            user.id, user.role, "AUTH_REFRESH", "auth_sessions", session.id,
        )
        return {
            "access_token": access_token,
            "refresh_cookie": str(jti) + "." + next_secret,
            "session_jti": str(jti),
            "remaining_seconds": max(0, int((session.expires_at - now).total_seconds())),
        }

    async def get_current_user_profile(self, user_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return None

        unit_info = None
        if user.unit_id:
            unit = await self.unit_repo.get_by_id(user.unit_id)
            if unit:
                unit_info = {
                    "id": str(unit.id),
                    "unit_code": unit.unit_code,
                    "unit_name": unit.unit_name,
                    "unit_type": unit.unit_type,
                    "location_label": unit.location_label,
                }

        personnel_info = None
        if user.personnel_id:
            person = await self.personnel_repo.get_by_id(user.personnel_id)
            if person:
                personnel_info = {
                    "id": str(person.id),
                    "pseudo_id": person.pseudo_id,
                    "rank_or_grade": person.rank_or_grade,
                    "role_title": person.role_title,
                    "status": person.status,
                }

        return {
            "id": str(user.id),
            "username": user.username,
            "role": user.role,
            "unit_id": str(user.unit_id) if user.unit_id else None,
            "personnel_id": str(user.personnel_id) if user.personnel_id else None,
            "unit": unit_info,
            "personnel": personnel_info,
        }
