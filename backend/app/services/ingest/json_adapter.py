import json
from typing import BinaryIO

import pandas as pd

from app.services.ingest.base_adapter import BaseAdapter
from app.services.ingest.schema_detector import detect_schema


class JsonAdapter(BaseAdapter):
    def parse(self, file: BinaryIO) -> pd.DataFrame:
        raw = file.read()
        text = raw.decode("utf-8-sig")
        data = json.loads(text)

        if isinstance(data, list):
            if not data:
                return pd.DataFrame()
            if isinstance(data[0], dict):
                return pd.DataFrame(data)
            raise ValueError("Unsupported JSON structure: list items must be objects")

        if isinstance(data, dict):
            keys = list(data.keys())
            if len(keys) == 1 and isinstance(data[keys[0]], list):
                inner = data[keys[0]]
                if not inner:
                    return pd.DataFrame()
                if not isinstance(inner[0], dict):
                    raise ValueError("Unsupported JSON structure: list items must be objects")
                return pd.DataFrame(inner)
            return pd.json_normalize(data)

        raise ValueError("Unsupported JSON structure: expected array or object")

    def detect_schema(self, df: pd.DataFrame) -> dict:
        return detect_schema(df)
