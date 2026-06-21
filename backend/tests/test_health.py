from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def mock_services():
    with (
        patch("app.api.v1.endpoints.health.engine") as mock_engine,
        patch("app.api.v1.endpoints.health.redis_client") as mock_redis,
        patch("app.api.v1.endpoints.health._check_minio") as mock_minio,
    ):
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_engine.connect.return_value = mock_cm

        mock_redis.ping = AsyncMock(return_value=True)

        mock_minio.return_value = None

        yield {"engine": mock_engine, "redis": mock_redis, "minio": mock_minio}


@pytest.mark.asyncio
async def test_health_all_up(mock_services):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["services"]["postgres"] == "up"
    assert data["services"]["redis"] == "up"
    assert data["services"]["minio"] == "up"


@pytest.mark.asyncio
async def test_health_postgres_down(mock_services):
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
    assert data["services"]["postgres"] == "down"
    assert data["services"]["redis"] == "up"


@pytest.mark.asyncio
async def test_health_redis_down(mock_services):
    mock_services["redis"].ping = AsyncMock(side_effect=Exception("Connection refused"))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["services"]["redis"] == "down"
    assert data["services"]["postgres"] == "up"


@pytest.mark.asyncio
async def test_health_minio_down(mock_services):
    mock_services["minio"].side_effect = Exception("Connection refused")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["services"]["minio"] == "down"
    assert data["services"]["postgres"] == "up"
    assert data["services"]["redis"] == "up"
