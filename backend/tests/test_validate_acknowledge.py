import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.database import get_db


def _make_mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


def _make_ingest_job(
    deck_id,
    status="CLEAN",
    schema_json=None,
    quality_report=None,
    validated_at=None,
):
    job = MagicMock()
    job.id = uuid.uuid4()
    job.deck_id = deck_id
    job.status = status
    job.schema_json = schema_json or {
        "columns": [
            {"name": "name", "type": "string", "nullable_pct": 0.0},
            {"name": "age", "type": "integer", "nullable_pct": 0.0},
        ],
        "row_count": 10,
    }
    job.quality_report = quality_report or {"status": status, "issues": []}
    job.validated_at = validated_at
    job.created_at = datetime(2026, 1, 1)
    return job


# ---------- Task 1: GET /decks/{deck_id}/ingest-status ----------


@pytest.mark.asyncio
async def test_get_ingest_status_clean():
    deck_id = uuid.uuid4()
    job = _make_ingest_job(deck_id, status="CLEAN")

    mock_session = _make_mock_session()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = job
    mock_session.execute.return_value = mock_result

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/decks/{deck_id}/ingest-status")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "CLEAN"
        assert data["ingest_job_id"] == str(job.id)
        assert "schema" in data
        assert "quality_report" in data
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_ingest_status_issues_blocking():
    deck_id = uuid.uuid4()
    quality_report = {
        "status": "ISSUES_BLOCKING",
        "issues": [
            {"severity": "high", "description": "Missing values in column 'age'", "count": 5, "sample_rows": [2, 7]},
        ],
    }
    job = _make_ingest_job(deck_id, status="ISSUES_BLOCKING", quality_report=quality_report)

    mock_session = _make_mock_session()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = job
    mock_session.execute.return_value = mock_result

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/decks/{deck_id}/ingest-status")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ISSUES_BLOCKING"
        assert len(data["quality_report"]["issues"]) == 1
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_ingest_status_no_job():
    deck_id = uuid.uuid4()

    mock_session = _make_mock_session()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/decks/{deck_id}/ingest-status")

        assert resp.status_code == 404
    finally:
        app.dependency_overrides.clear()


# ---------- Task 2: POST /decks/{deck_id}/validate-acknowledge ----------


