import uuid
from datetime import datetime, timedelta, timezone
import hmac
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from sqlalchemy import select
from app.models import AuthSession
from app.security.csrf import issue_csrf, validate_csrf
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.db.session import get_db
from app.repositories.user_repository import UserRepository
from app.repositories.unit_repository import UnitRepository
from app.repositories.personnel_repository import PersonnelRepository
from app.repositories.audit_repository import AuditRepository
from app.services.auth_service import AuthService
from app.security.deps import get_current_user
from app.security.jwt import decode_access_token

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _set_session_cookies(response: Response, result: Dict[str, Any]) -> str:
    secure = settings.ENVIRONMENT.lower() != "development"
    response.set_cookie(
        "prahari_session", result["access_token"], httponly=True,
        samesite="lax", secure=secure, max_age=15 * 60, path="/api/v1",
    )
    response.set_cookie(
        "prahari_refresh", result["refresh_cookie"], httponly=True,
        samesite="lax", secure=secure, max_age=result.get("remaining_seconds", 8 * 60 * 60),
        path="/api/v1/auth",
    )
    csrf_token = issue_csrf(result["session_jti"])
    response.set_cookie("prahari_csrf", csrf_token, secure=secure, samesite="lax", max_age=15 * 60, path="/api/v1")
    response.headers["Cache-Control"] = "no-store"
    return csrf_token


class LoginRequest(BaseModel):
    model_config = {"extra": "forbid"}
    username: str
    password: str


@router.post("/login")
async def login(req: LoginRequest, response: Response, request: Request, db: AsyncSession = Depends(get_db, scope="function")):
    if request.headers.get("origin") or request.cookies.get("prahari_session"):
        validate_csrf(request)
    auth_service = AuthService(
        user_repo=UserRepository(db),
        unit_repo=UnitRepository(db),
        personnel_repo=PersonnelRepository(db),
        audit_repo=AuditRepository(db),
    )
    result = await auth_service.authenticate(req.username, req.password, request.client.host if request.client else "unknown")
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    csrf_token = _set_session_cookies(response, result)

    # Return user information and token for programmatic/test clients
    return {
        "access_token": result["access_token"],
        "csrf_token": csrf_token,
        "user": result["user"],
        "message": "Authentication successful",
    }


@router.post("/refresh")
async def refresh(response: Response, request: Request, db: AsyncSession = Depends(get_db, scope="function")):
    raw = request.cookies.get("prahari_refresh")
    if not raw:
        raise HTTPException(401, "Reauthentication required")
    jti = raw.split(".", 1)[0]
    validate_csrf(request, jti)
    auth_service = AuthService(
        UserRepository(db), UnitRepository(db), PersonnelRepository(db), AuditRepository(db),
    )
    result = await auth_service.refresh(raw)
    csrf_token = _set_session_cookies(response, result)
    return {"access_token": result["access_token"], "csrf_token": csrf_token}



@router.post("/logout")
async def logout(response: Response, request: Request, db: AsyncSession = Depends(get_db, scope="function")):
    """Revoke a verified browser or bearer session and safely repeat logout."""
    cookie_token = request.cookies.get("prahari_session")
    bearer = request.headers.get("authorization", "")
    bearer_token = bearer[7:] if bearer.lower().startswith("bearer ") else None
    claims = decode_access_token(bearer_token or cookie_token) if bearer_token or cookie_token else None
    if cookie_token or request.cookies.get("prahari_refresh"):
        validate_csrf(request, claims.get("jti") if claims else None)
    session = None
    if claims:
        session = (await db.execute(select(AuthSession).where(
            AuthSession.user_id == uuid.UUID(claims["user_id"]),
            AuthSession.jti == uuid.UUID(claims["jti"]),
        ).with_for_update())).scalar_one_or_none()
    elif request.cookies.get("prahari_refresh"):
        try:
            raw_jti, secret = request.cookies["prahari_refresh"].split(".", 1)
            session = (await db.execute(select(AuthSession).where(
                AuthSession.jti == uuid.UUID(raw_jti),
            ).with_for_update())).scalar_one_or_none()
            if session:
                user = await UserRepository(db).get_by_id(session.user_id)
                if (not user or not session.refresh_secret_hash or not hmac.compare_digest(
                    session.refresh_secret_hash, AuthService._refresh_hash(secret, user)
                )):
                    session = None
        except (KeyError, ValueError):
            session = None
    if session and session.revoked_at is None:
        session.revoked_at = datetime.now(timezone.utc)
        session.revoke_reason = "LOGOUT"
        user = await UserRepository(db).get_by_id(session.user_id)
        if user:
            await AuditRepository(db).log_event(user.id, user.role, "AUTH_LOGOUT", "auth_sessions", session.id)
    response.delete_cookie("prahari_csrf", path="/api/v1")
    response.delete_cookie("prahari_session", path="/api/v1", httponly=True, samesite="lax")
    response.delete_cookie("prahari_csrf")
    response.delete_cookie("prahari_session")
    response.delete_cookie("prahari_refresh", path="/api/v1/auth", httponly=True, samesite="lax")
    response.headers["Cache-Control"] = "no-store"
    return {"message": "Logged out successfully"}


@router.get("/csrf")
async def csrf(response: Response, request: Request, for_login: bool = False,
               db: AsyncSession = Depends(get_db, scope="function")):
    jti = None
    if not for_login and request.cookies.get("prahari_session"):
        try:
            actor = await get_current_user(request, bearer_token=None)
            jti = actor["jti"]
        except HTTPException:
            pass
    if not for_login and jti is None and request.cookies.get("prahari_refresh"):
        try:
            raw_jti, secret = request.cookies["prahari_refresh"].split(".", 1)
            session = (await db.execute(select(AuthSession).where(
                AuthSession.jti == uuid.UUID(raw_jti),
            ))).scalar_one_or_none()
            if session and session.revoked_at is None and session.refresh_secret_hash:
                user = await UserRepository(db).get_by_id(session.user_id)
                now = datetime.now(timezone.utc)
                if (user and user.is_active and session.expires_at > now
                        and session.last_seen_at + timedelta(minutes=30) > now
                        and hmac.compare_digest(session.refresh_secret_hash,
                                                AuthService._refresh_hash(secret, user))):
                    jti = raw_jti
        except (ValueError, KeyError):
            pass
    token = issue_csrf(jti)
    response.set_cookie("prahari_csrf", token, secure=settings.ENVIRONMENT != "development", samesite="lax", path="/api/v1")
    response.headers["Cache-Control"] = "no-store"
    return {"csrf_token": token}



@router.get("/me")
async def me(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    user_id_str = current_user.get("user_id") or current_user.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="User ID missing from claims")

    auth_service = AuthService(
        user_repo=UserRepository(db),
        unit_repo=UnitRepository(db),
        personnel_repo=PersonnelRepository(db),
        audit_repo=AuditRepository(db),
    )
    profile = await auth_service.get_current_user_profile(uuid.UUID(user_id_str))
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    return profile
