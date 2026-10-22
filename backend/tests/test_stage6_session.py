"""Stage-6 session policy against the explicit disposable PostgreSQL DB."""

from datetime import datetime, timedelta, timezone
import asyncio
import secrets
import uuid

import httpx
import jwt
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.main import app
from app.models import AuthSession, User
from app.repositories.audit_repository import AuditRepository
from app.repositories.personnel_repository import PersonnelRepository
from app.repositories.unit_repository import UnitRepository
from app.repositories.user_repository import UserRepository
from app.security.password import hash_password
from app.services.auth_service import AuthService
from tests.test_stage4b_balance_decision import TEST_DB_URL


@pytest.mark.asyncio
async def test_session_rotation_replay_idle_absolute_and_logout(monkeypatch):
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    monkeypatch.setattr("app.db.session.AsyncSessionLocal", factory)
    monkeypatch.setattr("app.security.deps.AsyncSessionLocal", factory)
    username = "stage6_" + uuid.uuid4().hex
    password = secrets.token_urlsafe(24)
    try:
        async with factory() as db:
            user = User(username=username, password_hash=hash_password(password),
                        role="ADMIN", unit_id=None, personnel_id=None, is_active=True)
            db.add(user)
            await db.commit()
            user_id = user.id

        origin = settings.cors_origins[0]
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=origin) as client:
            bootstrap = await client.get("/api/v1/auth/csrf?for_login=true")
            bootstrap_cookie = bootstrap.headers["set-cookie"].lower()
            bootstrap_attrs = {part.strip() for part in bootstrap_cookie.split(";")[1:]}
            secure_expected = settings.ENVIRONMENT.lower() != "development"
            assert ("secure" in bootstrap_attrs) is secure_expected
            assert "samesite=lax" in bootstrap_attrs
            assert "path=/api/v1" in bootstrap_attrs
            assert not any(attribute.startswith("domain=") for attribute in bootstrap_attrs)
            login = await client.post("/api/v1/auth/login", json={"username": username, "password": password},
                                      headers={"Origin": origin, "X-CSRF-Token": bootstrap.json()["csrf_token"]})
            assert login.status_code == 200
            session_cookies = login.headers.get_list("set-cookie")
            expected_paths = {
                "prahari_session": "/api/v1",
                "prahari_refresh": "/api/v1/auth",
                "prahari_csrf": "/api/v1",
            }
            for cookie_name, expected_path in expected_paths.items():
                cookie = next(item.lower() for item in session_cookies if item.startswith(cookie_name + "="))
                attributes = {part.strip() for part in cookie.split(";")[1:]}
                assert ("secure" in attributes) is secure_expected
                assert "samesite=lax" in attributes
                assert f"path={expected_path}" in attributes
                assert not any(attribute.startswith("domain=") for attribute in attributes)
            token = login.json()["access_token"]
            claims = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM],
                                issuer="prahari", audience="prahari-api")
            assert claims["exp"] - claims["iat"] == 15 * 60
            old_refresh = client.cookies["prahari_refresh"]
            assert old_refresh not in str(login.json())
            async with factory() as db:
                stored = (await db.execute(select(AuthSession).where(
                    AuthSession.jti == uuid.UUID(claims["jti"]),
                ))).scalar_one()
                assert stored.refresh_secret_hash and len(stored.refresh_secret_hash) == 64
                assert old_refresh.split(".", 1)[1] not in stored.refresh_secret_hash
                assert stored.expires_at - stored.created_at == timedelta(hours=8)

            recovery = await client.get("/api/v1/auth/csrf", headers={
                "Cookie": "prahari_session=expired; prahari_refresh=" + old_refresh,
            })
            recovered_claims = jwt.decode(recovery.json()["csrf_token"], settings.SECRET_KEY,
                                          algorithms=[settings.ALGORITHM])
            assert recovered_claims["session_jti"] == claims["jti"]
            csrf = client.cookies["prahari_csrf"]
            assert (await client.post("/api/v1/auth/refresh", headers={
                "Origin": "http://evil.invalid", "X-CSRF-Token": csrf,
            })).status_code == 403
            first = await client.post("/api/v1/auth/refresh", headers={"Origin": origin, "X-CSRF-Token": csrf})
            assert first.status_code == 200
            assert client.cookies["prahari_refresh"] != old_refresh
            assert (await client.get("/api/v1/auth/me")).status_code == 200
            replay = await client.post("/api/v1/auth/refresh", headers={
                "Origin": origin, "X-CSRF-Token": csrf, "Cookie": "prahari_refresh=" + old_refresh + "; prahari_csrf=" + csrf,
            })
            assert replay.status_code == 401
            assert (await client.get("/api/v1/auth/me")).status_code == 401

            # A fresh login verifies logout clears both cookies and revokes
            # the server row immediately, even while its JWT remains valid.
            client.cookies.clear()
            bootstrap = await client.get("/api/v1/auth/csrf?for_login=true")
            second = await client.post("/api/v1/auth/login", json={"username": username, "password": password},
                                       headers={"Origin": origin, "X-CSRF-Token": bootstrap.json()["csrf_token"]})
            assert second.status_code == 200
            bearer = second.json()["access_token"]
            out = await client.post("/api/v1/auth/logout", headers={
                "Origin": origin, "X-CSRF-Token": client.cookies["prahari_csrf"],
            })
            assert out.status_code == 200
            assert (await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer " + bearer})).status_code == 401
            assert (await client.post("/api/v1/auth/logout")).status_code == 200

            client.cookies.clear()
            bootstrap = await client.get("/api/v1/auth/csrf?for_login=true")
            third = await client.post("/api/v1/auth/login", json={"username": username, "password": password},
                                      headers={"Origin": origin, "X-CSRF-Token": bootstrap.json()["csrf_token"]})
            assert third.status_code == 200
            third_csrf = client.cookies["prahari_csrf"]
            async with factory() as db:
                changed = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
                changed.role = "PERSONNEL"
                await db.commit()
            assert (await client.get("/api/v1/auth/me")).status_code == 401
            assert (await client.post("/api/v1/auth/refresh", headers={
                "Origin": origin, "X-CSRF-Token": third_csrf,
            })).status_code == 401

        async with factory() as db:
            user = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
            auth = AuthService(UserRepository(db), UnitRepository(db), PersonnelRepository(db), AuditRepository(db))
            now = datetime.now(timezone.utc)
            legacy = AuthSession(user_id=user_id, jti=uuid.uuid4(), created_at=now,
                                 last_seen_at=now, expires_at=now + timedelta(hours=8),
                                 refresh_secret_hash=None)
            db.add(legacy)
            await db.flush()
            with pytest.raises(HTTPException):
                await auth.refresh(str(legacy.jti) + "." + secrets.token_urlsafe(48))
            idle_secret = secrets.token_urlsafe(48)
            idle = AuthSession(user_id=user_id, jti=uuid.uuid4(), created_at=now - timedelta(minutes=31),
                               last_seen_at=now - timedelta(minutes=31), expires_at=now + timedelta(hours=7),
                               refresh_secret_hash=AuthService._refresh_hash(idle_secret, user))
            db.add(idle)
            await db.flush()
            with pytest.raises(HTTPException):
                await auth.refresh(str(idle.jti) + "." + idle_secret)
            absolute_secret = secrets.token_urlsafe(48)
            absolute = AuthSession(user_id=user_id, jti=uuid.uuid4(), created_at=now - timedelta(hours=8),
                                   last_seen_at=now, expires_at=now,
                                   refresh_secret_hash=AuthService._refresh_hash(absolute_secret, user))
            db.add(absolute)
            await db.flush()
            with pytest.raises(HTTPException):
                await auth.refresh(str(absolute.jti) + "." + absolute_secret)
            await db.rollback()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_concurrent_refresh_has_only_one_success():
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    try:
        async with factory() as db:
            user = User(username="refresh_race_" + uuid.uuid4().hex,
                        password_hash=hash_password(secrets.token_urlsafe(24)),
                        role="ADMIN", is_active=True)
            db.add(user)
            await db.flush()
            now = datetime.now(timezone.utc)
            secret = secrets.token_urlsafe(48)
            jti = uuid.uuid4()
            db.add(AuthSession(
                user_id=user.id, jti=jti, created_at=now, last_seen_at=now,
                expires_at=now + timedelta(hours=8),
                refresh_secret_hash=AuthService._refresh_hash(secret, user),
            ))
            await db.commit()

        async def attempt():
            async with factory() as db:
                auth = AuthService(UserRepository(db), UnitRepository(db),
                                   PersonnelRepository(db), AuditRepository(db))
                try:
                    await auth.refresh(str(jti) + "." + secret)
                    await db.commit()
                    return 200
                except HTTPException as exc:
                    await db.rollback()
                    return exc.status_code

        results = await asyncio.gather(attempt(), attempt())
        assert sorted(results) == [200, 401]
    finally:
        await engine.dispose()
