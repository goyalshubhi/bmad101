import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.database import get_db


def _make_result(obj):
    r = MagicMock()
    r.scalar_one_or_none.return_value = obj
    return r


def _make_scalar_result(value):
    r = MagicMock()
    r.scalar.return_value = value
    return r


def _build_mock_db(deck_id, narrative_id, *, has_selection=True, has_deck_output=True, has_verification=True):
    mock_verification = MagicMock()
    mock_verification.action = "verification_completed"

    mock_selection = MagicMock()
    mock_selection.deck_id = deck_id
    mock_selection.narrative_id = narrative_id
    mock_selection.user_edits_text = None
    mock_selection.updated_at = datetime(2026, 6, 21, 12, 0, 0)

    mock_narrative = MagicMock()
    mock_narrative.id = narrative_id
    mock_narrative.narrative_text = "Revenue grew 15% YoY."
    mock_narrative.overall_confidence = 0.85
    mock_narrative.story_angle = "trend"
    mock_narrative.viz_recommendation = {"chart_type": "bar", "justification": "Shows trend"}
    mock_narrative.assumptions_json = [
        {"text": "Revenue is $5M", "flag_type": "EXPLICIT", "confidence": 1.0, "source_reference": "data"},
    ]

    mock_deck = MagicMock()
    mock_deck.id = deck_id
    mock_deck.name = "Q3 Financial Review"

    mock_qs = MagicMock()
    mock_qs.questions_json = [{"id": "q1", "template": "What is the primary metric?"}]
    mock_qs.answers_json = [{"question_id": "q1", "raw_answer": "Revenue"}]

    mock_ij = MagicMock()
    mock_ij.file_url = "s3://bucket/uuid/financials.csv"
    mock_ij.quality_report = {"issues": []}

    mock_report = MagicMock()
    mock_report.checks_json = {"check_a": {"status": "pass"}, "check_b": {"status": "pass"}}
    mock_report.verified_at = datetime(2026, 6, 21, 14, 30, 0)

    mock_output = MagicMock()
    mock_output.deck_id = deck_id
    mock_output.version = 1
    mock_output.pptx_url = "s3://bucket/test-key/deck_v1.pptx"
    mock_output.rendered_at = datetime(2026, 6, 21, 15, 0, 0)

    return {
        "verification": mock_verification if has_verification else None,
        "selection": mock_selection if has_selection else None,
        "narrative": mock_narrative,
        "deck": mock_deck,
        "question_session": mock_qs,
        "ingest_job": mock_ij,
        "report": mock_report,
        "output": mock_output if has_deck_output else None,
    }


def _mock_render_db(deck_id, narrative_id, *, has_selection=True, has_verification=True):
    mocks = _build_mock_db(deck_id, narrative_id, has_selection=has_selection, has_verification=has_verification)

    mock_db = AsyncMock()
    call_count = {"n": 0}

    async def _execute(stmt):
        call_count["n"] += 1
        n = call_count["n"]
        if n == 1:
            return _make_result(mocks["selection"])
        elif n == 2:
            return _make_result(mocks["verification"])
        elif n == 3:
            return _make_result(mocks["narrative"])
        elif n == 4:
            return _make_result(mocks["deck"])
        elif n == 5:
            return _make_result(mocks["question_session"])
        elif n == 6:
            return _make_result(mocks["ingest_job"])
        elif n == 7:
            return _make_result(mocks["report"])
        elif n == 8:
            return _make_scalar_result(0)
        return _make_result(None)

    mock_db.execute = _execute
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    return mock_db, mocks


def _mock_download_db(deck_id, narrative_id, *, has_output=True):
    mocks = _build_mock_db(deck_id, narrative_id, has_deck_output=has_output)

    mock_db = AsyncMock()

    async def _execute(stmt):
        return _make_result(mocks["output"])

    mock_db.execute = _execute
    return mock_db, mocks


