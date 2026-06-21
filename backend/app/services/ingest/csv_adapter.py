from typing import BinaryIO

import pandas as pd

from app.services.ingest.base_adapter import BaseAdapter
from app.services.ingest.schema_detector import detect_schema


class CsvAdapter(BaseAdapter):
    def parse(self, file: BinaryIO) -> pd.DataFrame:
        return pd.read_csv(file)

    def detect_schema(self, df: pd.DataFrame) -> dict:
        return detect_schema(df)
