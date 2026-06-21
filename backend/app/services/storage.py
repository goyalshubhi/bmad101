import asyncio
import uuid
import boto3
from botocore.exceptions import ClientError

from app.core.config import settings


def _ensure_bucket(s3_client, bucket: str) -> None:
    try:
        s3_client.head_bucket(Bucket=bucket)
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code in ("404", "NoSuchBucket"):
            s3_client.create_bucket(Bucket=bucket)
        else:
            raise


def _upload_sync(file_data: bytes, filename: str) -> str:
    s3 = boto3.client(
        "s3",
        endpoint_url=f"http://{settings.MINIO_ENDPOINT}",
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
    )
    bucket = settings.MINIO_BUCKET
    _ensure_bucket(s3, bucket)

    file_key = f"{uuid.uuid4()}/{filename}"
    s3.put_object(Bucket=bucket, Key=file_key, Body=file_data)
    return f"s3://{bucket}/{file_key}"


async def upload_file(file_data: bytes, filename: str) -> str:
    return await asyncio.to_thread(_upload_sync, file_data, filename)


def _download_sync(object_key: str) -> bytes:
    s3 = boto3.client(
        "s3",
        endpoint_url=f"http://{settings.MINIO_ENDPOINT}",
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
    )
    bucket = settings.MINIO_BUCKET

    try:
        response = s3.get_object(Bucket=bucket, Key=object_key)
        return response["Body"].read()
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code in ("404", "NoSuchKey"):
            return None
        raise


def download_file(object_key: str) -> bytes | None:
    """Download a file from MinIO/S3 and return its bytes.

    Returns None if the object does not exist.
    """
    return _download_sync(object_key)
