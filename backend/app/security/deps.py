import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal, set_rls_context
from app.security.jwt import decode_access_token
from app.security.rbac import Role
from app.models import AuthSession, User
from sqlalchemy import select
from app.security.csrf import validate_csrf

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    request: Request,
    bearer_token: Optional[str] = Depends(oauth2_scheme),
) -> Dict[str, Any]:
    # Explicit bearer credentials take precedence over the browser cookie.
    token = bearer_token or request.cookies.get("prahari_session")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication session missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication session",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id, jti = uuid.UUID(payload["user_id"]), uuid.UUID(payload["jti"])
    except (ValueError, KeyError, TypeError):
        raise HTTPException(401, "Invalid authentication session") from None
    async with AsyncSessionLocal() as db:
        user = await db.get(User, user_id)
        session = (await db.execute(select(AuthSession).where(AuthSession.user_id == user_id, AuthSession.jti == jti))).scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if (not user or not user.is_active or user.role not in {role.value for role in Role}
                or not session or session.revoked_at is not None or session.refresh_secret_hash is None
                or session.expires_at <= now or session.last_seen_at + timedelta(minutes=30) <= now
                or payload.get("role") != user.role
                or payload.get("unit_id") != (str(user.unit_id) if user.unit_id else None)
                or payload.get("personnel_id") != (str(user.personnel_id) if user.personnel_id else None)):
            raise HTTPException(401, "Invalid authentication session")
        if not bearer_token and request.method not in ("GET", "HEAD", "OPTIONS"):
            validate_csrf(request, str(jti))
        session.last_seen_at = now
        await db.commit()
        actor = {"user_id": str(user.id), "sub": str(user.id), "username": user.username, "role": user.role, "unit_id": str(user.unit_id) if user.unit_id else None, "personnel_id": str(user.personnel_id) if user.personnel_id else None, "jti": str(jti)}
    request.state.actor = actor
    return actor


def require_roles(*allowed_roles: str):
    async def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = current_user.get("role")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied for role '{user_role}'. Required roles: {list(allowed_roles)}",
            )
        if user_role in ("COMMANDER", "WELFARE_OFFICER") and not current_user.get("unit_id"):
            raise HTTPException(403, "Unit scope is not configured")
        return current_user
    return role_checker


async def get_db_with_rls(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> AsyncGenerator[AsyncSession, None]:
    """
    Acquires an asynchronous database session and immediately binds
    the verified authenticated token claims to PostgreSQL session settings
    via SET LOCAL (SELECT set_config(..., true)).
    """
    async with AsyncSessionLocal() as session:
        session.info["actor"] = current_user
        # Establish transaction and apply RLS settings
        user_id = current_user.get("user_id") or current_user.get("sub")
        role = current_user.get("role")
        unit_id = current_user.get("unit_id")
        await set_rls_context(session, user_id=user_id, role=role, unit_id=unit_id)
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
