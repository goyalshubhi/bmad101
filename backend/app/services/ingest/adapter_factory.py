from app.services.ingest.base_adapter import BaseAdapter
from app.services.ingest.csv_adapter import CsvAdapter
from app.services.ingest.excel_adapter import ExcelAdapter
from app.services.ingest.json_adapter import JsonAdapter

SUPPORTED_FORMATS = "CSV, XLSX, JSON"


def get_adapter(filename: str) -> BaseAdapter:
    name = filename.lower()
    if name.endswith(".csv"):
        return CsvAdapter()
    if name.endswith(".xlsx"):
        return ExcelAdapter()
    if name.endswith(".json"):
        return JsonAdapter()
    raise ValueError(f"Unsupported file format. Supported formats: {SUPPORTED_FORMATS}")
