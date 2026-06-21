"""Template-based narrative generation.

Fills narrative templates using detected angles, user intent, and actual
data values.  Produces one narrative dict per angle.
No LLM/AI -- pure template substitution.
"""

from __future__ import annotations

import uuid
from typing import Any

import numpy as np
import pandas as pd


# --- Viz recommendation mapping by angle type ---

VIZ_RECOMMENDATIONS: dict[str, dict[str, str]] = {
    "trend": {
        "chart_type": "line",
        "justification": "Shows temporal progression of {metric}",
    },
    "disruption": {
        "chart_type": "line_with_bands",
        "justification": "Highlights volatility deviation from baseline",
    },
    "composition": {
        "chart_type": "stacked_bar",
        "justification": "Shows proportional breakdown by category",
    },
    "anomaly": {
        "chart_type": "scatter",
        "justification": "Highlights outlier values against normal distribution",
    },
    "comparison": {
        "chart_type": "dual_axis",
        "justification": "Shows correlation between variables",
    },
}


# --- Narrative templates keyed by angle type ---

TEMPLATES: dict[str, str] = {
    "trend": (
        "**{col}** demonstrates a clear {direction} trajectory, "
        "moving approximately {pct_change:.1f}% over the analysis period "
        "(from {first_value:.2f} to {last_value:.2f}). "
        "This trend, supported by an R-squared of {r_squared:.4f}, "
        "signals {implication}."
    ),
    "disruption": (
        "**{col}** shows a significant volatility spike in the most recent "
        "window. Rolling standard deviation ({rolling_std:.2f}) is "
        "{volatility_ratio:.1f}x the overall standard deviation "
        "({overall_std:.2f}), indicating a potential disruption in the "
        "underlying pattern."
    ),
    "comparison": (
        "**{col_a}** and **{col_b}** exhibit a {direction} correlation "
        "of {correlation:.2f} across {sample_size} observations. "
        "This suggests a meaningful {direction} relationship between "
        "these variables."
    ),
    "anomaly": (
        "**{col}** contains {outlier_count} data point(s) outside normal "
        "bounds ({outlier_pct:.1f}% of values), deviating more than 3 "
        "standard deviations from the mean of {mean:.2f} "
        "(std: {std:.2f}). These outliers may represent exceptional events "
        "or data quality issues."
    ),
    "composition": (
        "The breakdown of **{num_col}** by **{cat_col}** shows "
        "**{top_category}** commanding {top_share:.1f}% of the total. "
        "This level of concentration across {num_categories} segments "
        "presents both opportunity and risk."
    ),
}

TREND_IMPLICATIONS = {
    "upward": "a positive trajectory worth monitoring",
    "downward": "a declining trend that merits investigation",
}


def generate_narratives(
    angles: list[dict],
    parsed_answers: list[dict],
    schema: dict,
    df: pd.DataFrame,
) -> list[dict]:
    """Generate one narrative dict per detected angle.

    Each narrative includes the rendered text and a viz recommendation.

    Args:
        angles: Detected angles from ``angle_detector.detect_angles``.
        parsed_answers: Parsed answers from the question session.
        schema: Schema dict describing column types.
        df: The ingested DataFrame for filling actual values.

    Returns:
        List of narrative dicts, each with:
          - id (str UUID)
          - story_angle (str) -- angle type
          - narrative_text (str) -- rendered narrative
          - viz_recommendation (dict) -- chart recommendation
          - angle_id (str) -- source angle id
    """
    if not angles:
        return [_fallback_narrative()]

    narratives: list[dict] = []

    for angle in angles:
        angle_type = angle["type"]
        evidence = angle.get("evidence", {})
        columns = angle.get("columns", [])

        # Build context with actual data values
        context = _build_template_context(angle, evidence, columns, df)

        # Render narrative text
        template = TEMPLATES.get(angle_type, "{description}")
        try:
            narrative_text = template.format(**context, description=angle.get("description", ""))
        except (KeyError, IndexError):
            narrative_text = angle.get("description", "Data pattern detected.")

        # Build viz recommendation
        viz_rec = _build_viz_recommendation(angle_type, columns)

        narratives.append({
            "id": str(uuid.uuid4()),
            "story_angle": angle_type,
            "narrative_text": narrative_text,
            "viz_recommendation": viz_rec,
            "angle_id": angle["id"],
        })

    return narratives


def _build_viz_recommendation(angle_type: str, columns: list[str]) -> dict:
    """Build visualization recommendation for an angle type."""
    template = VIZ_RECOMMENDATIONS.get(angle_type, {
        "chart_type": "bar",
        "justification": "General data visualization",
    })
    metric = columns[-1] if columns else "metric"
    return {
        "chart_type": template["chart_type"],
        "justification": template["justification"].format(metric=metric),
    }


