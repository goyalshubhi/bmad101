import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.database import get_db


def _make_result(obj):
    r = MagicMock()
    r.scalar_one_or_none.return_value = obj
    return r


def _mock_db_for_verify(deck_id, narrative_id, has_selection=True, has_narrative=True, has_job=True):
    mock_selection = MagicMock()
    mock_selection.deck_id = deck_id
    mock_selection.narrative_id = narrative_id
    mock_selection.user_edits_text = None

    mock_narrative = MagicMock()
    mock_narrative.id = narrative_id
    mock_narrative.narrative_text = "Revenue was $1,000.50 and grew 15.3% over the year."

    mock_job = MagicMock()
    mock_job.file_url = "uploads/test.csv"
    mock_job.schema_json = {"columns": [{"name": "sales", "dtype": "float64"}]}
    mock_job.validated_at = "2024-01-01"

    mock_db = AsyncMock()
    call_count = {"n": 0}

    async def _execute(stmt):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _make_result(mock_selection if has_selection else None)
        elif call_count["n"] == 2:
            return _make_result(mock_narrative if has_narrative else None)
        elif call_count["n"] == 3:
            return _make_result(mock_job if has_job else None)
        return _make_result(None)

    mock_db.execute = _execute
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()

    report_id = uuid.uuid4()
    mock_db.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, "id", report_id))

    return mock_db


@pytest.mark.asyncio
@patch("app.api.v1.endpoints.verify.load_dataframe")
async def test_verify_returns_report(mock_load):
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()

    mock_load.return_value = pd.DataFrame({
        "sales": [100.0, 200.0, 300.0, 400.0],
    })

    mock_db = _mock_db_for_verify(deck_id, narrative_id)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/v1/decks/{deck_id}/verify")

    assert response.status_code == 200
    data = response.json()
    assert "report_id" in data
    assert data["deck_id"] == str(deck_id)
    assert data["narrative_id"] == str(narrative_id)
    assert isinstance(data["passed"], bool)
    assert "checks" in data
    assert "check_a" in data["checks"]
    assert "check_b" in data["checks"]
    assert "check_c" in data["checks"]
    assert "check_d" in data["checks"]
    assert "check_e" in data["checks"]
    assert isinstance(data["figure_traces"], list)

    for check in data["checks"].values():
        assert check["status"] in ("pass", "fail")

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_verify_404_no_selection():
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()

    mock_db = _mock_db_for_verify(deck_id, narrative_id, has_selection=False)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/v1/decks/{deck_id}/verify")

    assert response.status_code == 404
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_verify_400_no_validated_job():
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()

    mock_db = _mock_db_for_verify(deck_id, narrative_id, has_job=False)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/v1/decks/{deck_id}/verify")

    assert response.status_code == 400
    app.dependency_overrides.clear()


@pytest.mark.asyncio
@patch("app.api.v1.endpoints.verify.load_dataframe")
async def test_verify_passed_false_when_check_fails(mock_load):
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()

    mock_load.return_value = pd.DataFrame({
        "sales": [100.0, 200.0, 300.0],
    })

    mock_db = _mock_db_for_verify(deck_id, narrative_id)

    call_count = {"n": 0}
    mock_narrative = MagicMock()
    mock_narrative.id = narrative_id
    mock_narrative.narrative_text = "Revenue of $999999 shows a consistent increasing trend YoY."

    mock_selection = MagicMock()
    mock_selection.deck_id = deck_id
    mock_selection.narrative_id = narrative_id
    mock_selection.user_edits_text = None

    mock_job = MagicMock()
    mock_job.file_url = "uploads/test.csv"
    mock_job.schema_json = {"columns": []}
    mock_job.validated_at = "2024-01-01"

    async def _execute(stmt):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _make_result(mock_selection)
        elif call_count["n"] == 2:
            return _make_result(mock_narrative)
        elif call_count["n"] == 3:
            return _make_result(mock_job)
        return _make_result(None)

    mock_db.execute = _execute

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/v1/decks/{deck_id}/verify")

    assert response.status_code == 200
    data = response.json()
    assert data["passed"] is False

    app.dependency_overrides.clear()


