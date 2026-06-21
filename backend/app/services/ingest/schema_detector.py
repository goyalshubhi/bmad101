import pandas as pd

SAMPLE_ROWS = 1000


def _clean_column_name(name: str) -> str:
    return str(name).strip().lower().replace(" ", "_")


def _infer_type(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    try:
        pd.to_datetime(series.dropna().head(20), format="mixed")
        return "datetime"
    except (ValueError, TypeError):
        pass
    return "text"


def _detect_date_format(series: pd.Series) -> str | None:
    sample = series.dropna().head(10).astype(str)
    for fmt, pattern in [
        ("%Y-%m-%d", "YYYY-MM-DD"),
        ("%m/%d/%Y", "MM/DD/YYYY"),
        ("%d/%m/%Y", "DD/MM/YYYY"),
        ("%Y/%m/%d", "YYYY/MM/DD"),
    ]:
        try:
            pd.to_datetime(sample, format=fmt)
            return pattern
        except (ValueError, TypeError):
            continue
    return None


def detect_schema(df: pd.DataFrame) -> dict:
    sample = df.head(SAMPLE_ROWS)
    schema = {}
    for col in sample.columns:
        clean_name = _clean_column_name(col)
        series = sample[col]
        col_type = _infer_type(series)
        nullability = round(float(series.isna().mean()), 4)
        cardinality = int(series.nunique())
        date_format = _detect_date_format(series) if col_type == "datetime" else None

        entry: dict = {
            "type": col_type,
            "nullability": nullability,
            "cardinality": cardinality,
        }
        if date_format:
            entry["date_format"] = date_format

        schema[clean_name] = entry
    return schema
