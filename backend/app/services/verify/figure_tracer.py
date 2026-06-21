from __future__ import annotations

import numpy as np
import pandas as pd

from app.services.verify.numeric_parser import parse_numeric


def trace_figures(
    figures: list[dict],
    df: pd.DataFrame,
    schema: dict,
) -> list[dict]:
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    results: list[dict] = []

    for fig in figures:
        fig_val = parse_numeric(fig["value"])
        if fig_val is None:
            results.append({
                "figure_value": fig["value"],
                "source_rows": "",
                "formula": "UNPARSEABLE",
                "match_status": "mismatch",
                "variance_pct": 100.0,
            })
            continue

        best_match: dict | None = None
        best_variance = float("inf")

        for col in numeric_cols:
            col_data = df[col].dropna()
            if col_data.empty:
                continue

            row_range = f"1-{len(df)}"
            aggs = [
                ("SUM", col_data.sum()),
                ("AVG", col_data.mean()),
                ("COUNT", float(len(col_data))),
                ("MIN", col_data.min()),
                ("MAX", col_data.max()),
            ]

            for agg_name, agg_val in aggs:
                if agg_val == 0 and fig_val == 0:
                    variance_pct = 0.0
                elif agg_val == 0:
                    continue
                else:
                    variance_pct = abs(fig_val - agg_val) / abs(agg_val) * 100

                if variance_pct < best_variance:
                    best_variance = variance_pct
                    if variance_pct == 0:
                        match_status = "exact"
                    elif variance_pct <= 1:
                        match_status = "within_tolerance"
                    else:
                        match_status = "mismatch"
                    best_match = {
                        "figure_value": fig["value"],
                        "source_rows": row_range,
                        "formula": f"{agg_name}({col})",
                        "match_status": match_status,
                        "variance_pct": round(variance_pct, 4),
                    }

            exact_matches = col_data[col_data == fig_val]
            if not exact_matches.empty and best_variance > 0.0:
                row_indices = exact_matches.index.tolist()
                row_str = ",".join(str(int(r) + 1) if isinstance(r, (int, float, np.integer)) else str(r) for r in row_indices[:10])
                best_variance = 0.0
                best_match = {
                    "figure_value": fig["value"],
                    "source_rows": row_str,
                    "formula": f"VALUE({col})",
                    "match_status": "exact",
                    "variance_pct": 0.0,
                }

        if best_match:
            results.append(best_match)
        else:
            results.append({
                "figure_value": fig["value"],
                "source_rows": "",
                "formula": "NO_MATCH",
                "match_status": "mismatch",
                "variance_pct": 100.0,
            })

    return results
