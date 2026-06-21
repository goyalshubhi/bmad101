from __future__ import annotations

import re


_FIGURE_PATTERNS = [
    re.compile(r"-?\$[\d,]+\.?\d*[KMB]?"),
    re.compile(r"-?\d+[.,]\d+%"),
    re.compile(r"-?\d{2,}[.,]\d+"),
    re.compile(r"(?<![.\d])-?\d{3,}(?!\d)"),
]

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

_YEAR_PATTERN = re.compile(r"^-?\d{4}$")
_LIKELY_NON_FINANCIAL = re.compile(r"^(19|20)\d{2}$")


def _is_likely_non_financial(value: str) -> bool:
    bare = value.lstrip("-")
    if _LIKELY_NON_FINANCIAL.match(bare):
        return True
    if bare.isdigit() and len(bare) <= 2:
        return True
    return False


def _find_sentence(text: str, start: int, end: int) -> str:
    sentences = _SENTENCE_SPLIT.split(text)
    pos = 0
    for sentence in sentences:
        idx = text.find(sentence, pos)
        if idx == -1:
            pos += len(sentence)
            continue
        sent_end = idx + len(sentence)
        if idx <= start < sent_end:
            return sentence.strip()
        pos = sent_end
    return text[max(0, start - 50):end + 50].strip()


def extract_figures(narrative_text: str) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    results: list[dict] = []

    for pattern in _FIGURE_PATTERNS:
        for match in pattern.finditer(narrative_text):
            value = match.group()
            if _is_likely_non_financial(value):
                continue
            context_sentence = _find_sentence(narrative_text, match.start(), match.end())
            key = (value, context_sentence)
            if key in seen:
                continue
            seen.add(key)
            results.append({
                "value": value,
                "context_sentence": context_sentence,
                "narrative_position": match.start(),
            })

    results.sort(key=lambda f: f["narrative_position"])
    return results
