from typing import BinaryIO

import pandas as pd

from app.services.ingest.base_adapter import BaseAdapter
from app.services.ingest.schema_detector import detect_schema


class ExcelAdapter(BaseAdapter):
    def parse(self, file: BinaryIO) -> pd.DataFrame:
        return pd.read_excel(file, engine="openpyxl", sheet_name=0)

    def detect_schema(self, df: pd.DataFrame) -> dict:
        return detect_schema(df)
