import pandas as pd
import pytest

from app.services.ingest.quality_checker import run_quality_checks


def test_clean_data_returns_clean():
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    result = run_quality_checks(df)
    assert result["status"] == "CLEAN"
    assert len(result["quality_issues"]) == 0


def test_duplicate_detection():
    df = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
    result = run_quality_checks(df)
    dupe_issues = [i for i in result["quality_issues"] if "duplicate" in i["description"].lower()]
    assert len(dupe_issues) == 1


def test_type_consistency():
    df = pd.DataFrame({"mixed": ["hello", "123", "world", "456", "test"]})
    result = run_quality_checks(df)
    type_issues = [i for i in result["quality_issues"] if "mixed type" in i["description"].lower() or "Mixed" in i["description"]]
    assert len(type_issues) >= 1


def test_missing_data():
    df = pd.DataFrame({"col": [1, None, None, 4]})
    result = run_quality_checks(df)
    missing_issues = [i for i in result["quality_issues"] if "missing" in i["description"].lower() or "Missing" in i["description"]]
    assert len(missing_issues) == 1
    assert missing_issues[0]["count"] == 2


def test_cardinality_warning():
    df = pd.DataFrame({"col": list(range(1500))})
    result = run_quality_checks(df)
    card_issues = [i for i in result["quality_issues"] if "cardinality" in i["description"].lower()]
    assert len(card_issues) == 1


def test_high_severity_makes_blocking():
    df = pd.DataFrame({"col": [None] * 6 + [1, 2, 3, 4]})
    result = run_quality_checks(df)
    assert result["status"] == "ISSUES_BLOCKING"


def test_issues_have_required_fields():
    df = pd.DataFrame({"col": [1, None, 3]})
    result = run_quality_checks(df)
    for issue in result["quality_issues"]:
        assert "severity" in issue
        assert "description" in issue
        assert "count" in issue
        assert "sample_rows" in issue