@pytest.mark.asyncio
@patch("app.api.v1.endpoints.render.upload_file", new_callable=AsyncMock)
async def test_render_creates_deck_output(mock_upload):
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()
    mock_upload.return_value = "s3://bucket/test/deck_v1.pptx"

    mock_db, mocks = _mock_render_db(deck_id, narrative_id)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/v1/decks/{deck_id}/render")

    assert response.status_code == 200
    data = response.json()
    assert data["version"] == 1
    assert data["status"] == "rendered"
    assert data["deck_id"] == str(deck_id)
    assert "pptx_url" in data

    assert mock_db.add.call_count >= 2
    app.dependency_overrides.clear()


@pytest.mark.asyncio
@patch("app.api.v1.endpoints.render.upload_file", new_callable=AsyncMock)
async def test_render_creates_audit_log(mock_upload):
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()
    mock_upload.return_value = "s3://bucket/test/deck_v1.pptx"

    mock_db, mocks = _mock_render_db(deck_id, narrative_id)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/v1/decks/{deck_id}/render")

    assert response.status_code == 200
    add_calls = mock_db.add.call_args_list
    audit_added = any(
        hasattr(call.args[0], "action") and call.args[0].action == "deck_rendered"
        for call in add_calls
        if call.args
    )
    assert audit_added
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_render_409_no_verification():
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()

    mock_db, mocks = _mock_render_db(deck_id, narrative_id, has_verification=False)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/v1/decks/{deck_id}/render")

    assert response.status_code == 409
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_render_404_no_selection():
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()

    mock_db, mocks = _mock_render_db(deck_id, narrative_id, has_selection=False)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/v1/decks/{deck_id}/render")

    assert response.status_code == 404
    app.dependency_overrides.clear()


@pytest.mark.asyncio
@patch("app.api.v1.endpoints.render.upload_file", new_callable=AsyncMock)
async def test_render_generates_valid_pptx(mock_upload):
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()

    captured_bytes = {}

    async def capture_upload(data, filename):
        captured_bytes["data"] = data
        return "s3://bucket/test/deck.pptx"

    mock_upload.side_effect = capture_upload

    mock_db, mocks = _mock_render_db(deck_id, narrative_id)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/v1/decks/{deck_id}/render")

    assert response.status_code == 200
    assert captured_bytes["data"][:2] == b"PK"
    app.dependency_overrides.clear()


@pytest.mark.asyncio
@patch("app.api.v1.endpoints.render.download_file")
async def test_download_returns_pptx(mock_download):
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()
    mock_download.return_value = b"PK\x03\x04fake-pptx-content"

    mock_db, mocks = _mock_download_db(deck_id, narrative_id, has_output=True)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/decks/{deck_id}/render/download")

    assert response.status_code == 200
    assert "presentation" in response.headers.get("content-type", "")
    assert response.headers.get("content-disposition", "").startswith("attachment")
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_download_404_no_output():
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()

    mock_db, mocks = _mock_download_db(deck_id, narrative_id, has_output=False)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/decks/{deck_id}/render/download")

    assert response.status_code == 404
    app.dependency_overrides.clear()


@pytest.mark.asyncio
@patch("app.api.v1.endpoints.render.upload_file", new_callable=AsyncMock)
async def test_version_increments_on_rerender(mock_upload):
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()
    mock_upload.return_value = "s3://bucket/test/deck.pptx"

    mock_db, mocks = _mock_render_db(deck_id, narrative_id)

    original_execute = mock_db.execute
    call_count = {"n": 0}

    async def _execute_v2(stmt):
        call_count["n"] += 1
        if call_count["n"] == 8:
            return _make_scalar_result(2)
        return await original_execute(stmt)

    mock_db.execute = _execute_v2

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/v1/decks/{deck_id}/render")

    assert response.status_code == 200
    assert response.json()["version"] == 3
    app.dependency_overrides.clear()
