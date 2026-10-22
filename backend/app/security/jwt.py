from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import jwt
from app.config import settings

ALGORITHM = settings.ALGORITHM
SECRET_KEY = settings.SECRET_KEY


def create_access_token(
    subject: str | Dict[str, Any],
    role: str,
    user_id: str,
    personnel_id: Optional[str] = None,
    unit_id: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
    session_jti: Optional[str] = None,
) -> str:
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + min(expires_delta, timedelta(minutes=15))
    else:
        expire = now + timedelta(minutes=15)

    to_encode: Dict[str, Any] = {
        "sub": str(user_id),
        "username": subject if isinstance(subject, str) else subject.get("username", ""),
        "role": role,
        "user_id": str(user_id),
        "personnel_id": str(personnel_id) if personnel_id else None,
        "unit_id": str(unit_id) if unit_id else None,
        "exp": expire,
        "iat": now,
        "jti": session_jti,
        "token_use": "access",
        "iss": "prahari",
        "aud": "prahari-api",
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], issuer="prahari", audience="prahari-api", options={"require": ["sub", "user_id", "jti", "exp", "iat", "token_use"]})
        if payload.get("token_use") != "access" or not payload.get("jti") or payload["sub"] != payload["user_id"]:
            return None
        return payload
    except Exception:
        return None
