from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def mock_services():
    with (
        patch("app.api.v1.endpoints.health.engine") as mock_engine,
        patch("app.api.v1.endpoints.health.get_redis") as mock_get_redis,
        patch("app.api.v1.endpoints.health._check_storage") as mock_storage,
    ):
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_engine.connect.return_value = mock_cm

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_get_redis.return_value = mock_redis

        mock_storage.return_value = None

        yield {"engine": mock_engine, "get_redis": mock_get_redis, "redis": mock_redis, "storage": mock_storage}


@pytest.mark.asyncio
async def test_health_all_up(mock_services):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["services"]["database"] == "up"
    assert data["services"]["redis"] == "up"
    assert "storage" in data["services"]


@pytest.mark.asyncio
async def test_health_database_down(mock_services):
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(side_effect=Exception("Connection refused"))
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    mock_services["engine"].connect.return_value = mock_cm

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["services"]["database"] == "down"


@pytest.mark.asyncio
async def test_health_redis_down(mock_services):
    mock_services["redis"].ping = AsyncMock(side_effect=Exception("Connection refused"))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["services"]["redis"] == "unavailable (optional)"


@pytest.mark.asyncio
async def test_health_storage_down(mock_services):
    mock_services["storage"].side_effect = Exception("Not accessible")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["services"]["storage"] == "down"