@pytest.mark.asyncio
@patch("app.api.v1.endpoints.verify.load_dataframe")
async def test_verify_400_file_not_found(mock_load):
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()

    mock_load.side_effect = FileNotFoundError("Object not found")

    mock_db = _mock_db_for_verify(deck_id, narrative_id)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/v1/decks/{deck_id}/verify")

    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_verify_400_empty_narrative():
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()

    mock_selection = MagicMock()
    mock_selection.deck_id = deck_id
    mock_selection.narrative_id = narrative_id
    mock_selection.user_edits_text = ""

    mock_narrative = MagicMock()
    mock_narrative.id = narrative_id
    mock_narrative.narrative_text = ""

    mock_db = AsyncMock()
    call_count = {"n": 0}

    async def _execute(stmt):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _make_result(mock_selection)
        elif call_count["n"] == 2:
            return _make_result(mock_narrative)
        return _make_result(None)

    mock_db.execute = _execute

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/v1/decks/{deck_id}/verify")

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()
    app.dependency_overrides.clear()


def _mock_db_for_apply_fix(deck_id, narrative_id, report_id):
    mock_report = MagicMock()
    mock_report.id = report_id
    mock_report.deck_id = deck_id
    mock_report.narrative_id = narrative_id
    mock_report.checks_json = {
        "check_a": {"status": "fail", "expected": "$100", "actual": "$90"},
        "check_b": {"status": "pass", "expected": "$50", "actual": "$50"},
    }

    mock_selection = MagicMock()
    mock_selection.deck_id = deck_id
    mock_selection.narrative_id = narrative_id
    mock_selection.user_edits_text = None

    mock_narrative = MagicMock()
    mock_narrative.id = narrative_id
    mock_narrative.narrative_text = "Revenue was $1,000.50 and grew 15.3% over the year."

    mock_job = MagicMock()
    mock_job.file_url = "uploads/test.csv"
    mock_job.schema_json = {"columns": [{"name": "sales", "dtype": "float64"}]}
    mock_job.validated_at = "2024-01-01"

    mock_db = AsyncMock()
    call_count = {"n": 0}

    async def _execute(stmt):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _make_result(mock_report)
        elif call_count["n"] == 2:
            return _make_result(mock_selection)
        elif call_count["n"] == 3:
            return _make_result(mock_narrative)
        elif call_count["n"] == 4:
            return _make_result(mock_job)
        return _make_result(None)

    mock_db.execute = _execute
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()

    new_report_id = uuid.uuid4()
    mock_db.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, "id", new_report_id))

    return mock_db, new_report_id


@pytest.mark.asyncio
@patch("app.api.v1.endpoints.verify.load_dataframe")
async def test_apply_fix_creates_new_report(mock_load):
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()
    report_id = uuid.uuid4()

    mock_load.return_value = pd.DataFrame({
        "sales": [100.0, 200.0, 300.0, 400.0],
    })

    mock_db, new_report_id = _mock_db_for_apply_fix(deck_id, narrative_id, report_id)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/decks/{deck_id}/verify/apply-fix",
            json={
                "report_id": str(report_id),
                "check_name": "check_a",
                "fix_type": "exclude_rows",
                "parameters": {"row_ids": [0]},
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert "report_id" in data
    assert data["deck_id"] == str(deck_id)
    assert isinstance(data["passed"], bool)
    assert "checks" in data

    add_calls = mock_db.add.call_args_list
    added_types = [type(call[0][0]).__name__ for call in add_calls]
    assert "ReconciliationReport" in added_types
    assert "AuditLog" in added_types

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_apply_fix_404_invalid_report():
    deck_id = uuid.uuid4()
    report_id = uuid.uuid4()

    mock_db = AsyncMock()

    async def _execute(stmt):
        return _make_result(None)

    mock_db.execute = _execute

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/decks/{deck_id}/verify/apply-fix",
            json={
                "report_id": str(report_id),
                "check_name": "check_a",
                "fix_type": "exclude_rows",
                "parameters": {"row_ids": [0]},
            },
        )

    assert response.status_code == 404
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_apply_fix_400_empty_row_ids():
    deck_id = uuid.uuid4()
    report_id = uuid.uuid4()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/decks/{deck_id}/verify/apply-fix",
            json={
                "report_id": str(report_id),
                "check_name": "check_a",
                "fix_type": "exclude_rows",
                "parameters": {"row_ids": []},
            },
        )

    assert response.status_code == 400
    assert "row_ids" in response.json()["detail"].lower()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_apply_fix_400_invalid_check_name():
    deck_id = uuid.uuid4()
    report_id = uuid.uuid4()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/decks/{deck_id}/verify/apply-fix",
            json={
                "report_id": str(report_id),
                "check_name": "check_z",
                "fix_type": "exclude_rows",
                "parameters": {"row_ids": [0]},
            },
        )

    assert response.status_code == 400
    assert "invalid check name" in response.json()["detail"].lower()
    app.dependency_overrides.clear()


