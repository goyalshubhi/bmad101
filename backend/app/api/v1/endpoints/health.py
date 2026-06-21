import asyncio

from fastapi import APIRouter
from sqlalchemy import text
import boto3

from app.core.database import engine
from app.core.redis import redis_client
from app.core.config import settings

router = APIRouter()


def _check_minio() -> None:
    s3 = boto3.client(
        "s3",
        endpoint_url=f"http://{settings.MINIO_ENDPOINT}",
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
    )
    s3.list_buckets()


@router.get("/health")
async def health_check():
    services = {}

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        services["postgres"] = "up"
    except Exception:
        services["postgres"] = "down"

    try:
        await redis_client.ping()
        services["redis"] = "up"
    except Exception:
        services["redis"] = "down"

    try:
        await asyncio.to_thread(_check_minio)
        services["minio"] = "up"
    except Exception:
        services["minio"] = "down"

    status = "ok" if all(v == "up" for v in services.values()) else "degraded"

    return {"status": status, "services": services}
