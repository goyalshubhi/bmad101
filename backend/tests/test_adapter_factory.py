import pytest

from app.services.ingest.adapter_factory import get_adapter
from app.services.ingest.csv_adapter import CsvAdapter
from app.services.ingest.excel_adapter import ExcelAdapter
from app.services.ingest.json_adapter import JsonAdapter


def test_csv_adapter():
    adapter = get_adapter("data.csv")
    assert isinstance(adapter, CsvAdapter)


def test_xlsx_adapter():
    adapter = get_adapter("data.xlsx")
    assert isinstance(adapter, ExcelAdapter)


def test_xls_unsupported():
    with pytest.raises(ValueError, match="Unsupported file format"):
        get_adapter("report.xls")


def test_json_adapter():
    adapter = get_adapter("data.json")
    assert isinstance(adapter, JsonAdapter)


def test_unsupported_pdf():
    with pytest.raises(ValueError, match="Unsupported file format"):
        get_adapter("data.pdf")


def test_unsupported_txt():
    with pytest.raises(ValueError, match="Unsupported file format"):
        get_adapter("data.txt")