@pytest.mark.asyncio
async def test_acknowledge_blocking_issues():
    deck_id = uuid.uuid4()
    user_id = uuid.uuid4()
    job = _make_ingest_job(deck_id, status="ISSUES_BLOCKING")

    mock_session = _make_mock_session()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = job
    mock_session.execute.return_value = mock_result

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                f"/api/v1/decks/{deck_id}/validate-acknowledge",
                json={"user_id": str(user_id)},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ISSUES_ACKNOWLEDGED"
        assert data["validated_at"] is not None
        assert job.status == "ISSUES_ACKNOWLEDGED"
        assert job.validated_at is not None

        # Verify audit_log was added
        mock_session.add.assert_called()
        audit_log_arg = mock_session.add.call_args[0][0]
        assert audit_log_arg.action == "data_validated"
        assert audit_log_arg.deck_id == deck_id
        assert audit_log_arg.user_id == user_id
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_acknowledge_clean_data():
    deck_id = uuid.uuid4()
    user_id = uuid.uuid4()
    job = _make_ingest_job(deck_id, status="CLEAN")

    mock_session = _make_mock_session()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = job
    mock_session.execute.return_value = mock_result

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                f"/api/v1/decks/{deck_id}/validate-acknowledge",
                json={"user_id": str(user_id)},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "CLEAN"
        assert data["validated_at"] is not None
        assert job.validated_at is not None

        mock_session.add.assert_called()
        audit_log_arg = mock_session.add.call_args[0][0]
        assert audit_log_arg.action == "data_validated"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_acknowledge_clean_already_validated_skips():
    """CLEAN job with validated_at already set returns existing data without new audit log."""
    deck_id = uuid.uuid4()
    user_id = uuid.uuid4()
    existing_validated_at = datetime(2026, 6, 1)
    job = _make_ingest_job(deck_id, status="CLEAN", validated_at=existing_validated_at)

    mock_session = _make_mock_session()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = job
    mock_session.execute.return_value = mock_result

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                f"/api/v1/decks/{deck_id}/validate-acknowledge",
                json={"user_id": str(user_id)},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "CLEAN"
        # No new audit log should be created
        mock_session.add.assert_not_called()
        mock_session.commit.assert_not_called()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_acknowledge_unexpected_status_rejected():
    """Jobs with unexpected status values are rejected with 400."""
    deck_id = uuid.uuid4()
    user_id = uuid.uuid4()
    job = _make_ingest_job(deck_id, status="PROCESSING")

    mock_session = _make_mock_session()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = job
    mock_session.execute.return_value = mock_result

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                f"/api/v1/decks/{deck_id}/validate-acknowledge",
                json={"user_id": str(user_id)},
            )

        assert resp.status_code == 400
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_acknowledge_already_acknowledged():
    deck_id = uuid.uuid4()
    user_id = uuid.uuid4()
    job = _make_ingest_job(
        deck_id,
        status="ISSUES_ACKNOWLEDGED",
        validated_at=datetime(2026, 1, 1),
    )

    mock_session = _make_mock_session()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = job
    mock_session.execute.return_value = mock_result

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                f"/api/v1/decks/{deck_id}/validate-acknowledge",
                json={"user_id": str(user_id)},
            )

        assert resp.status_code == 409
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_acknowledge_no_ingest_job():
    deck_id = uuid.uuid4()
    user_id = uuid.uuid4()

    mock_session = _make_mock_session()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                f"/api/v1/decks/{deck_id}/validate-acknowledge",
                json={"user_id": str(user_id)},
            )

        assert resp.status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_audit_log_has_correct_details():
    deck_id = uuid.uuid4()
    user_id = uuid.uuid4()
    quality_report = {
        "status": "ISSUES_BLOCKING",
        "issues": [
            {"severity": "high", "description": "Nulls", "count": 3, "sample_rows": [1]},
            {"severity": "medium", "description": "Outliers", "count": 2, "sample_rows": [5]},
        ],
    }
    job = _make_ingest_job(deck_id, status="ISSUES_BLOCKING", quality_report=quality_report)

    mock_session = _make_mock_session()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = job
    mock_session.execute.return_value = mock_result

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post(
                f"/api/v1/decks/{deck_id}/validate-acknowledge",
                json={"user_id": str(user_id)},
            )

        audit_log_arg = mock_session.add.call_args[0][0]
        details = audit_log_arg.details
        assert details["ingest_job_id"] == str(job.id)
        assert details["previous_status"] == "ISSUES_BLOCKING"
        assert details["acknowledged_issues_count"] == 2
    finally:
        app.dependency_overrides.clear()


# ---------- Task 5: Integration-style flow test ----------


@pytest.mark.asyncio
async def test_full_flow_get_status_then_acknowledge():
    """Integration-style test: GET ingest-status → POST validate-acknowledge → verify audit_log."""
    deck_id = uuid.uuid4()
    user_id = uuid.uuid4()
    quality_report = {
        "status": "ISSUES_BLOCKING",
        "issues": [
            {"severity": "high", "description": "Nulls in age", "count": 3, "sample_rows": [1, 4]},
        ],
    }
    job = _make_ingest_job(deck_id, status="ISSUES_BLOCKING", quality_report=quality_report)

    mock_session = _make_mock_session()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = job
    mock_session.execute.return_value = mock_result

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Step 1: GET ingest status — should show ISSUES_BLOCKING
            get_resp = await client.get(f"/api/v1/decks/{deck_id}/ingest-status")
            assert get_resp.status_code == 200
            status_data = get_resp.json()
            assert status_data["status"] == "ISSUES_BLOCKING"
            assert len(status_data["quality_report"]["issues"]) == 1

            # Step 2: POST acknowledge
            ack_resp = await client.post(
                f"/api/v1/decks/{deck_id}/validate-acknowledge",
                json={"user_id": str(user_id)},
            )
            assert ack_resp.status_code == 200
            ack_data = ack_resp.json()
            assert ack_data["status"] == "ISSUES_ACKNOWLEDGED"
            assert ack_data["validated_at"] is not None

            # Step 3: Verify job was mutated
            assert job.status == "ISSUES_ACKNOWLEDGED"
            assert job.validated_at is not None

            # Step 4: Verify audit_log entry was created
            audit_log_arg = mock_session.add.call_args[0][0]
            assert audit_log_arg.action == "data_validated"
            assert audit_log_arg.user_id == user_id
            assert audit_log_arg.details["previous_status"] == "ISSUES_BLOCKING"
            assert audit_log_arg.details["acknowledged_issues_count"] == 1
    finally:
        app.dependency_overrides.clear()
