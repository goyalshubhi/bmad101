import hashlib
from datetime import datetime

import pandas as pd


def _check_duplicates(df: pd.DataFrame) -> list[dict]:
    hashes = df.apply(lambda row: hashlib.md5(str(row.values).encode()).hexdigest(), axis=1)
    dupes = hashes[hashes.duplicated(keep=False)]
    if dupes.empty:
        return []
    dupe_count = len(dupes) - dupes.nunique()
    sample_rows = dupes[dupes.duplicated(keep="first")].index.tolist()[:5]
    severity = "high" if dupe_count / len(df) > 0.05 else "medium"
    return [{
        "severity": severity,
        "description": f"Found {dupe_count} duplicate rows",
        "count": dupe_count,
        "sample_rows": sample_rows,
    }]


def _check_encoding(df: pd.DataFrame) -> list[dict]:
    issues = []
    for col in df.select_dtypes(include=["object", "string"]).columns:
        replacement_count = 0
        for val in df[col].dropna().head(500):
            s = str(val)
            if "�" in s:
                replacement_count += 1
        if replacement_count > 0:
            issues.append({
                "severity": "high",
                "description": f"Encoding issues in column '{col}': {replacement_count} values contain replacement characters",
                "count": replacement_count,
                "sample_rows": [],
            })
    return issues


def _check_type_consistency(df: pd.DataFrame) -> list[dict]:
    issues = []
    for col in df.columns:
        series = df[col].dropna()
        if series.empty:
            continue
        numeric_count = pd.to_numeric(series, errors="coerce").notna().sum()
        total = len(series)
        if total == 0:
            continue
        ratio = numeric_count / total
        if 0.1 < ratio < 0.9:
            severity = "high" if abs(ratio - 0.5) < 0.1 else "medium"
            issues.append({
                "severity": severity,
                "description": f"Mixed types in column '{col}': {numeric_count}/{total} numeric",
                "count": total,
                "sample_rows": [],
            })
    return issues


def _check_date_ranges(df: pd.DataFrame) -> list[dict]:
    issues = []
    current_year = datetime.now().year
    for col in df.columns:
        try:
            dates = pd.to_datetime(df[col], errors="coerce", format="mixed")
        except Exception:
            continue
        valid_dates = dates.dropna()
        if valid_dates.empty or len(valid_dates) < len(df[col].dropna()) * 0.5:
            continue
        bad_rows = []
        for idx, dt in valid_dates.items():
            if dt.year < 1900 or dt.year > current_year + 5:
                bad_rows.append(idx)
        if bad_rows:
            issues.append({
                "severity": "medium",
                "description": f"Unrealistic dates in column '{col}'",
                "count": len(bad_rows),
                "sample_rows": bad_rows[:5],
            })
    return issues


def _check_cardinality(df: pd.DataFrame) -> list[dict]:
    issues = []
    for col in df.columns:
        unique_count = df[col].nunique()
        if unique_count > 1000:
            issues.append({
                "severity": "low",
                "description": f"High cardinality in column '{col}': {unique_count} unique values",
                "count": unique_count,
                "sample_rows": [],
            })
    return issues


def _check_missing_data(df: pd.DataFrame) -> list[dict]:
    issues = []
    for col in df.columns:
        missing_pct = df[col].isna().mean()
        if missing_pct > 0:
            severity = "high" if missing_pct > 0.5 else "medium" if missing_pct > 0.1 else "low"
            issues.append({
                "severity": severity,
                "description": f"Missing data in column '{col}': {missing_pct:.1%}",
                "count": int(df[col].isna().sum()),
                "sample_rows": df[col][df[col].isna()].index.tolist()[:5],
            })
    return issues


def run_quality_checks(df: pd.DataFrame) -> dict:
    all_issues = []
    all_issues.extend(_check_duplicates(df))
    all_issues.extend(_check_encoding(df))
    all_issues.extend(_check_type_consistency(df))
    all_issues.extend(_check_date_ranges(df))
    all_issues.extend(_check_cardinality(df))
    all_issues.extend(_check_missing_data(df))

    if not all_issues:
        status = "CLEAN"
    else:
        status = "ISSUES_BLOCKING"

    return {
        "quality_issues": all_issues,
        "status": status,
    }
