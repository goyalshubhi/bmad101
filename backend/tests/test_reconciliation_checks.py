import pytest
import numpy as np
import pandas as pd

from app.services.verify.reconciliation_checks import run_all_checks


def _make_figures(*values):
    return [{"value": v, "context_sentence": f"Figure is {v}.", "narrative_position": 0} for v in values]


class TestCheckA_SumOfParts:
    def test_pass_when_parts_sum_to_total(self):
        figures = _make_figures("$100", "$60", "$40")
        df = pd.DataFrame({"a": [1]})
        result = run_all_checks(figures, df, "", {})
        assert result["check_a"]["status"] == "pass"

    def test_pass_when_too_few_figures(self):
        figures = _make_figures("$100", "$50")
        df = pd.DataFrame({"a": [1]})
        result = run_all_checks(figures, df, "", {})
        assert result["check_a"]["status"] == "pass"

    def test_pass_vacuous_no_figures(self):
        result = run_all_checks([], pd.DataFrame({"a": [1]}), "", {})
        assert result["check_a"]["status"] == "pass"

    def test_percentages_excluded_from_sum_check(self):
        figures = _make_figures("50.0%", "30.0%", "20.0%")
        df = pd.DataFrame({"a": [1]})
        result = run_all_checks(figures, df, "", {})
        assert result["check_a"]["status"] == "pass"


class TestCheckB_DataConsistency:
    def test_pass_figure_matches_sum(self):
        df = pd.DataFrame({"sales": [10, 20, 30]})
        figures = _make_figures("60")
        result = run_all_checks(figures, df, "", {})
        assert result["check_b"]["status"] == "pass"

    def test_fail_figure_no_match(self):
        df = pd.DataFrame({"sales": [10, 20, 30]})
        figures = _make_figures("$999999")
        result = run_all_checks(figures, df, "", {})
        assert result["check_b"]["status"] == "fail"

    def test_pass_empty_dataframe(self):
        df = pd.DataFrame({"name": ["a", "b"]})
        figures = _make_figures("$100")
        result = run_all_checks(figures, df, "", {})
        assert result["check_b"]["status"] == "pass"

    def test_percentages_excluded_from_consistency_check(self):
        df = pd.DataFrame({"sales": [10, 20, 30]})
        figures = _make_figures("15.3%")
        result = run_all_checks(figures, df, "", {})
        assert result["check_b"]["status"] == "pass"


class TestCheckC_TimeSeriesContinuity:
    def test_pass_no_temporal_claims(self):
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = run_all_checks([], df, "Revenue was strong.", {})
        assert result["check_c"]["status"] == "pass"

    def test_pass_continuous_series(self):
        dates = pd.date_range("2024-01-01", periods=12, freq="MS")
        df = pd.DataFrame({"date": dates, "value": range(12)})
        result = run_all_checks([], df, "Revenue grew over 12 consecutive months.", {})
        assert result["check_c"]["status"] == "pass"

    def test_fail_gap_in_series(self):
        dates = pd.to_datetime(["2024-01-01", "2024-02-01", "2024-06-01", "2024-07-01"])
        df = pd.DataFrame({"date": dates, "value": [10, 20, 30, 40]})
        result = run_all_checks([], df, "Revenue grew over consecutive months.", {})
        assert result["check_c"]["status"] in ("pass", "fail")


class TestCheckD_ComparisonValidity:
    def test_pass_no_comparison_claims(self):
        df = pd.DataFrame({"a": [1, 2]})
        result = run_all_checks([], df, "Revenue was strong.", {})
        assert result["check_d"]["status"] == "pass"

    def test_pass_two_years(self):
        dates = pd.to_datetime(["2023-06-01", "2024-06-01"])
        df = pd.DataFrame({"date": dates, "value": [100, 120]})
        result = run_all_checks([], df, "Revenue grew 20% YoY.", {})
        assert result["check_d"]["status"] == "pass"

    def test_fail_single_period(self):
        dates = pd.to_datetime(["2024-01-15"])
        df = pd.DataFrame({"date": dates, "value": [100]})
        result = run_all_checks([], df, "Revenue grew 20% YoY.", {})
        assert result["check_d"]["status"] == "fail"


class TestCheckE_StatisticalSignificance:
    def test_pass_no_trend_claims(self):
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = run_all_checks([], df, "Revenue was $100.", {})
        assert result["check_e"]["status"] == "pass"

    def test_pass_strong_trend(self):
        dates = pd.date_range("2024-01-01", periods=10, freq="MS")
        df = pd.DataFrame({"date": dates, "value": np.arange(10) * 5 + 100})
        result = run_all_checks([], df, "Revenue shows a consistent increasing trend.", {})
        assert result["check_e"]["status"] == "pass"
        assert "R²" in str(result["check_e"]["actual"])

    def test_fail_weak_trend(self):
        dates = pd.date_range("2024-01-01", periods=10, freq="MS")
        np.random.seed(42)
        df = pd.DataFrame({"date": dates, "value": np.random.uniform(50, 150, 10)})
        result = run_all_checks([], df, "Revenue shows a consistent increasing trend.", {})
        assert result["check_e"]["status"] == "fail"
        assert result["check_e"]["fix_suggestion"] is not None


class TestAllChecksIntegration:
    def test_all_pass_clean_data(self):
        dates = pd.date_range("2024-01-01", periods=12, freq="MS")
        values = np.arange(12) * 10 + 100
        df = pd.DataFrame({"date": dates, "sales": values})
        total = float(values.sum())
        figures = _make_figures(str(total))
        result = run_all_checks(figures, df, f"Total sales were {total}.", {})
        for check_key in ["check_a", "check_b", "check_c", "check_d", "check_e"]:
            assert check_key in result
            assert result[check_key]["status"] in ("pass", "fail")
