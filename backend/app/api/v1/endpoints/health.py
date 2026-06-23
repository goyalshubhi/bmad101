import asyncio

from fastapi import APIRouter
from sqlalchemy import text

from app.core.database import engine
from app.core.redis import get_redis
from app.core.config import settings

router = APIRouter()


def _check_storage() -> None:
    from pathlib import Path
    uploads = Path(settings.UPLOADS_DIR)
    uploads.mkdir(parents=True, exist_ok=True)
    if not uploads.is_dir():
        raise RuntimeError("Uploads directory is not accessible")


@router.get("/health")
async def health_check():
    services = {}

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        services["database"] = "up"
    except Exception:
        services["database"] = "down"

    try:
        redis = await get_redis()
        await redis.ping()
        services["redis"] = "up"
    except Exception:
        services["redis"] = "unavailable (optional)"

    try:
        await asyncio.to_thread(_check_storage)
        services["storage"] = "up (local filesystem)"
    except Exception:
        services["storage"] = "down"

    required_up = services.get("database") == "up"
    status = "ok" if required_up else "degraded"

    return {"status": status, "services": services}
