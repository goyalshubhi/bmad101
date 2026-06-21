import io
import pytest
import pandas as pd

from app.services.ingest.csv_adapter import CsvAdapter


@pytest.fixture
def adapter():
    return CsvAdapter()


def test_parse_valid_csv(adapter):
    csv_data = b"name,age,score\nAlice,30,95.5\nBob,25,87.2\n"
    df = adapter.parse(io.BytesIO(csv_data))
    assert len(df) == 2
    assert list(df.columns) == ["name", "age", "score"]


def test_parse_empty_csv(adapter):
    csv_data = b"name,age\n"
    df = adapter.parse(io.BytesIO(csv_data))
    assert len(df) == 0
    assert list(df.columns) == ["name", "age"]


def test_parse_csv_with_special_chars(adapter):
    csv_data = b"col 1,Col Two,COL_THREE\na,1,x\nb,2,y\n"
    df = adapter.parse(io.BytesIO(csv_data))
    assert len(df) == 2


def test_detect_schema_returns_dict(adapter):
    csv_data = b"name,age,active\nAlice,30,true\nBob,25,false\n"
    df = adapter.parse(io.BytesIO(csv_data))
    schema = adapter.detect_schema(df)
    assert isinstance(schema, dict)
    assert "name" in schema
    assert "age" in schema
