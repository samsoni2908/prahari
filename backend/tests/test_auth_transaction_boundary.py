"""No successful authentication response may precede durable transaction completion."""
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.main import app
from app.services.auth_service import AuthService


@pytest.mark.asyncio
async def test_login_commit_failure_does_not_issue_session_or_token():
    async def failed_commit():
        yield object()
        # A real failed commit follows the same generator teardown boundary.
        raise HTTPException(503, "Authentication persistence unavailable")

    result = {"access_token": "test-token", "refresh_cookie": "test-refresh", "session_jti": str(uuid.uuid4()), "user": {"role": "PERSONNEL"}}
    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = failed_commit
    try:
        with patch.object(AuthService, "authenticate", AsyncMock(return_value=result)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/v1/auth/login", json={"username": "synthetic", "password": "synthetic"})
        assert response.status_code == 503
        assert "access_token" not in response.json()
        assert "prahari_session" not in response.cookies
        assert "prahari_refresh" not in response.cookies
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous
