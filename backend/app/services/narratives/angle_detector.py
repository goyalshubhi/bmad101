"""Statistical angle detection for narrative generation.

Analyzes a pandas DataFrame to detect data-driven "angles" -- narrative
themes that can be turned into presentation stories.  Uses numpy for
linear regression (polyfit) and basic statistics.  No scipy dependency.
"""

from __future__ import annotations

import uuid
from typing import Any

import numpy as np
import pandas as pd


def detect_angles(df: pd.DataFrame, schema: dict) -> list[dict]:
    """Detect narrative angles from data and schema.

    Args:
        df: The ingested dataset as a DataFrame.
        schema: Schema dict describing column types.  Expected keys:
            ``columns`` (list of dicts with ``name`` and ``type``).

    Returns:
        A list of angle dicts, each with:
          - id (str UUID)
          - type (str)  -- e.g. "trend", "disruption", "comparison", "outlier", "composition"
          - title (str) -- human-readable angle title
          - description (str)
          - strength (float 0-1) -- statistical confidence
          - evidence (dict) -- supporting stats
          - columns (list[str]) -- columns involved
    """
    angles: list[dict] = []

    # Use schema to classify columns, falling back to pandas dtype detection
    numeric_cols = _get_columns_by_type(df, schema, "numeric")
    datetime_cols = _get_columns_by_type(df, schema, "datetime")
    text_cols = _get_columns_by_type(df, schema, "text")

    # Angle 1: Trend detection (linear regression on numeric cols with datetime)
    if datetime_cols and numeric_cols:
        trend_angles = _detect_trends(df, datetime_cols[0], numeric_cols)
        angles.extend(trend_angles)

    # Angle 2: Disruption detection (volatility spikes)
    if numeric_cols:
        disruption_angles = _detect_disruptions(df, numeric_cols)
        angles.extend(disruption_angles)

    # Angle 3: Comparison -- pairwise correlation between numeric columns
    if len(numeric_cols) >= 2:
        comparison_angles = _detect_comparisons(df, numeric_cols)
        angles.extend(comparison_angles)

    # Angle 4: Outlier detection using z-scores
    if numeric_cols:
        outlier_angles = _detect_outliers(df, numeric_cols)
        angles.extend(outlier_angles)

    # Angle 5: Composition -- percentage breakdown
    if text_cols and numeric_cols:
        composition_angles = _detect_compositions(df, text_cols, numeric_cols)
        angles.extend(composition_angles)

    # Sort by strength descending, cap at 3 angles
    angles.sort(key=lambda a: a["strength"], reverse=True)
    return angles[:3]


def _get_columns_by_type(df: pd.DataFrame, schema: dict, col_type: str) -> list[str]:
    """Get column names by type using schema, falling back to pandas dtype."""
    schema_cols = schema.get("columns", [])

    if schema_cols:
        type_map = {
            "numeric": {"numeric", "integer", "float", "number", "decimal"},
            "datetime": {"datetime", "date", "timestamp", "time"},
            "text": {"text", "string", "categorical", "category", "object"},
        }
        target_types = type_map.get(col_type, set())
        matched = [
            c["name"] for c in schema_cols
            if c.get("type", "").lower() in target_types and c["name"] in df.columns
        ]
        if matched:
            return matched

    # Fallback to pandas dtype detection
    if col_type == "numeric":
        return df.select_dtypes(include="number").columns.tolist()
    elif col_type == "datetime":
        return df.select_dtypes(include="datetime").columns.tolist()
    elif col_type == "text":
        return df.select_dtypes(include="object").columns.tolist()
    return []


