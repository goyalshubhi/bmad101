from unittest.mock import patch, MagicMock

import pytest

from app.services.storage import upload_file


@pytest.mark.asyncio
async def test_upload_file():
    with patch("app.services.storage.boto3") as mock_boto3:
        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3
        mock_s3.head_bucket.return_value = {}

        result = await upload_file(b"test data", "test.csv")

        assert result.startswith("s3://")
        assert "test.csv" in result
        mock_s3.put_object.assert_called_once()


@pytest.mark.asyncio
async def test_upload_creates_bucket_if_missing():
    from botocore.exceptions import ClientError

    with patch("app.services.storage.boto3") as mock_boto3:
        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3
        mock_s3.head_bucket.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadBucket"
        )

        result = await upload_file(b"test data", "test.csv")

        mock_s3.create_bucket.assert_called_once()
        assert result.startswith("s3://")
