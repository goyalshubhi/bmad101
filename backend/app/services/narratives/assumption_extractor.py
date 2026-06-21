"""Assumption extractor for narrative generation.

Flags assumptions made during angle detection and narrative generation.
Uses three flag types per the spec:
  - EXPLICIT  (confidence=1.0)  -- direct data facts
  - PATTERN   (confidence=0.75) -- statistical patterns from angle detection
  - INFERRED  (confidence=0.40) -- contextual inferences not directly in data

SPECULATIVE assumptions (confidence=0.0) are filtered out and never included.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def extract_assumptions(
    df: pd.DataFrame,
    angles: list[dict],
    narratives: list[dict],
    parsed_answers: list[dict],
) -> list[dict]:
    """Extract assumptions from the generated narratives and data analysis.

    Args:
        df: The ingested DataFrame.
        angles: Detected angles from angle_detector.
        narratives: Generated narratives from template_engine.
        parsed_answers: Parsed answers from the question session.

    Returns:
        List of assumption dicts, each with:
          - text (str) -- human-readable assumption
          - flag_type (str) -- EXPLICIT | PATTERN | INFERRED
          - confidence (float)
          - source_reference (str)
    """
    assumptions: list[dict] = []

    # 1. EXPLICIT assumptions -- direct data facts
    assumptions.extend(_explicit_assumptions(df, angles))

    # 2. PATTERN assumptions -- statistical patterns from angle detection
    assumptions.extend(_pattern_assumptions(angles))

    # 3. INFERRED assumptions -- contextual inferences
    assumptions.extend(_inferred_assumptions(df, angles, parsed_answers))

    return assumptions


def _explicit_assumptions(df: pd.DataFrame, angles: list[dict]) -> list[dict]:
    """EXPLICIT: direct data facts (values that exist in the data)."""
    assumptions: list[dict] = []

    # Dataset shape fact
    total_cells = df.shape[0] * df.shape[1]
    if total_cells > 0:
        missing_count = int(df.isnull().sum().sum())
        if missing_count > 0:
            missing_pct = missing_count / total_cells * 100
            assumptions.append({
                "text": (
                    f"Dataset contains {missing_pct:.1f}% missing values "
                    f"({missing_count} cells). Missing values were excluded "
                    f"from statistical calculations."
                ),
                "flag_type": "EXPLICIT",
                "confidence": 1.0,
                "source_reference": "data_loader: null-cell count",
            })

    # Row count fact
    assumptions.append({
        "text": f"Analysis is based on {len(df)} rows and {len(df.columns)} columns.",
        "flag_type": "EXPLICIT",
        "confidence": 1.0,
        "source_reference": "data_loader: dataset dimensions",
    })

    # Column value ranges used in angles
    for angle in angles:
        for col in angle.get("columns", []):
            if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                col_min = df[col].min()
                col_max = df[col].max()
                if pd.notna(col_min) and pd.notna(col_max):
                    assumptions.append({
                        "text": (
                            f"Column '{col}' ranges from {col_min:.2f} to {col_max:.2f} "
                            f"in the dataset."
                        ),
                        "flag_type": "EXPLICIT",
                        "confidence": 1.0,
                        "source_reference": f"data_loader: {col} value range",
                    })

    return assumptions


def _pattern_assumptions(angles: list[dict]) -> list[dict]:
    """PATTERN: statistical patterns from angle detection."""
    assumptions: list[dict] = []

    for angle in angles:
        angle_type = angle.get("type", "")
        evidence = angle.get("evidence", {})

        if angle_type == "trend":
            direction = evidence.get("direction", "unknown")
            r_squared = evidence.get("r_squared", 0)
            col = angle["columns"][-1] if angle.get("columns") else "metric"
            assumptions.append({
                "text": (
                    f"'{col}' shows {direction} trend (R-squared: {r_squared:.3f}). "
                    f"A linear model was assumed; non-linear patterns are not captured."
                ),
                "flag_type": "PATTERN",
                "confidence": 0.75,
                "source_reference": f"angle_detector: trend on {col}",
            })

        elif angle_type == "anomaly":
            col = angle["columns"][0] if angle.get("columns") else "metric"
            assumptions.append({
                "text": (
                    f"Outlier detection in '{col}' uses z-score with a 3-sigma "
                    f"threshold. This assumes approximately normal distribution."
                ),
                "flag_type": "PATTERN",
                "confidence": 0.75,
                "source_reference": f"angle_detector: outlier detection on {col}",
            })

        elif angle_type == "disruption":
            col = angle["columns"][0] if angle.get("columns") else "metric"
            ratio = evidence.get("volatility_ratio", 0)
            assumptions.append({
                "text": (
                    f"Disruption in '{col}' detected via rolling volatility "
                    f"(ratio: {ratio:.1f}x). Window size chosen heuristically."
                ),
                "flag_type": "PATTERN",
                "confidence": 0.75,
                "source_reference": f"angle_detector: disruption on {col}",
            })

        elif angle_type == "comparison":
            col_a = evidence.get("column_a", "")
            col_b = evidence.get("column_b", "")
            corr = evidence.get("correlation", 0)
            assumptions.append({
                "text": (
                    f"Correlation of {corr:.2f} between '{col_a}' and '{col_b}' "
                    f"measures linear association only."
                ),
                "flag_type": "PATTERN",
                "confidence": 0.75,
                "source_reference": f"angle_detector: correlation {col_a} vs {col_b}",
            })

        elif angle_type == "composition":
            cat_col = angle["columns"][0] if angle.get("columns") else "category"
            assumptions.append({
                "text": (
                    f"Composition breakdown by '{cat_col}' uses sum aggregation. "
                    f"Other aggregations (mean, median) may tell a different story."
                ),
                "flag_type": "PATTERN",
                "confidence": 0.75,
                "source_reference": f"angle_detector: composition by {cat_col}",
            })

    return assumptions


def _inferred_assumptions(
    df: pd.DataFrame,
    angles: list[dict],
    parsed_answers: list[dict],
) -> list[dict]:
    """INFERRED: contextual inferences not directly in data."""
    assumptions: list[dict] = []

    # Scope inference: columns not analysed
    total_cols = len(df.columns)
    analysed_cols: set[str] = set()
    for angle in angles:
        analysed_cols.update(angle.get("columns", []))

    if total_cols > 0 and len(analysed_cols) < total_cols:
        excluded_count = total_cols - len(analysed_cols)
        assumptions.append({
            "text": (
                f"Analysis covers {len(analysed_cols)} of {total_cols} columns. "
                f"{excluded_count} column(s) may contain additional insights."
            ),
            "flag_type": "INFERRED",
            "confidence": 0.40,
            "source_reference": "angle_detector: column coverage",
        })

    # Intent interpretation inference
    low_confidence_answers = [
        a for a in parsed_answers
        if a.get("confidence", 0) < 0.7 and a.get("parsed_intent") != "DEFAULT"
    ]
    if low_confidence_answers:
        assumptions.append({
            "text": (
                f"User intent was interpreted with low confidence for "
                f"{len(low_confidence_answers)} answer(s). "
                f"Narrative may not fully align with user expectations."
            ),
            "flag_type": "INFERRED",
            "confidence": 0.40,
            "source_reference": "template_engine: intent interpretation",
        })

    # Small sample size inference
    if len(df) < 30:
        assumptions.append({
            "text": (
                f"Dataset contains only {len(df)} rows. "
                f"Key drivers and patterns may not be statistically reliable."
            ),
            "flag_type": "INFERRED",
            "confidence": 0.40,
            "source_reference": "data_loader: sample size",
        })

    return assumptions
