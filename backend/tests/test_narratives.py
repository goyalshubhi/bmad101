import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.database import get_db
from app.services.narratives.angle_detector import detect_angles
from app.services.narratives.template_engine import generate_narratives
from app.services.narratives.assumption_extractor import extract_assumptions


# --- Test DataFrames ---

def _make_trend_df():
    """DataFrame with clear upward trend in revenue."""
    dates = pd.date_range("2024-01-01", periods=12, freq="MS")
    return pd.DataFrame({
        "date": dates,
        "revenue": np.linspace(100, 200, 12) + np.random.default_rng(42).normal(0, 5, 12),
        "cost": np.linspace(50, 60, 12) + np.random.default_rng(43).normal(0, 2, 12),
        "region": ["North", "South", "East", "West"] * 3,
    })


def _make_comparison_df():
    """DataFrame with clear top performer in a category."""
    return pd.DataFrame({
        "category": ["A", "A", "A", "B", "B", "C", "C", "C", "C", "C"],
        "sales": [100, 120, 110, 30, 25, 200, 210, 190, 220, 205],
        "profit": [20, 25, 22, 5, 4, 50, 55, 48, 52, 51],
    })


def _make_outlier_df():
    """DataFrame with clear outliers in a numeric column."""
    values = [10, 12, 11, 13, 10, 11, 12, 100, 11, 10, 12, 11, 13, -50, 10]
    return pd.DataFrame({
        "metric": values,
        "label": [f"item_{i}" for i in range(len(values))],
    })


def _make_minimal_df():
    """Minimal DataFrame with few rows."""
    return pd.DataFrame({
        "value": [1, 2, 3],
    })


PARSED_ANSWERS_PROFIT = [
    {"question_id": "q1", "raw_answer": "profit margins", "parsed_intent": "PROFIT", "confidence": 0.9},
    {"question_id": "q2", "raw_answer": "board of directors", "parsed_intent": "BOARD", "confidence": 0.9},
]

PARSED_ANSWERS_GROWTH = [
    {"question_id": "q1", "raw_answer": "revenue growth", "parsed_intent": "GROWTH", "confidence": 0.85},
    {"question_id": "q2", "raw_answer": "investors", "parsed_intent": "INVESTORS", "confidence": 0.85},
]

PARSED_ANSWERS_LOW_CONFIDENCE = [
    {"question_id": "q1", "raw_answer": "maybe numbers", "parsed_intent": "UNKNOWN", "confidence": 0.5},
]

PARSED_ANSWERS_SKIPPED = [
    {"question_id": "q1", "raw_answer": "skip", "parsed_intent": "DEFAULT", "confidence": 0.0, "defaulted": True},
]


# --- Angle Detector Tests ---


def test_detect_trends():
    df = _make_trend_df()
    angles = detect_angles(df, PARSED_ANSWERS_PROFIT)

    trend_angles = [a for a in angles if a["type"] == "TREND"]
    assert len(trend_angles) >= 1

    for a in trend_angles:
        assert "id" in a
        assert "strength" in a
        assert 0 <= a["strength"] <= 1
        assert "evidence" in a
        assert "columns" in a
        assert a["evidence"]["direction"] in ("upward", "downward")


def test_detect_comparisons():
    df = _make_comparison_df()
    angles = detect_angles(df, PARSED_ANSWERS_PROFIT)

    comparison_angles = [a for a in angles if a["type"] == "COMPARISON"]
    assert len(comparison_angles) >= 1

    for a in comparison_angles:
        assert a["evidence"]["num_categories"] >= 2


def test_detect_outliers():
    df = _make_outlier_df()
    angles = detect_angles(df, PARSED_ANSWERS_PROFIT)

    outlier_angles = [a for a in angles if a["type"] == "OUTLIER"]
    assert len(outlier_angles) >= 1

    for a in outlier_angles:
        assert a["evidence"]["outlier_count"] > 0


def test_angles_capped_at_3():
    df = _make_trend_df()
    angles = detect_angles(df, PARSED_ANSWERS_PROFIT)
    assert len(angles) <= 3


def test_angles_sorted_by_strength():
    df = _make_trend_df()
    angles = detect_angles(df, PARSED_ANSWERS_PROFIT)
    strengths = [a["strength"] for a in angles]
    assert strengths == sorted(strengths, reverse=True)


def test_detect_angles_minimal_data():
    df = _make_minimal_df()
    angles = detect_angles(df, PARSED_ANSWERS_PROFIT)
    # Should not crash, may return empty or limited angles
    assert isinstance(angles, list)


# --- Template Engine Tests ---


def test_generate_narratives_with_trend():
    df = _make_trend_df()
    angles = detect_angles(df, PARSED_ANSWERS_PROFIT)
    narratives = generate_narratives(angles, PARSED_ANSWERS_PROFIT, "BOARD")

    assert len(narratives) >= 2
    for n in narratives:
        assert "id" in n
        assert "title" in n
        assert "sections" in n
        assert "tone" in n
        assert len(n["sections"]) > 0


