import io

import pytest
from openpyxl import Workbook

from app.services.ingest.excel_adapter import ExcelAdapter


@pytest.fixture
def adapter():
    return ExcelAdapter()


def _make_xlsx(rows, sheet_name="Sheet1", extra_sheets=None):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name
    for row in rows:
        ws.append(row)
    if extra_sheets:
        for name, data in extra_sheets.items():
            ws2 = wb.create_sheet(title=name)
            for row in data:
                ws2.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def test_parse_valid_xlsx(adapter):
    xlsx = _make_xlsx([
        ["name", "age", "score"],
        ["Alice", 30, 95.5],
        ["Bob", 25, 87.2],
    ])
    df = adapter.parse(xlsx)
    assert len(df) == 2
    assert list(df.columns) == ["name", "age", "score"]


def test_parse_empty_xlsx(adapter):
    xlsx = _make_xlsx([["name", "age"]])
    df = adapter.parse(xlsx)
    assert len(df) == 0
    assert list(df.columns) == ["name", "age"]


def test_parse_multi_sheet_uses_first(adapter):
    xlsx = _make_xlsx(
        [["col_a"], ["first_sheet_val"]],
        sheet_name="Primary",
        extra_sheets={"Secondary": [["col_b"], ["second_sheet_val"]]},
    )
    df = adapter.parse(xlsx)
    assert list(df.columns) == ["col_a"]
    assert df.iloc[0]["col_a"] == "first_sheet_val"


def test_detect_schema_returns_dict(adapter):
    xlsx = _make_xlsx([
        ["name", "age", "active"],
        ["Alice", 30, True],
        ["Bob", 25, False],
    ])
    df = adapter.parse(xlsx)
    schema = adapter.detect_schema(df)
    assert isinstance(schema, dict)
    assert "name" in schema
    assert "age" in schema