def _mock_db_for_dismiss(deck_id, narrative_id, report_id, check_status="fail"):
    mock_report = MagicMock()
    mock_report.id = report_id
    mock_report.deck_id = deck_id
    mock_report.narrative_id = narrative_id
    mock_report.checks_json = {
        "check_a": {"status": check_status, "expected": "$100", "actual": "$90"},
        "check_b": {"status": "pass", "expected": "$50", "actual": "$50"},
        "check_c": {"status": "pass", "expected": "ok", "actual": "ok"},
        "check_d": {"status": "pass", "expected": "ok", "actual": "ok"},
        "check_e": {"status": "pass", "expected": "ok", "actual": "ok"},
    }
    mock_report.figure_traces = []
    mock_report.passed = False

    mock_db = AsyncMock()

    async def _execute(stmt):
        return _make_result(mock_report)

    mock_db.execute = _execute
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    return mock_db, mock_report


@pytest.mark.asyncio
async def test_dismiss_check_updates_status():
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()
    report_id = uuid.uuid4()

    mock_db, mock_report = _mock_db_for_dismiss(deck_id, narrative_id, report_id)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/decks/{deck_id}/verify/dismiss-check",
            json={
                "report_id": str(report_id),
                "check_name": "check_a",
                "reason": "Known data gap, not material",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["checks"]["check_a"]["status"] == "dismissed"
    assert data["checks"]["check_a"]["dismissed_reason"] == "Known data gap, not material"
    assert "dismissed_at" in data["checks"]["check_a"]
    assert data["passed"] is True

    add_calls = mock_db.add.call_args_list
    added_types = [type(call[0][0]).__name__ for call in add_calls]
    assert "AuditLog" in added_types

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_dismiss_check_empty_reason_400():
    deck_id = uuid.uuid4()
    report_id = uuid.uuid4()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/decks/{deck_id}/verify/dismiss-check",
            json={
                "report_id": str(report_id),
                "check_name": "check_a",
                "reason": "   ",
            },
        )

    assert response.status_code == 422
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_dismiss_check_already_dismissed_400():
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()
    report_id = uuid.uuid4()

    mock_db, _ = _mock_db_for_dismiss(deck_id, narrative_id, report_id, check_status="dismissed")

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/decks/{deck_id}/verify/dismiss-check",
            json={
                "report_id": str(report_id),
                "check_name": "check_a",
                "reason": "Some reason",
            },
        )

    assert response.status_code == 400
    assert "already dismissed" in response.json()["detail"].lower()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_dismiss_check_recomputes_passed():
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()
    report_id = uuid.uuid4()

    mock_db, mock_report = _mock_db_for_dismiss(deck_id, narrative_id, report_id, check_status="fail")

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/decks/{deck_id}/verify/dismiss-check",
            json={
                "report_id": str(report_id),
                "check_name": "check_a",
                "reason": "Acceptable variance",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["passed"] is True
    assert mock_report.passed is True

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_dismiss_check_invalid_check_name_400():
    deck_id = uuid.uuid4()
    report_id = uuid.uuid4()
    narrative_id = uuid.uuid4()

    mock_db, _ = _mock_db_for_dismiss(deck_id, narrative_id, report_id)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/decks/{deck_id}/verify/dismiss-check",
            json={
                "report_id": str(report_id),
                "check_name": "check_z",
                "reason": "Some reason",
            },
        )

    assert response.status_code == 400
    assert "invalid check name" in response.json()["detail"].lower()
    app.dependency_overrides.clear()


# --- Assumption action tests ---

SAMPLE_ASSUMPTIONS = [
    {"text": "Based on 500 rows.", "flag_type": "EXPLICIT", "confidence": 1.0, "source_reference": "data_loader"},
    {"text": "Growing trend.", "flag_type": "PATTERN", "confidence": 0.75, "source_reference": "angle_detector"},
    {"text": "Scope limited.", "flag_type": "INFERRED", "confidence": 0.40, "source_reference": "angle_detector"},
]


