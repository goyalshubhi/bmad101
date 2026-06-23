import pytest

from app.services.storage import upload_file, download_file


@pytest.mark.asyncio
async def test_upload_file(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.storage.UPLOADS_DIR", tmp_path)

    result = await upload_file(b"test data", "test.csv")

    assert result.startswith("local://")
    assert "test.csv" in result


@pytest.mark.asyncio
async def test_upload_and_download_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.storage.UPLOADS_DIR", tmp_path)

    url = await upload_file(b"hello world", "data.csv")
    data = download_file(url)

    assert data == b"hello world"


def test_download_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.storage.UPLOADS_DIR", tmp_path)

    result = download_file("local://nonexistent/file.csv")
    assert result is None
