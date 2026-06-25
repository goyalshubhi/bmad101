import asyncio
import uuid
from pathlib import Path, PurePosixPath

from app.core.config import settings

UPLOADS_DIR = Path(settings.UPLOADS_DIR).resolve()


def _ensure_dir() -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def _sanitize_filename(filename: str) -> str:
    safe = PurePosixPath(filename).name
    safe = safe.lstrip(".")
    if not safe:
        safe = "upload"
    return safe


def _upload_sync(file_data: bytes, filename: str, *, file_key: str | None = None) -> str:
    _ensure_dir()
    if file_key is None:
        safe_name = _sanitize_filename(filename)
        file_key = f"{uuid.uuid4()}/{safe_name}"
    dest = UPLOADS_DIR / file_key
    if not dest.resolve().is_relative_to(UPLOADS_DIR):
        raise ValueError("Path traversal detected in upload filename")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(file_data)
    return f"local://{file_key}"


async def upload_file(file_data: bytes, filename: str, *, file_key: str | None = None) -> str:
    return await asyncio.to_thread(_upload_sync, file_data, filename, file_key=file_key)


def download_file(object_key: str) -> bytes | None:
    if object_key.startswith("local://"):
        object_key = object_key[len("local://"):]
    elif object_key.startswith("s3://"):
        parts = object_key[5:].split("/", 1)
        object_key = parts[1] if len(parts) > 1 else parts[0]

    path = (UPLOADS_DIR / object_key).resolve()
    if not path.is_relative_to(UPLOADS_DIR):
        return None
    if not path.exists():
        return None
    return path.read_bytes()