def _mock_db_for_assumption_action(deck_id, narrative_id, report_id, assumptions=None, existing_actions=None):
    mock_report = MagicMock()
    mock_report.id = report_id
    mock_report.deck_id = deck_id
    mock_report.narrative_id = narrative_id
    mock_report.checks_json = {
        "check_a": {"status": "pass", "expected": None, "actual": None},
    }
    mock_report.figure_traces = []
    mock_report.assumption_actions_json = existing_actions
    mock_report.passed = True

    mock_narrative = MagicMock()
    mock_narrative.id = narrative_id
    mock_narrative.assumptions_json = assumptions if assumptions is not None else SAMPLE_ASSUMPTIONS

    mock_db = AsyncMock()
    call_count = {"n": 0}

    async def _execute(stmt):
        call_count["n"] += 1
        stmt_str = str(stmt)
        if "reconciliation_reports" in stmt_str:
            return _make_result(mock_report)
        if "narratives" in stmt_str:
            return _make_result(mock_narrative)
        return _make_result(mock_report)

    mock_db.execute = _execute
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    return mock_db, mock_report


@pytest.mark.asyncio
async def test_assumption_action_acknowledge_pattern():
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()
    report_id = uuid.uuid4()

    mock_db, mock_report = _mock_db_for_assumption_action(deck_id, narrative_id, report_id)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/decks/{deck_id}/verify/assumption-action",
            json={
                "report_id": str(report_id),
                "assumption_index": 1,
                "action": "acknowledged",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert "assumptions" in data
    assert len(data["assumptions"]) == 3
    assert data["assumptions"][1]["flag_type"] == "PATTERN"
    assert len(data["assumption_actions"]) > 0

    add_calls = mock_db.add.call_args_list
    added_types = [type(call[0][0]).__name__ for call in add_calls]
    assert "AuditLog" in added_types

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_assumption_action_sign_off_inferred():
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()
    report_id = uuid.uuid4()

    mock_db, mock_report = _mock_db_for_assumption_action(deck_id, narrative_id, report_id)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/decks/{deck_id}/verify/assumption-action",
            json={
                "report_id": str(report_id),
                "assumption_index": 2,
                "action": "signed_off",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["assumptions"][2]["flag_type"] == "INFERRED"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_assumption_action_invalid_index_400():
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()
    report_id = uuid.uuid4()

    mock_db, _ = _mock_db_for_assumption_action(deck_id, narrative_id, report_id)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/decks/{deck_id}/verify/assumption-action",
            json={
                "report_id": str(report_id),
                "assumption_index": 99,
                "action": "acknowledged",
            },
        )

    assert response.status_code == 400
    assert "invalid assumption index" in response.json()["detail"].lower()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_assumption_action_mismatched_action_flag_type_400():
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()
    report_id = uuid.uuid4()

    mock_db, _ = _mock_db_for_assumption_action(deck_id, narrative_id, report_id)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/decks/{deck_id}/verify/assumption-action",
            json={
                "report_id": str(report_id),
                "assumption_index": 1,
                "action": "signed_off",
            },
        )

    assert response.status_code == 400
    assert "not valid" in response.json()["detail"].lower()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_assumption_action_explicit_no_action_400():
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()
    report_id = uuid.uuid4()

    mock_db, _ = _mock_db_for_assumption_action(deck_id, narrative_id, report_id)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/decks/{deck_id}/verify/assumption-action",
            json={
                "report_id": str(report_id),
                "assumption_index": 0,
                "action": "acknowledged",
            },
        )

    assert response.status_code == 400
    assert "does not require" in response.json()["detail"].lower()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_assumption_action_404_invalid_report():
    deck_id = uuid.uuid4()
    report_id = uuid.uuid4()

    mock_db = AsyncMock()

    async def _execute(stmt):
        return _make_result(None)

    mock_db.execute = _execute

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/decks/{deck_id}/verify/assumption-action",
            json={
                "report_id": str(report_id),
                "assumption_index": 0,
                "action": "acknowledged",
            },
        )

    assert response.status_code == 404
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_assumption_action_rejected():
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()
    report_id = uuid.uuid4()

    mock_db, _ = _mock_db_for_assumption_action(deck_id, narrative_id, report_id)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/decks/{deck_id}/verify/assumption-action",
            json={
                "report_id": str(report_id),
                "assumption_index": 2,
                "action": "rejected",
            },
        )

    assert response.status_code == 200
    app.dependency_overrides.clear()


