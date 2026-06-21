"""Load DataFrame from MinIO/S3 storage for narrative generation.

Reads the ingested CSV file from object storage using the same pattern
as the ingest pipeline.  The data is loaded into a pandas DataFrame
for statistical analysis.
"""

from __future__ import annotations

import io

import pandas as pd

from app.services.storage import download_file


def load_dataframe(object_key: str) -> pd.DataFrame:
    """Download a CSV file from object storage and return a DataFrame.

    This is a synchronous function — callers should wrap it in
    ``asyncio.to_thread()`` when called from async endpoints.

    Args:
        object_key: The S3/MinIO object key (or full ``s3://bucket/key`` URL)
            for the ingested file.

    Returns:
        A pandas DataFrame parsed from the CSV.

    Raises:
        FileNotFoundError: If the object does not exist in storage.
        ValueError: If the file cannot be parsed as CSV.
    """
    # Strip s3://bucket/ prefix if present
    key = object_key
    if key.startswith("s3://"):
        # s3://bucket/actual/key -> actual/key
        parts = key[5:].split("/", 1)
        key = parts[1] if len(parts) > 1 else parts[0]

    file_bytes = download_file(key)
    if file_bytes is None:
        raise FileNotFoundError(f"Object not found in storage: {object_key}")

    try:
        df = pd.read_csv(io.BytesIO(file_bytes))
    except Exception as e:
        raise ValueError(f"Failed to parse CSV from storage: {e}") from e

    # Auto-detect datetime columns and convert
    for col in df.columns:
        if df[col].dtype == "object":
            try:
                df[col] = pd.to_datetime(df[col], infer_datetime_format=True)
            except (ValueError, TypeError):
                pass

    return df
