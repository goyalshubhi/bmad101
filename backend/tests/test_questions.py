import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.database import get_db
from app.services.questions.generator import generate_questions
from app.services.questions.parser import parse_answers


# --- Generator Tests ---


def test_generate_questions_rich_schema():
    schema = {
        "revenue": {"type": "numeric", "nullability": 0.0, "cardinality": 50},
        "profit": {"type": "numeric", "nullability": 0.0, "cardinality": 40},
        "cost": {"type": "numeric", "nullability": 0.02, "cardinality": 30},
        "date": {"type": "datetime", "nullability": 0.0, "cardinality": 12, "date_format": "%Y-%m"},
    }
    quality_report = {"issues": [], "status": "CLEAN"}

    questions = generate_questions(schema, quality_report)

    assert 4 <= len(questions) <= 5
    tiers = [q["tier"] for q in questions]
    assert tiers == sorted(tiers)
    assert any(q["tier"] == 1 for q in questions)

    for q in questions:
        assert "id" in q
        assert "template" in q
        assert "context" in q
        assert "suggestion_chips" in q
        assert isinstance(q["suggestion_chips"], list)


def test_generate_questions_minimal_schema():
    schema = {
        "value": {"type": "numeric", "nullability": 0.0, "cardinality": 10},
    }
    quality_report = {"issues": [], "status": "CLEAN"}

    questions = generate_questions(schema, quality_report)

    assert len(questions) >= 2
    tier1 = [q for q in questions if q["tier"] == 1]
    assert len(tier1) >= 1


def test_generate_questions_high_cardinality():
    schema = {
        "revenue": {"type": "numeric", "nullability": 0.0, "cardinality": 50},
        "profit": {"type": "numeric", "nullability": 0.0, "cardinality": 40},
        "product_id": {"type": "text", "nullability": 0.0, "cardinality": 5000},
    }
    quality_report = {"issues": [], "status": "CLEAN"}

    questions = generate_questions(schema, quality_report)

    templates = [q["template"] for q in questions]
    assert any("top" in t.lower() for t in templates)


def test_generate_questions_with_data_gaps():
    schema = {
        "revenue": {"type": "numeric", "nullability": 0.1, "cardinality": 50},
        "profit": {"type": "numeric", "nullability": 0.0, "cardinality": 40},
    }
    quality_report = {
        "issues": [{"severity": "warning", "description": "Missing values", "count": 15, "sample_rows": [1, 5]}],
        "status": "ISSUES_BLOCKING",
        "total_rows": 100,
    }

    questions = generate_questions(schema, quality_report)

    templates = [q["template"] for q in questions]
    assert any("missing" in t.lower() or "incomplete" in t.lower() for t in templates)


def test_generate_questions_data_gaps_below_threshold():
    schema = {
        "revenue": {"type": "numeric", "nullability": 0.0, "cardinality": 50},
        "profit": {"type": "numeric", "nullability": 0.0, "cardinality": 40},
    }
    quality_report = {
        "issues": [{"severity": "warning", "description": "Missing values", "count": 2, "sample_rows": [1]}],
        "status": "ISSUES_BLOCKING",
        "total_rows": 1000,
    }

    questions = generate_questions(schema, quality_report)

    templates = [q["template"] for q in questions]
    assert not any("missing" in t.lower() or "incomplete" in t.lower() for t in templates)


# --- Parser Tests ---


def test_parse_profit_keyword():
    questions = [{"id": "q1", "template": "test", "tier": 1}]
    answers = [{"question_id": "q1", "text": "Focus on profit margins"}]

    result = parse_answers(questions, answers)

    assert len(result["parsed"]) == 1
    parsed = result["parsed"][0]
    assert parsed["parsed_intent"] == "PROFIT"
    assert parsed["confidence"] == 0.9


def test_parse_growth_keyword():
    questions = [{"id": "q1", "template": "test", "tier": 1}]
    answers = [{"question_id": "q1", "text": "We care about revenue growth"}]

    result = parse_answers(questions, answers)

    parsed = result["parsed"][0]
    assert parsed["parsed_intent"] == "GROWTH"
    assert parsed["confidence"] == 0.85


def test_parse_ambiguous_answer():
    questions = [{"id": "q1", "template": "test", "tier": 1}]
    answers = [{"question_id": "q1", "text": "maybe the numbers"}]

    result = parse_answers(questions, answers)

    parsed = result["parsed"][0]
    assert parsed["confidence"] < 0.7


def test_parse_skip_answer():
    questions = [{"id": "q1", "template": "test", "tier": 1}]
    answers = [{"question_id": "q1", "text": "skip"}]

    result = parse_answers(questions, answers)

    parsed = result["parsed"][0]
    assert parsed["parsed_intent"] == "DEFAULT"
    assert parsed.get("defaulted") is True


def test_parse_empty_answer():
    questions = [{"id": "q1", "template": "test", "tier": 1}]
    answers = [{"question_id": "q1", "text": ""}]

    result = parse_answers(questions, answers)

    parsed = result["parsed"][0]
    assert parsed["parsed_intent"] == "DEFAULT"
    assert parsed.get("defaulted") is True


