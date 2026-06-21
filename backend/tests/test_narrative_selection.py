import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.database import get_db


def _make_result(obj):
    r = MagicMock()
    r.scalar_one_or_none.return_value = obj
    return r


@pytest.mark.asyncio
async def test_select_narrative_success():
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()
    selection_id = uuid.uuid4()

    mock_narrative = MagicMock()
    mock_narrative.id = narrative_id
    mock_narrative.deck_id = deck_id

    mock_db = AsyncMock()
    call_count = {"n": 0}

    async def _execute(stmt):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _make_result(mock_narrative)
        else:
            return _make_result(None)

    mock_db.execute = _execute
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock(side_effect=lambda obj: (
        setattr(obj, "id", selection_id),
        setattr(obj, "narrative_id", narrative_id),
        setattr(obj, "user_edits_text", None),
    ))

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/decks/{deck_id}/select-narrative",
            json={"narrative_id": str(narrative_id)},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["selection_id"] == str(selection_id)
    assert data["narrative_id"] == str(narrative_id)
    assert data["user_edits_text"] is None

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_select_narrative_with_edits():
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()
    selection_id = uuid.uuid4()
    edited_text = "My custom narrative text"

    mock_narrative = MagicMock()
    mock_narrative.id = narrative_id
    mock_narrative.deck_id = deck_id

    mock_db = AsyncMock()
    call_count = {"n": 0}

    async def _execute(stmt):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _make_result(mock_narrative)
        else:
            return _make_result(None)

    mock_db.execute = _execute
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock(side_effect=lambda obj: (
        setattr(obj, "id", selection_id),
        setattr(obj, "narrative_id", narrative_id),
        setattr(obj, "user_edits_text", edited_text),
    ))

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/decks/{deck_id}/select-narrative",
            json={"narrative_id": str(narrative_id), "user_edits_text": edited_text},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["user_edits_text"] == edited_text

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_select_narrative_not_found():
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=_make_result(None))

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/decks/{deck_id}/select-narrative",
            json={"narrative_id": str(narrative_id)},
        )

    assert response.status_code == 404
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_select_narrative_upsert():
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()
    selection_id = uuid.uuid4()

    mock_narrative = MagicMock()
    mock_narrative.id = narrative_id
    mock_narrative.deck_id = deck_id

    mock_existing = MagicMock()
    mock_existing.id = selection_id
    mock_existing.deck_id = deck_id
    mock_existing.narrative_id = uuid.uuid4()
    mock_existing.user_edits_text = None

    mock_db = AsyncMock()
    call_count = {"n": 0}

    async def _execute(stmt):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _make_result(mock_narrative)
        else:
            return _make_result(mock_existing)

    mock_db.execute = _execute
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock(side_effect=lambda obj: (
        setattr(obj, "id", selection_id),
        setattr(obj, "narrative_id", narrative_id),
        setattr(obj, "user_edits_text", None),
    ))

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/decks/{deck_id}/select-narrative",
            json={"narrative_id": str(narrative_id)},
        )

    assert response.status_code == 200
    assert mock_existing.narrative_id == narrative_id

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_qa_summary_with_answers():
    deck_id = uuid.uuid4()

    mock_session = MagicMock()
    mock_session.questions_json = [
        {"id": "q1", "template": "What is the focus?"},
        {"id": "q2", "template": "Who is the audience?"},
    ]
    mock_session.answers_json = {
        "parsed": [
            {"question_id": "q1", "raw_answer": "profit margins", "parsed_intent": "PROFIT", "confidence": 0.9},
            {"question_id": "q2", "raw_answer": "board", "parsed_intent": "BOARD", "confidence": 0.85},
        ],
        "ready_to_generate": True,
    }

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=_make_result(mock_session))

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/decks/{deck_id}/qa-summary")

    assert response.status_code == 200
    data = response.json()
    assert len(data["questions"]) == 2
    assert data["questions"][0]["template"] == "What is the focus?"
    assert data["questions"][0]["answer"] == "profit margins"
    assert data["questions"][0]["parsed_intent"] == "PROFIT"
    assert data["questions"][1]["answer"] == "board"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_qa_summary_no_session():
    deck_id = uuid.uuid4()

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=_make_result(None))

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/decks/{deck_id}/qa-summary")

    assert response.status_code == 200
    data = response.json()
    assert data["questions"] == []

    app.dependency_overrides.clear()
