import io
import json

import pytest

from app.services.ingest.json_adapter import JsonAdapter


@pytest.fixture
def adapter():
    return JsonAdapter()


def _make_json_file(data):
    raw = json.dumps(data).encode("utf-8")
    return io.BytesIO(raw)


def test_parse_flat_array_of_objects(adapter):
    data = [
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
    ]
    df = adapter.parse(_make_json_file(data))
    assert len(df) == 2
    assert list(df.columns) == ["name", "age"]


def test_parse_nested_dict(adapter):
    data = {"user": {"name": "Alice", "age": 30}, "meta": {"source": "api"}}
    df = adapter.parse(_make_json_file(data))
    assert len(df) == 1
    assert "user.name" in df.columns
    assert "user.age" in df.columns
    assert "meta.source" in df.columns


def test_parse_dict_with_list_value(adapter):
    data = {"results": [
        {"name": "Alice", "score": 95},
        {"name": "Bob", "score": 87},
    ]}
    df = adapter.parse(_make_json_file(data))
    assert len(df) == 2
    assert list(df.columns) == ["name", "score"]


def test_parse_empty_array(adapter):
    df = adapter.parse(_make_json_file([]))
    assert len(df) == 0


def test_parse_non_tabular_raises(adapter):
    with pytest.raises(ValueError, match="Unsupported JSON structure"):
        adapter.parse(_make_json_file([1, 2, 3]))


def test_detect_schema_returns_dict(adapter):
    data = [
        {"name": "Alice", "age": 30, "active": True},
        {"name": "Bob", "age": 25, "active": False},
    ]
    df = adapter.parse(_make_json_file(data))
    schema = adapter.detect_schema(df)
    assert isinstance(schema, dict)
    assert "name" in schema
    assert "age" in schema