def test_ready_to_generate_all_tier1_answered():
    questions = [
        {"id": "q1", "template": "headline", "tier": 1},
        {"id": "q2", "template": "audience", "tier": 1},
        {"id": "q3", "template": "optional", "tier": 2},
    ]
    answers = [
        {"question_id": "q1", "text": "profit margins"},
        {"question_id": "q2", "text": "board of directors"},
    ]

    result = parse_answers(questions, answers)

    assert result["ready_to_generate"] is True


def test_parse_unknown_question_id_filtered():
    questions = [{"id": "q1", "template": "test", "tier": 1}]
    answers = [
        {"question_id": "q1", "text": "profit margins"},
        {"question_id": "fake_id", "text": "should be ignored"},
    ]

    result = parse_answers(questions, answers)

    assert len(result["parsed"]) == 1
    assert result["parsed"][0]["question_id"] == "q1"


def test_ready_to_generate_missing_tier1():
    questions = [
        {"id": "q1", "template": "headline", "tier": 1},
        {"id": "q2", "template": "audience", "tier": 1},
    ]
    answers = [
        {"question_id": "q1", "text": "profit margins"},
    ]

    result = parse_answers(questions, answers)

    assert result["ready_to_generate"] is False


# --- Endpoint Tests ---


@pytest.mark.asyncio
async def test_get_questions_endpoint():
    deck_id = uuid.uuid4()
    session_id = uuid.uuid4()

    mock_job = MagicMock()
    mock_job.validated_at = datetime.now(timezone.utc)
    mock_job.schema_json = {
        "revenue": {"type": "numeric", "nullability": 0.0, "cardinality": 50},
        "profit": {"type": "numeric", "nullability": 0.0, "cardinality": 40},
        "date": {"type": "datetime", "nullability": 0.0, "cardinality": 12},
    }
    mock_job.quality_report = {"issues": [], "status": "CLEAN"}

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_job
    mock_session.execute.return_value = mock_result
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, "id", session_id))

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/decks/{deck_id}/questions")

    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "questions" in data
    assert 4 <= len(data["questions"]) <= 5

    for q in data["questions"]:
        assert "id" in q
        assert "template" in q
        assert "suggestion_chips" in q

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_questions_not_validated():
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
        response = await client.get(f"/api/v1/decks/{deck_id}/questions")

    assert response.status_code == 400
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_answer_questions_endpoint():
    deck_id = uuid.uuid4()
    session_id = uuid.uuid4()

    mock_qs = MagicMock()
    mock_qs.id = session_id
    mock_qs.deck_id = deck_id
    mock_qs.version = 1
    mock_qs.questions_json = [
        {"id": "q1", "template": "headline", "tier": 1, "context": "test", "suggestion_chips": []},
        {"id": "q2", "template": "audience", "tier": 1, "context": "test", "suggestion_chips": []},
    ]
    mock_qs.answers_json = None

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_qs
    mock_session.execute.return_value = mock_result
    mock_session.commit = AsyncMock()

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/decks/{deck_id}/answer-questions",
            json={
                "session_id": str(session_id),
                "answers": [
                    {"question_id": "q1", "text": "Focus on profit margins"},
                    {"question_id": "q2", "text": "Board of directors"},
                ],
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert "parsed" in data
    assert "ready_to_generate" in data
    assert data["ready_to_generate"] is True
    assert len(data["parsed"]) == 2
    assert data["parsed"][0]["parsed_intent"] == "PROFIT"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_answer_questions_invalid_session():
    deck_id = uuid.uuid4()
    session_id = uuid.uuid4()

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
            f"/api/v1/decks/{deck_id}/answer-questions",
            json={
                "session_id": str(session_id),
                "answers": [{"question_id": "q1", "text": "test"}],
            },
        )

    assert response.status_code == 404
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_answer_questions_already_answered():
    deck_id = uuid.uuid4()
    session_id = uuid.uuid4()

    mock_qs = MagicMock()
    mock_qs.id = session_id
    mock_qs.deck_id = deck_id
    mock_qs.questions_json = [{"id": "q1", "template": "test", "tier": 1}]
    mock_qs.answers_json = {"parsed": [{"question_id": "q1"}], "ready_to_generate": True}

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_qs
    mock_session.execute.return_value = mock_result

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/decks/{deck_id}/answer-questions",
            json={
                "session_id": str(session_id),
                "answers": [{"question_id": "q1", "text": "profit"}],
            },
        )

    assert response.status_code == 409
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_answer_questions_response_includes_defaulted():
    deck_id = uuid.uuid4()
    session_id = uuid.uuid4()

    mock_qs = MagicMock()
    mock_qs.id = session_id
    mock_qs.deck_id = deck_id
    mock_qs.version = 1
    mock_qs.questions_json = [
        {"id": "q1", "template": "headline", "tier": 1, "context": "test", "suggestion_chips": []},
    ]
    mock_qs.answers_json = None

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_qs
    mock_session.execute.return_value = mock_result
    mock_session.commit = AsyncMock()

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/decks/{deck_id}/answer-questions",
            json={
                "session_id": str(session_id),
                "answers": [{"question_id": "q1", "text": "skip"}],
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["parsed"][0]["defaulted"] is True
    assert data["parsed"][0]["parsed_intent"] == "DEFAULT"
    app.dependency_overrides.clear()
