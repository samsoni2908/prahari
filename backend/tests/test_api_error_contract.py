"""Error envelopes never echo credentials, input values or database internals."""
import uuid
from types import SimpleNamespace
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.security.deps import get_current_user, get_db_with_rls


@pytest.mark.asyncio
@pytest.mark.parametrize("path, expected", [
    ("/api/v1/alerts?limit=0", 422),
    ("/api/v1/alerts?cursor=SECRET_INVALID_CURSOR", 400),
    ("/api/v1/personnel/me", 403),
])
async def test_canonical_error_envelope(path, expected):
    prior = app.dependency_overrides.get(get_current_user)
    prior_db = app.dependency_overrides.get(get_db_with_rls)
    actor = {"user_id": str(uuid.UUID(int=1)), "role": "COMMANDER", "unit_id": str(uuid.UUID(int=2))}
    app.dependency_overrides[get_current_user] = lambda: actor
    # Transport-only validation; these requests fail before a repository read.
    # Live cursor/persistence behavior is covered by test_alert_contract.
    app.dependency_overrides[get_db_with_rls] = lambda: SimpleNamespace(info={"actor": actor})
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(path)
        assert response.status_code == expected
        payload = response.json()
        assert set(payload) == {"error"}
        assert {"code", "message", "request_id"}.issubset(payload["error"])
        assert str(uuid.UUID(payload["error"]["request_id"])) == response.headers["X-Request-ID"]
        assert "SECRET_INVALID_CURSOR" not in response.text
        for field in payload["error"].get("field_errors", []):
            assert set(field) == {"field", "code"}
    finally:
        if prior is None:
            app.dependency_overrides.pop(get_current_user, None)
        else:
            app.dependency_overrides[get_current_user] = prior
        if prior_db is None:
            app.dependency_overrides.pop(get_db_with_rls, None)
        else:
            app.dependency_overrides[get_db_with_rls] = prior_db
