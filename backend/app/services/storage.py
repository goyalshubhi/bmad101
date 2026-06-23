import asyncio
import uuid
from pathlib import Path

from app.core.config import settings

UPLOADS_DIR = Path(settings.UPLOADS_DIR)


def _ensure_dir() -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def _upload_sync(file_data: bytes, filename: str) -> str:
    _ensure_dir()
    file_key = f"{uuid.uuid4()}/{filename}"
    dest = UPLOADS_DIR / file_key
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(file_data)
    return f"local://{file_key}"


async def upload_file(file_data: bytes, filename: str) -> str:
    return await asyncio.to_thread(_upload_sync, file_data, filename)


def download_file(object_key: str) -> bytes | None:
    if object_key.startswith("local://"):
        object_key = object_key[len("local://"):]
    elif object_key.startswith("s3://"):
        parts = object_key[5:].split("/", 1)
        object_key = parts[1] if len(parts) > 1 else parts[0]

    path = UPLOADS_DIR / object_key
    if not path.exists():
        return None
    return path.read_bytes()
