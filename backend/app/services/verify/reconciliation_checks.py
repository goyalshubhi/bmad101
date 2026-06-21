from __future__ import annotations

import re
from itertools import combinations

import numpy as np
import pandas as pd

from app.services.verify.numeric_parser import parse_numeric, is_percentage

_MAX_FIGURES_FOR_COMBINATORIAL = 15


def run_all_checks(
    figures: list[dict],
    df: pd.DataFrame,
    narrative_text: str,
    schema: dict,
) -> dict:
    return {
        "check_a": _check_sum_of_parts(figures),
        "check_b": _check_data_consistency(figures, df, schema),
        "check_c": _check_time_series_continuity(narrative_text, df),
        "check_d": _check_comparison_validity(narrative_text, df),
        "check_e": _check_statistical_significance(narrative_text, df),
    }


def _check_sum_of_parts(figures: list[dict]) -> dict:
    numeric_vals = []
    for fig in figures:
        if is_percentage(fig["value"]):
            continue
        val = parse_numeric(fig["value"])
        if val is not None and val > 0:
            numeric_vals.append(val)

    if len(numeric_vals) < 3:
        return {"status": "pass", "expected": None, "actual": None, "fix_suggestion": None}

    for i, candidate_total in enumerate(numeric_vals):
        others = numeric_vals[:i] + numeric_vals[i + 1:]
        parts_sum = sum(others)
        if parts_sum == 0:
            continue
        variance = abs(candidate_total - parts_sum) / parts_sum
        if variance <= 0.01:
            return {"status": "pass", "expected": candidate_total, "actual": parts_sum, "fix_suggestion": None}

    if len(numeric_vals) > _MAX_FIGURES_FOR_COMBINATORIAL:
        return {"status": "pass", "expected": None, "actual": None, "fix_suggestion": None}

    for i, candidate_total in enumerate(numeric_vals):
        others = numeric_vals[:i] + numeric_vals[i + 1:]
        for size in range(2, len(others) + 1):
            for combo in combinations(others, size):
                parts_sum = sum(combo)
                if parts_sum == 0:
                    continue
                variance = abs(candidate_total - parts_sum) / parts_sum
                if variance <= 0.01:
                    return {"status": "pass", "expected": candidate_total, "actual": parts_sum, "fix_suggestion": None}
                if 0.01 < variance <= 0.10:
                    return {
                        "status": "fail",
                        "expected": candidate_total,
                        "actual": parts_sum,
                        "fix_suggestion": "Recalculate total as sum of components",
                    }

    return {"status": "pass", "expected": None, "actual": None, "fix_suggestion": None}


def _check_data_consistency(figures: list[dict], df: pd.DataFrame, schema: dict) -> dict:
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols or not figures:
        return {"status": "pass", "expected": None, "actual": None, "fix_suggestion": None}

    aggregations: dict[str, list[tuple[str, float]]] = {}
    for col in numeric_cols:
        col_vals = df[col].dropna()
        if col_vals.empty:
            continue
        aggregations[col] = [
            ("SUM", col_vals.sum()),
            ("AVG", col_vals.mean()),
            ("COUNT", float(len(col_vals))),
            ("MIN", col_vals.min()),
            ("MAX", col_vals.max()),
        ]

    first_failure = None
    for fig in figures:
        if is_percentage(fig["value"]):
            continue
        fig_val = parse_numeric(fig["value"])
        if fig_val is None:
            continue

        matched = False
        for col, aggs in aggregations.items():
            for agg_name, agg_val in aggs:
                if agg_val == 0 and fig_val == 0:
                    matched = True
                    break
                if agg_val != 0:
                    variance = abs(fig_val - agg_val) / abs(agg_val)
                    if variance <= 0.001:
                        matched = True
                        break
            if matched:
                break

        if not matched and fig_val != 0 and first_failure is None:
            null_count = 0
            for col in numeric_cols:
                null_count += int(df[col].isna().sum())
            suggestion = None
            if null_count > 0:
                suggestion = f"Exclude {null_count} rows with null/invalid entries"
            first_failure = {
                "status": "fail",
                "expected": fig["value"],
                "actual": "no matching aggregation found",
                "fix_suggestion": suggestion,
            }

    if first_failure is not None:
        return first_failure

    return {"status": "pass", "expected": None, "actual": None, "fix_suggestion": None}


_TEMPORAL_KEYWORDS = re.compile(
    r"\b(quarters?|months?|years?|consecutive|continuous|growing\s+\d+\s+periods?)\b",
    re.IGNORECASE,
)


def _get_datetime_col(df: pd.DataFrame) -> str | None:
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            return col
    return None