def test_generate_narratives_multiple_tones():
    df = _make_trend_df()
    angles = detect_angles(df, PARSED_ANSWERS_GROWTH)
    narratives = generate_narratives(angles, PARSED_ANSWERS_GROWTH, "INVESTORS")

    tones = {n["tone"] for n in narratives}
    assert "INVESTORS" in tones
    assert len(tones) >= 2


def test_generate_narratives_fallback_no_angles():
    narratives = generate_narratives([], PARSED_ANSWERS_PROFIT, "DEFAULT")
    assert len(narratives) == 1
    assert narratives[0]["title"] == "Data Summary"


def test_narrative_sections_have_required_fields():
    df = _make_comparison_df()
    angles = detect_angles(df, PARSED_ANSWERS_PROFIT)
    narratives = generate_narratives(angles, PARSED_ANSWERS_PROFIT, "EXECUTIVE")

    for n in narratives:
        for s in n["sections"]:
            assert "order" in s
            assert "heading" in s
            assert "body" in s
            assert "evidence_summary" in s
            assert isinstance(s["body"], str)
            assert len(s["body"]) > 0


# --- Assumption Extractor Tests ---


def test_extract_assumptions_with_missing_data():
    df = _make_trend_df().copy()
    df.loc[0, "revenue"] = None
    df.loc[1, "revenue"] = None

    angles = detect_angles(df, PARSED_ANSWERS_PROFIT)
    narratives = generate_narratives(angles, PARSED_ANSWERS_PROFIT, "BOARD")
    assumptions = extract_assumptions(df, angles, narratives, PARSED_ANSWERS_PROFIT)

    data_quality = [a for a in assumptions if a["category"] == "DATA_QUALITY"]
    assert len(data_quality) >= 1


def test_extract_assumptions_statistical():
    df = _make_trend_df()
    angles = detect_angles(df, PARSED_ANSWERS_PROFIT)
    narratives = generate_narratives(angles, PARSED_ANSWERS_PROFIT, "BOARD")
    assumptions = extract_assumptions(df, angles, narratives, PARSED_ANSWERS_PROFIT)

    stat_assumptions = [a for a in assumptions if a["category"] == "STATISTICAL"]
    # Trend angles always generate a linear assumption
    trend_angles = [a for a in angles if a["type"] == "TREND"]
    if trend_angles:
        assert len(stat_assumptions) >= 1


def test_extract_assumptions_low_confidence_intent():
    df = _make_trend_df()
    angles = detect_angles(df, PARSED_ANSWERS_LOW_CONFIDENCE)
    narratives = generate_narratives(angles, PARSED_ANSWERS_LOW_CONFIDENCE, "DEFAULT")
    assumptions = extract_assumptions(df, angles, narratives, PARSED_ANSWERS_LOW_CONFIDENCE)

    intent_assumptions = [a for a in assumptions if a["category"] == "INTENT"]
    assert len(intent_assumptions) >= 1


def test_extract_assumptions_skipped_answers():
    df = _make_trend_df()
    angles = detect_angles(df, PARSED_ANSWERS_SKIPPED)
    narratives = generate_narratives(angles, PARSED_ANSWERS_SKIPPED, "DEFAULT")
    assumptions = extract_assumptions(df, angles, narratives, PARSED_ANSWERS_SKIPPED)

    intent_assumptions = [a for a in assumptions if a["category"] == "INTENT"]
    assert any("skipped" in a["description"].lower() for a in intent_assumptions)


def test_extract_assumptions_small_dataset():
    df = _make_minimal_df()
    angles = detect_angles(df, PARSED_ANSWERS_PROFIT)
    narratives = generate_narratives(angles, PARSED_ANSWERS_PROFIT, "DEFAULT")
    assumptions = extract_assumptions(df, angles, narratives, PARSED_ANSWERS_PROFIT)

    scope_assumptions = [a for a in assumptions if a["category"] == "SCOPE"]
    assert any("rows" in a["description"].lower() for a in scope_assumptions)


def test_assumption_fields():
    df = _make_trend_df()
    angles = detect_angles(df, PARSED_ANSWERS_PROFIT)
    narratives = generate_narratives(angles, PARSED_ANSWERS_PROFIT, "BOARD")
    assumptions = extract_assumptions(df, angles, narratives, PARSED_ANSWERS_PROFIT)

    for a in assumptions:
        assert "id" in a
        assert a["category"] in ("DATA_QUALITY", "STATISTICAL", "INTENT", "SCOPE")
        assert a["severity"] in ("LOW", "MEDIUM", "HIGH")
        assert isinstance(a["description"], str)
        assert isinstance(a["auto_resolved"], bool)


# --- Endpoint Tests ---


