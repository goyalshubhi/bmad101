import re

KEYWORD_RULES: list[tuple[re.Pattern, str, float]] = [
    (re.compile(r"\b(?:profit|margin|profitability)\b", re.IGNORECASE), "PROFIT", 0.9),
    (re.compile(r"\b(?:revenue|sales|growth)\b", re.IGNORECASE), "GROWTH", 0.85),
    (re.compile(r"\b(?:cost|spending|efficiency)\b", re.IGNORECASE), "COST", 0.9),
    (re.compile(r"\b(?:market|share|position)\b", re.IGNORECASE), "MARKET", 0.8),
    (re.compile(r"\b(?:board|directors|governance)\b", re.IGNORECASE), "BOARD", 0.9),
    (re.compile(r"\b(?:investors|shareholders)\b", re.IGNORECASE), "INVESTORS", 0.85),
    (re.compile(r"\b(?:executive|leadership|c-suite)\b", re.IGNORECASE), "EXECUTIVE", 0.85),
    (re.compile(r"\b(?:operations|ops|team)\b", re.IGNORECASE), "OPERATIONS", 0.8),
]


def _match_intent(text: str) -> tuple[str, float]:
    for pattern, intent, confidence in KEYWORD_RULES:
        if pattern.search(text):
            return intent, confidence
    return "UNKNOWN", 0.5


def parse_answers(questions: list[dict], answers: list[dict]) -> dict:
    questions_by_id = {q["id"]: q for q in questions}
    parsed: list[dict] = []

    for answer in answers:
        qid = answer["question_id"]
        if qid not in questions_by_id:
            continue
        text = answer.get("text", "").strip()

        if text.lower() == "skip" or text == "":
            parsed.append({
                "question_id": qid,
                "raw_answer": text,
                "parsed_intent": "DEFAULT",
                "confidence": 0.0,
                "defaulted": True,
            })
        else:
            intent, confidence = _match_intent(text)
            parsed.append({
                "question_id": qid,
                "raw_answer": text,
                "parsed_intent": intent,
                "confidence": confidence,
            })

    tier1_ids = {q["id"] for q in questions if q.get("tier") == 1}
    answered_ids = {a["question_id"] for a in parsed}
    ready_to_generate = tier1_ids.issubset(answered_ids)

    return {
        "parsed": parsed,
        "ready_to_generate": ready_to_generate,
    }