def _detect_trends(
    df: pd.DataFrame,
    time_col: str,
    numeric_cols: list[str],
) -> list[dict]:
    """Detect linear trends in numeric columns over time."""
    angles: list[dict] = []

    df_sorted = df.sort_values(time_col).reset_index(drop=True)
    x = np.arange(len(df_sorted), dtype=float)

    if len(x) < 3:
        return angles

    for col in numeric_cols[:3]:
        values = pd.to_numeric(df_sorted[col], errors="coerce").dropna()
        if len(values) < 3:
            continue

        x_valid = np.arange(len(values), dtype=float)
        coeffs = np.polyfit(x_valid, values.values, 1)
        slope = coeffs[0]

        predicted = np.polyval(coeffs, x_valid)
        ss_res = np.sum((values.values - predicted) ** 2)
        ss_tot = np.sum((values.values - np.mean(values.values)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        if abs(r_squared) < 0.1:
            continue

        direction = "upward" if slope > 0 else "downward"
        pct_change = (slope * len(values)) / abs(np.mean(values.values)) * 100 if np.mean(values.values) != 0 else 0

        strength = min(abs(r_squared), 1.0)

        angles.append({
            "id": str(uuid.uuid4()),
            "type": "trend",
            "title": f"{col} shows {direction} trend",
            "description": f"{col} has a {direction} trend over the time period, "
                           f"changing approximately {abs(pct_change):.1f}% overall.",
            "strength": round(strength, 3),
            "evidence": {
                "slope": round(float(slope), 4),
                "r_squared": round(float(r_squared), 4),
                "direction": direction,
                "pct_change": round(float(pct_change), 1),
            },
            "columns": [time_col, col],
        })

    return angles


def _detect_disruptions(
    df: pd.DataFrame,
    numeric_cols: list[str],
) -> list[dict]:
    """Detect disruption patterns via rolling volatility spikes.

    For each numeric column, compute rolling std deviation with
    window = max(3, len//10).  If latest window std > 2x overall std,
    flag as disruption.
    """
    angles: list[dict] = []

    for col in numeric_cols[:3]:
        values = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(values) < 6:
            continue

        window = max(3, len(values) // 10)
        overall_std = float(np.std(values))
        if overall_std == 0:
            continue

        rolling_std = values.rolling(window=window).std().dropna()
        if rolling_std.empty:
            continue

        latest_std = float(rolling_std.iloc[-1])
        volatility_ratio = latest_std / overall_std

        if volatility_ratio <= 2.0:
            continue

        strength = min(volatility_ratio / 5.0, 1.0)

        angles.append({
            "id": str(uuid.uuid4()),
            "type": "disruption",
            "title": f"Disruption detected in {col}",
            "description": (
                f"{col} shows a volatility spike in the most recent window. "
                f"Rolling std ({latest_std:.2f}) is {volatility_ratio:.1f}x "
                f"the overall std ({overall_std:.2f}), suggesting a disruption."
            ),
            "strength": round(strength, 3),
            "evidence": {
                "rolling_std": round(latest_std, 4),
                "overall_std": round(overall_std, 4),
                "volatility_ratio": round(volatility_ratio, 2),
                "window_size": window,
            },
            "columns": [col],
        })

    return angles


def _detect_comparisons(
    df: pd.DataFrame,
    numeric_cols: list[str],
) -> list[dict]:
    """Detect pairwise correlations between numeric columns.

    Flag pairs with correlation > 0.7 or < -0.3.
    """
    angles: list[dict] = []
    seen_pairs: set[tuple[str, str]] = set()

    for i, col_a in enumerate(numeric_cols):
        for col_b in numeric_cols[i + 1:]:
            pair_key = (col_a, col_b)
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            vals_a = pd.to_numeric(df[col_a], errors="coerce")
            vals_b = pd.to_numeric(df[col_b], errors="coerce")
            valid = vals_a.notna() & vals_b.notna()

            if valid.sum() < 5:
                continue

            corr = float(np.corrcoef(vals_a[valid], vals_b[valid])[0, 1])

            if np.isnan(corr):
                continue

            if corr > 0.7:
                direction = "positive"
            elif corr < -0.3:
                direction = "negative"
            else:
                continue

            strength = min(abs(corr), 1.0)

            angles.append({
                "id": str(uuid.uuid4()),
                "type": "comparison",
                "title": f"{direction.capitalize()} correlation: {col_a} vs {col_b}",
                "description": (
                    f"{col_a} and {col_b} show a {direction} correlation "
                    f"of {corr:.2f}, suggesting a meaningful relationship "
                    f"between these variables."
                ),
                "strength": round(strength, 3),
                "evidence": {
                    "correlation": round(corr, 4),
                    "direction": direction,
                    "column_a": col_a,
                    "column_b": col_b,
                    "sample_size": int(valid.sum()),
                },
                "columns": [col_a, col_b],
            })

    return angles


def _detect_outliers(
    df: pd.DataFrame,
    numeric_cols: list[str],
) -> list[dict]:
    """Detect outliers using z-score method with 3-sigma threshold."""
    angles: list[dict] = []

    for col in numeric_cols[:3]:
        values = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(values) < 5:
            continue

        mean = float(np.mean(values))
        std = float(np.std(values))

        if std == 0:
            continue

        z_scores = np.abs((values - mean) / std)
        outlier_count = int(np.sum(z_scores > 3.0))

        if outlier_count == 0:
            continue

        outlier_pct = outlier_count / len(values) * 100
        strength = min(outlier_pct / 20, 1.0)

        angles.append({
            "id": str(uuid.uuid4()),
            "type": "anomaly",
            "title": f"Outliers detected in {col}",
            "description": f"{outlier_count} outlier(s) found in {col} ({outlier_pct:.1f}% of values), "
                           f"deviating more than 3 standard deviations from the mean of {mean:.2f}.",
            "strength": round(strength, 3),
            "evidence": {
                "outlier_count": outlier_count,
                "outlier_pct": round(outlier_pct, 1),
                "mean": round(mean, 2),
                "std": round(std, 2),
                "threshold": 3.0,
            },
            "columns": [col],
        })

    return angles


def _detect_compositions(
    df: pd.DataFrame,
    text_cols: list[str],
    numeric_cols: list[str],
) -> list[dict]:
    """Detect composition/distribution patterns."""
    angles: list[dict] = []

    cat_col = text_cols[0]
    num_col = numeric_cols[0]

    grouped = df.groupby(cat_col)[num_col].sum()
    if len(grouped) < 2:
        return angles

    total = grouped.sum()
    if total == 0:
        return angles

    shares = (grouped / total * 100).sort_values(ascending=False)
    top_share = shares.iloc[0]

    concentration = top_share / 100
    strength = min(concentration, 1.0)

    if strength < 0.2:
        return angles

    top_3 = shares.head(3)
    top_3_labels = [f"{name} ({val:.1f}%)" for name, val in top_3.items()]

    angles.append({
        "id": str(uuid.uuid4()),
        "type": "composition",
        "title": f"{num_col} breakdown by {cat_col}",
        "description": f"Distribution of {num_col} across {cat_col}: "
                       f"{', '.join(top_3_labels)}.",
        "strength": round(strength, 3),
        "evidence": {
            "top_category": str(shares.index[0]),
            "top_share_pct": round(float(top_share), 1),
            "num_categories": len(grouped),
            "top_3": {str(k): round(float(v), 1) for k, v in top_3.items()},
        },
        "columns": [cat_col, num_col],
    })

    return angles
