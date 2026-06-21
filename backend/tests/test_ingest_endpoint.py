import io
import json
import uuid
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from openpyxl import Workbook

from app.main import app
from app.core.database import get_db


@pytest.mark.asyncio
async def test_ingest_csv_endpoint():
    deck_id = uuid.uuid4()

    mock_deck = MagicMock()
    mock_deck.id = deck_id

    mock_job_id = uuid.uuid4()

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_deck
    mock_session.execute.return_value = mock_result
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, "id", mock_job_id))

    async def override_get_db():
        yield mock_session

    with patch("app.api.v1.endpoints.ingest.upload_file", new_callable=AsyncMock) as mock_upload:
        mock_upload.return_value = "s3://bucket/file.csv"
        app.dependency_overrides[get_db] = override_get_db

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            csv_content = b"name,age,score\nAlice,30,95\nBob,25,87\n"
            response = await client.post(
                f"/api/v1/decks/{deck_id}/ingest",
                files={"file": ("test.csv", csv_content, "text/csv")},
            )

        assert response.status_code == 200
        data = response.json()
        assert "schema" in data
        assert "quality_report" in data
        assert data["status"] in ("CLEAN", "ISSUES_BLOCKING")
        assert data["ingest_job_id"] == str(mock_job_id)

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ingest_deck_not_found():
    deck_id = uuid.uuid4()

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/decks/{deck_id}/ingest",
            files={"file": ("test.csv", b"a,b\n1,2\n", "text/csv")},
        )

    assert response.status_code == 404
    app.dependency_overrides.clear()


def _mock_ingest_db(deck_id):
    mock_deck = MagicMock()
    mock_deck.id = deck_id

    mock_job_id = uuid.uuid4()

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_deck
    mock_session.execute.return_value = mock_result
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, "id", mock_job_id))

    return mock_session, mock_job_id


@pytest.mark.asyncio
async def test_ingest_xlsx_endpoint():
    deck_id = uuid.uuid4()
    mock_session, mock_job_id = _mock_ingest_db(deck_id)

    wb = Workbook()
    ws = wb.active
    ws.append(["name", "age", "score"])
    ws.append(["Alice", 30, 95])
    ws.append(["Bob", 25, 87])
    buf = io.BytesIO()
    wb.save(buf)
    xlsx_bytes = buf.getvalue()

    async def override_get_db():
        yield mock_session

    with patch("app.api.v1.endpoints.ingest.upload_file", new_callable=AsyncMock) as mock_upload:
        mock_upload.return_value = "s3://bucket/file.xlsx"
        app.dependency_overrides[get_db] = override_get_db

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/decks/{deck_id}/ingest",
                files={"file": ("test.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            )

        assert response.status_code == 200
        data = response.json()
        assert "schema" in data
        assert "quality_report" in data
        assert data["status"] in ("CLEAN", "ISSUES_BLOCKING")

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ingest_json_endpoint():
    deck_id = uuid.uuid4()
    mock_session, mock_job_id = _mock_ingest_db(deck_id)

    json_data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
    json_bytes = json.dumps(json_data).encode("utf-8")

    async def override_get_db():
        yield mock_session

    with patch("app.api.v1.endpoints.ingest.upload_file", new_callable=AsyncMock) as mock_upload:
        mock_upload.return_value = "s3://bucket/file.json"
        app.dependency_overrides[get_db] = override_get_db

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/decks/{deck_id}/ingest",
                files={"file": ("test.json", json_bytes, "application/json")},
            )

        assert response.status_code == 200
        data = response.json()
        assert "schema" in data
        assert "quality_report" in data
        assert data["status"] in ("CLEAN", "ISSUES_BLOCKING")

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ingest_unsupported_format():
    deck_id = uuid.uuid4()
    mock_session, _ = _mock_ingest_db(deck_id)

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/decks/{deck_id}/ingest",
            files={"file": ("data.pdf", b"fake pdf content", "application/pdf")},
        )

    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]
    assert "CSV, XLSX, JSON" in response.json()["detail"]
    app.dependency_overrides.clear()
