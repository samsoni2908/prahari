import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.db.session import get_db


@pytest.mark.anyio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "prahari-backend"


@pytest.mark.anyio
async def test_root_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["project"] == "PRAHARI"
        assert data["health_url"] == "/health"


@pytest.mark.anyio
async def test_ready_endpoint_mocked():
    class MockResult:
        def scalar(self):
            return 1

        def scalars(self):
            return self

        def all(self):
            from pathlib import Path
            from alembic.config import Config
            from alembic.script import ScriptDirectory
            config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
            return list(ScriptDirectory.from_config(config).get_heads())

    class MockSession:
        async def execute(self, query):
            return MockResult()

    async def override_get_db():
        yield MockSession()

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/ready")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"
            assert data["database"] == "connected"
    finally:
        app.dependency_overrides.pop(get_db, None)
