from __future__ import annotations


def parse_numeric(value_str: str) -> float | None:
    s = value_str.replace("$", "").replace(",", "").replace("%", "")
    multiplier = 1
    if s.endswith("K"):
        multiplier = 1_000
        s = s[:-1]
    elif s.endswith("M"):
        multiplier = 1_000_000
        s = s[:-1]
    elif s.endswith("B"):
        multiplier = 1_000_000_000
        s = s[:-1]
    try:
        return float(s) * multiplier
    except ValueError:
        return None


def is_percentage(value_str: str) -> bool:
    return value_str.rstrip().endswith("%")