def _build_template_context(
    angle: dict,
    evidence: dict,
    columns: list[str],
    df: pd.DataFrame,
) -> dict:
    """Build the dict used for template string formatting with actual data values."""
    ctx: dict[str, Any] = {
        "col": columns[-1] if columns else "metric",
        "cat_col": columns[0] if len(columns) > 1 else "category",
    }

    angle_type = angle["type"]

    if angle_type == "trend":
        direction = evidence.get("direction", "upward")
        ctx["direction"] = direction
        ctx["pct_change"] = abs(evidence.get("pct_change", 0))
        ctx["r_squared"] = evidence.get("r_squared", 0)
        ctx["implication"] = TREND_IMPLICATIONS.get(direction, TREND_IMPLICATIONS["upward"])
        # Fill actual first/last values from data
        col = columns[-1] if columns else None
        if col and col in df.columns:
            values = pd.to_numeric(df[col], errors="coerce").dropna()
            ctx["first_value"] = float(values.iloc[0]) if len(values) > 0 else 0.0
            ctx["last_value"] = float(values.iloc[-1]) if len(values) > 0 else 0.0
        else:
            ctx["first_value"] = 0.0
            ctx["last_value"] = 0.0

    elif angle_type == "disruption":
        ctx["rolling_std"] = evidence.get("rolling_std", 0)
        ctx["overall_std"] = evidence.get("overall_std", 0)
        ctx["volatility_ratio"] = evidence.get("volatility_ratio", 0)

    elif angle_type == "comparison":
        ctx["col_a"] = evidence.get("column_a", columns[0] if columns else "A")
        ctx["col_b"] = evidence.get("column_b", columns[1] if len(columns) > 1 else "B")
        ctx["correlation"] = evidence.get("correlation", 0)
        ctx["direction"] = evidence.get("direction", "positive")
        ctx["sample_size"] = evidence.get("sample_size", 0)

    elif angle_type == "anomaly":
        ctx["outlier_count"] = evidence.get("outlier_count", 0)
        ctx["outlier_pct"] = evidence.get("outlier_pct", 0)
        ctx["mean"] = evidence.get("mean", 0)
        ctx["std"] = evidence.get("std", 0)

    elif angle_type == "composition":
        ctx["num_col"] = columns[-1] if columns else "metric"
        ctx["top_category"] = evidence.get("top_category", "Leader")
        ctx["top_share"] = evidence.get("top_share_pct", 0)
        ctx["num_categories"] = evidence.get("num_categories", 2)

    return ctx


def compute_confidence(
    df: pd.DataFrame,
    angle: dict,
    parsed_answers: list[dict],
) -> float:
    """Compute overall confidence score for a narrative.

    Combines three factors:
      - data_completeness: 1.0 - (null cells / total cells) for columns in the angle
      - angle_strength: the angle's strength field
      - user_intent_match: 1.0 if direct match, 0.7 if related, 0.4 if unrelated

    Returns:
        Float in [0.0, 1.0].
    """
    # Data completeness for columns used in the angle
    angle_cols = [c for c in angle.get("columns", []) if c in df.columns]
    if angle_cols:
        subset = df[angle_cols]
        total_cells = subset.shape[0] * subset.shape[1]
        null_cells = int(subset.isnull().sum().sum())
        data_completeness = 1.0 - (null_cells / total_cells) if total_cells > 0 else 0.0
    else:
        data_completeness = 1.0

    # Angle strength
    angle_strength = angle.get("strength", 0.5)

    # User intent match
    angle_type = angle.get("type", "")
    user_intent = _extract_dominant_intent(parsed_answers)
    user_intent_match = _compute_intent_match(user_intent, angle_type)

    overall = data_completeness * angle_strength * user_intent_match
    return round(max(0.0, min(1.0, overall)), 4)


def _compute_intent_match(user_intent: str, angle_type: str) -> float:
    """Score how well an angle type matches user intent."""
    # Direct match mappings
    direct_matches: dict[str, set[str]] = {
        "GROWTH": {"trend"},
        "PROFIT": {"trend", "comparison"},
        "COST": {"trend", "anomaly"},
        "MARKET": {"comparison", "composition"},
        "RISK": {"anomaly", "disruption"},
    }

    related_matches: dict[str, set[str]] = {
        "GROWTH": {"comparison", "composition"},
        "PROFIT": {"composition", "anomaly"},
        "COST": {"composition", "disruption"},
        "MARKET": {"trend", "disruption"},
        "RISK": {"trend", "composition"},
    }

    if user_intent in direct_matches and angle_type in direct_matches[user_intent]:
        return 1.0
    if user_intent in related_matches and angle_type in related_matches[user_intent]:
        return 0.7
    if user_intent == "GENERAL":
        return 0.7
    return 0.4


def _extract_dominant_intent(parsed_answers: list[dict]) -> str:
    """Extract the dominant user intent from parsed answers."""
    for answer in parsed_answers:
        intent = answer.get("parsed_intent", "UNKNOWN")
        confidence = answer.get("confidence", 0.0)
        if intent not in ("UNKNOWN", "DEFAULT") and confidence >= 0.7:
            return intent
    return "GENERAL"


def _fallback_narrative() -> dict:
    """Generate a minimal fallback narrative when no angles detected."""
    return {
        "id": str(uuid.uuid4()),
        "story_angle": "general",
        "narrative_text": (
            "The uploaded data does not exhibit strong statistical "
            "patterns for automated narrative generation. "
            "Consider reviewing the data for additional context "
            "or providing more specific guidance."
        ),
        "viz_recommendation": {"chart_type": "bar", "justification": "General overview"},
        "angle_id": None,
    }
