"""Signed double-submit CSRF tokens, bound to the session when authenticated."""

import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, Request

from app.config import settings


def issue_csrf(jti=None):
    return jwt.encode({"token_use": "csrf", "session_jti": jti, "nonce": secrets.token_urlsafe(32), "exp": datetime.now(timezone.utc) + timedelta(minutes=15)}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def validate_csrf(request: Request, jti=None):
    if request.headers.get("origin") not in settings.cors_origins:
        raise HTTPException(403, "CSRF validation failed")
    cookie = request.cookies.get("prahari_csrf", "")
    header = request.headers.get("x-csrf-token", "")
    if not cookie or not secrets.compare_digest(cookie, header):
        raise HTTPException(403, "CSRF validation failed")
    try:
        claims = jwt.decode(header, settings.SECRET_KEY, algorithms=[settings.ALGORITHM], options={"require": ["exp", "token_use", "nonce"]})
        if claims.get("token_use") != "csrf" or claims.get("session_jti") != jti:
            raise ValueError("Wrong session")
    except Exception:
        raise HTTPException(403, "CSRF validation failed") from None
