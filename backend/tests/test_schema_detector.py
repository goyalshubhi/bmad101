import pandas as pd
import pytest

from app.services.ingest.schema_detector import detect_schema, _clean_column_name


def test_clean_column_name():
    assert _clean_column_name("  First Name  ") == "first_name"
    assert _clean_column_name("AGE") == "age"
    assert _clean_column_name("col 1") == "col_1"


def test_detect_numeric_columns():
    df = pd.DataFrame({"price": [10.5, 20.3, 30.0], "qty": [1, 2, 3]})
    schema = detect_schema(df)
    assert schema["price"]["type"] == "numeric"
    assert schema["qty"]["type"] == "numeric"


def test_detect_text_columns():
    df = pd.DataFrame({"name": ["Alice", "Bob", "Charlie"]})
    schema = detect_schema(df)
    assert schema["name"]["type"] == "text"


def test_detect_nullability():
    df = pd.DataFrame({"col": [1, None, 3, None]})
    schema = detect_schema(df)
    assert schema["col"]["nullability"] == 0.5


def test_detect_cardinality():
    df = pd.DataFrame({"col": ["a", "b", "c", "a", "b"]})
    schema = detect_schema(df)
    assert schema["col"]["cardinality"] == 3


def test_detect_datetime_column():
    df = pd.DataFrame({"date": ["2024-01-01", "2024-02-01", "2024-03-01"]})
    schema = detect_schema(df)
    assert schema["date"]["type"] == "datetime"
    assert "date_format" in schema["date"]


def test_schema_uses_sample_rows():
    df = pd.DataFrame({"val": list(range(2000))})
    schema = detect_schema(df)
    assert schema["val"]["cardinality"] <= 1000