def _check_time_series_continuity(narrative_text: str, df: pd.DataFrame) -> dict:
    if not _TEMPORAL_KEYWORDS.search(narrative_text):
        return {"status": "pass", "expected": None, "actual": None, "fix_suggestion": None}

    dt_col = _get_datetime_col(df)
    if dt_col is None:
        return {"status": "pass", "expected": None, "actual": None, "fix_suggestion": None}

    try:
        dates = df[dt_col].dropna().sort_values()
    except TypeError:
        return {"status": "pass", "expected": None, "actual": None, "fix_suggestion": None}

    if len(dates) < 2:
        return {"status": "pass", "expected": None, "actual": None, "fix_suggestion": None}

    freq = pd.infer_freq(dates)
    if freq is not None:
        return {"status": "pass", "expected": "continuous series", "actual": "continuous series", "fix_suggestion": None}

    min_diff = dates.diff().dropna().min()
    max_diff = dates.diff().dropna().max()
    if max_diff > min_diff * 3:
        return {
            "status": "fail",
            "expected": "continuous series",
            "actual": f"gap detected (max interval {max_diff})",
            "fix_suggestion": "Data has gaps in the time series. Consider noting data limitations.",
        }

    return {"status": "pass", "expected": "continuous series", "actual": "continuous series", "fix_suggestion": None}


_COMPARISON_KEYWORDS = re.compile(
    r"\b(YoY|MoM|year-over-year|month-over-month|compared\s+to|vs\.?|versus)\b",
    re.IGNORECASE,
)


def _check_comparison_validity(narrative_text: str, df: pd.DataFrame) -> dict:
    if not _COMPARISON_KEYWORDS.search(narrative_text):
        return {"status": "pass", "expected": None, "actual": None, "fix_suggestion": None}

    dt_col = _get_datetime_col(df)
    if dt_col is None:
        return {"status": "pass", "expected": None, "actual": None, "fix_suggestion": None}

    try:
        dates = df[dt_col].dropna().sort_values()
    except TypeError:
        return {"status": "pass", "expected": None, "actual": None, "fix_suggestion": None}

    if len(dates) < 2:
        return {
            "status": "fail",
            "expected": "data in both comparison periods",
            "actual": "insufficient data points",
            "fix_suggestion": "Insufficient data for comparison — need at least two periods",
        }

    unique_years = dates.dt.year.unique()
    if len(unique_years) >= 2:
        return {"status": "pass", "expected": "data in both periods", "actual": "data in both periods", "fix_suggestion": None}

    unique_months = dates.dt.to_period("M").unique()
    if len(unique_months) >= 2:
        return {"status": "pass", "expected": "data in both periods", "actual": "data in both periods", "fix_suggestion": None}

    return {
        "status": "fail",
        "expected": "data in both comparison periods",
        "actual": "data in single period only",
        "fix_suggestion": "Period has no comparable data — comparison invalid",
    }


_TREND_KEYWORDS = re.compile(
    r"\b(trend|growing|declining|increasing|decreasing|consistent)\b",
    re.IGNORECASE,
)


def _check_statistical_significance(narrative_text: str, df: pd.DataFrame) -> dict:
    if not _TREND_KEYWORDS.search(narrative_text):
        return {"status": "pass", "expected": None, "actual": None, "fix_suggestion": None}

    dt_col = _get_datetime_col(df)
    if dt_col is None:
        return {"status": "pass", "expected": None, "actual": None, "fix_suggestion": None}

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        return {"status": "pass", "expected": None, "actual": None, "fix_suggestion": None}

    target_col = numeric_cols[0]
    clean = df[[dt_col, target_col]].dropna()
    if len(clean) < 3:
        return {"status": "pass", "expected": None, "actual": None, "fix_suggestion": None}

    x = np.arange(len(clean), dtype=float)
    y = clean[target_col].values.astype(float)

    y_mean = np.mean(y)
    if y_mean == 0:
        return {"status": "pass", "expected": None, "actual": None, "fix_suggestion": None}

    try:
        coeffs = np.polyfit(x, y, 1)
    except (np.linalg.LinAlgError, ValueError):
        return {"status": "pass", "expected": None, "actual": None, "fix_suggestion": None}

    y_pred = np.polyval(coeffs, x)

    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y_mean) ** 2)
    if ss_tot == 0:
        return {"status": "pass", "expected": None, "actual": None, "fix_suggestion": None}

    r_squared = 1 - ss_res / ss_tot

    if r_squared > 0.6:
        return {
            "status": "pass",
            "expected": "R² > 0.6",
            "actual": f"R²={r_squared:.3f}",
            "fix_suggestion": None,
        }

    return {
        "status": "fail",
        "expected": "R² > 0.6",
        "actual": f"R²={r_squared:.3f}",
        "fix_suggestion": f"R²={r_squared:.3f} — trend claim is statistically weak. Consider softening language.",
    }