@pytest.mark.asyncio
async def test_generate_narratives_endpoint():
    deck_id = uuid.uuid4()
    session_id = uuid.uuid4()
    narrative_id = uuid.uuid4()

    mock_qs = MagicMock()
    mock_qs.id = session_id
    mock_qs.deck_id = deck_id
    mock_qs.answers_json = {
        "parsed": [
            {"question_id": "q1", "raw_answer": "profit margins", "parsed_intent": "PROFIT", "confidence": 0.9},
            {"question_id": "q2", "raw_answer": "board", "parsed_intent": "BOARD", "confidence": 0.9},
        ],
        "ready_to_generate": True,
    }

    mock_job = MagicMock()
    mock_job.validated_at = datetime.now(timezone.utc)
    mock_job.file_path = "uploads/test.csv"

    # Mock DB session to return different objects for different queries
    mock_db = AsyncMock()
    call_count = {"n": 0}

    def _make_result(obj):
        r = MagicMock()
        r.scalar_one_or_none.return_value = obj
        return r

    async def _execute(stmt):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _make_result(mock_qs)
        else:
            return _make_result(mock_job)

    mock_db.execute = _execute
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, "id", narrative_id))
    mock_db.add = MagicMock()

    async def override_get_db():
        yield mock_db

    # Mock the data loader to return a test DataFrame
    test_df = _make_trend_df()

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.services.narratives.data_loader.download_file", return_value=b"dummy"):
        with patch("app.services.narratives.data_loader.pd.read_csv", return_value=test_df):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/v1/decks/{deck_id}/generate-narratives",
                    json={"session_id": str(session_id)},
                )

    assert response.status_code == 200
    data = response.json()
    assert "narrative_id" in data
    assert "angles" in data
    assert "narratives" in data
    assert "assumptions" in data
    assert isinstance(data["angles"], list)
    assert isinstance(data["narratives"], list)
    assert len(data["narratives"]) >= 1

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_generate_narratives_no_session():
    deck_id = uuid.uuid4()
    session_id = uuid.uuid4()

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/decks/{deck_id}/generate-narratives",
            json={"session_id": str(session_id)},
        )

    assert response.status_code == 404
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_generate_narratives_not_answered():
    deck_id = uuid.uuid4()
    session_id = uuid.uuid4()

    mock_qs = MagicMock()
    mock_qs.id = session_id
    mock_qs.deck_id = deck_id
    mock_qs.answers_json = None

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_qs
    mock_db.execute.return_value = mock_result

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/decks/{deck_id}/generate-narratives",
            json={"session_id": str(session_id)},
        )

    assert response.status_code == 400
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_generate_narratives_not_ready():
    deck_id = uuid.uuid4()
    session_id = uuid.uuid4()

    mock_qs = MagicMock()
    mock_qs.id = session_id
    mock_qs.deck_id = deck_id
    mock_qs.answers_json = {
        "parsed": [
            {"question_id": "q1", "raw_answer": "test", "parsed_intent": "UNKNOWN", "confidence": 0.5},
        ],
        "ready_to_generate": False,
    }

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_qs
    mock_db.execute.return_value = mock_result

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/decks/{deck_id}/generate-narratives",
            json={"session_id": str(session_id)},
        )

    assert response.status_code == 400
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_select_narrative_endpoint():
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()

    mock_narrative = MagicMock()
    mock_narrative.id = narrative_id
    mock_narrative.deck_id = deck_id
    mock_narrative.version = 1
    mock_narrative.narratives_json = [
        {
            "id": str(uuid.uuid4()),
            "title": "Executive Summary: Trend Analysis",
            "sections": [
                {
                    "order": 0,
                    "angle_id": "a1",
                    "angle_type": "TREND",
                    "heading": "Revenue shows upward trend",
                    "body": "Revenue is trending up.",
                    "evidence_summary": "Slope: 8.3, R-squared: 0.95",
                }
            ],
            "tone": "EXECUTIVE",
            "angle_ids": ["a1"],
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Board Report: Trend Analysis",
            "sections": [
                {
                    "order": 0,
                    "angle_id": "a1",
                    "angle_type": "TREND",
                    "heading": "Revenue shows upward trend",
                    "body": "The board should note upward revenue.",
                    "evidence_summary": "Slope: 8.3, R-squared: 0.95",
                }
            ],
            "tone": "BOARD",
            "angle_ids": ["a1"],
        },
    ]
    mock_narrative.selected_index = None

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_narrative
    mock_db.execute.return_value = mock_result
    mock_db.commit = AsyncMock()

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/decks/{deck_id}/narratives/{narrative_id}/select",
            json={"selected_index": 1},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["selected_index"] == 1
    assert data["selected_narrative"]["tone"] == "BOARD"
    assert data["narrative_id"] == str(narrative_id)

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_select_narrative_not_found():
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/decks/{deck_id}/narratives/{narrative_id}/select",
            json={"selected_index": 0},
        )

    assert response.status_code == 404
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_select_narrative_invalid_index():
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()

    mock_narrative = MagicMock()
    mock_narrative.id = narrative_id
    mock_narrative.deck_id = deck_id
    mock_narrative.version = 1
    mock_narrative.narratives_json = [
        {"id": "n1", "title": "Only one", "sections": [], "tone": "DEFAULT", "angle_ids": []},
    ]

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_narrative
    mock_db.execute.return_value = mock_result

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/decks/{deck_id}/narratives/{narrative_id}/select",
            json={"selected_index": 5},
        )

    assert response.status_code == 400
    app.dependency_overrides.clear()