# --- Verify complete tests ---

def _mock_db_for_complete(deck_id, narrative_id, report_id, checks_json=None, assumptions=None, actions=None):
    mock_report = MagicMock()
    mock_report.id = report_id
    mock_report.deck_id = deck_id
    mock_report.narrative_id = narrative_id
    mock_report.checks_json = checks_json or {
        "check_a": {"status": "pass"},
    }
    mock_report.assumption_actions_json = actions

    mock_narrative = MagicMock()
    mock_narrative.id = narrative_id
    mock_narrative.assumptions_json = assumptions if assumptions is not None else SAMPLE_ASSUMPTIONS

    mock_db = AsyncMock()

    async def _execute(stmt):
        stmt_str = str(stmt)
        if "narratives" in stmt_str:
            return _make_result(mock_narrative)
        return _make_result(mock_report)

    mock_db.execute = _execute
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    return mock_db


@pytest.mark.asyncio
async def test_verify_complete_creates_audit_log():
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()
    report_id = uuid.uuid4()

    actions = [
        {"assumption_index": 1, "action": "acknowledged"},
        {"assumption_index": 2, "action": "signed_off"},
    ]
    mock_db = _mock_db_for_complete(deck_id, narrative_id, report_id, actions=actions)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/v1/decks/{deck_id}/verify/complete")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    add_calls = mock_db.add.call_args_list
    added_types = [type(call[0][0]).__name__ for call in add_calls]
    assert "AuditLog" in added_types

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_verify_complete_400_unresolved_checks():
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()
    report_id = uuid.uuid4()

    checks = {"check_a": {"status": "fail"}}
    mock_db = _mock_db_for_complete(deck_id, narrative_id, report_id, checks_json=checks)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/v1/decks/{deck_id}/verify/complete")

    assert response.status_code == 400
    assert "check" in response.json()["detail"].lower()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_verify_complete_400_unresolved_assumptions():
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()
    report_id = uuid.uuid4()

    mock_db = _mock_db_for_complete(deck_id, narrative_id, report_id, actions=None)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/v1/decks/{deck_id}/verify/complete")

    assert response.status_code == 400
    assert "assumption" in response.json()["detail"].lower()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
@patch("app.api.v1.endpoints.verify.load_dataframe")
async def test_verify_response_includes_assumptions(mock_load):
    deck_id = uuid.uuid4()
    narrative_id = uuid.uuid4()

    mock_load.return_value = pd.DataFrame({"sales": [100.0, 200.0, 300.0, 400.0]})

    mock_selection = MagicMock()
    mock_selection.deck_id = deck_id
    mock_selection.narrative_id = narrative_id
    mock_selection.user_edits_text = None

    mock_narrative = MagicMock()
    mock_narrative.id = narrative_id
    mock_narrative.narrative_text = "Revenue was $1,000.50."
    mock_narrative.assumptions_json = SAMPLE_ASSUMPTIONS

    mock_job = MagicMock()
    mock_job.file_url = "uploads/test.csv"
    mock_job.schema_json = {"columns": []}
    mock_job.validated_at = "2024-01-01"

    mock_db = AsyncMock()
    call_count = {"n": 0}

    async def _execute(stmt):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _make_result(mock_selection)
        elif call_count["n"] == 2:
            return _make_result(mock_narrative)
        elif call_count["n"] == 3:
            return _make_result(mock_job)
        return _make_result(None)

    mock_db.execute = _execute
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    report_id = uuid.uuid4()
    mock_db.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, "id", report_id))

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/v1/decks/{deck_id}/verify")

    assert response.status_code == 200
    data = response.json()
    assert "assumptions" in data
    assert len(data["assumptions"]) == 3
    assert data["assumptions"][0]["flag_type"] == "EXPLICIT"
    assert data["assumptions"][1]["flag_type"] == "PATTERN"
    assert data["assumptions"][2]["flag_type"] == "INFERRED"
    assert "assumption_actions" in data
    assert data["assumption_actions"] == []

    app.dependency_overrides.clear()
