import uuid


def generate_questions(schema: dict, quality_report: dict) -> list[dict]:
    questions: list[dict] = []

    numeric_cols = [col for col, info in schema.items() if info.get("type") == "numeric"]
    datetime_cols = [col for col, info in schema.items() if info.get("type") == "datetime"]
    high_cardinality_cols = [col for col, info in schema.items() if info.get("cardinality", 0) > 1000]

    issues = quality_report.get("issues", [])
    total_rows = quality_report.get("total_rows", 0)
    has_data_gaps = False
    if total_rows > 0:
        total_issue_count = sum(i.get("count", 0) for i in issues)
        has_data_gaps = (total_issue_count / total_rows) > 0.05
    elif any(i.get("count", 0) > 0 for i in issues):
        has_data_gaps = True

    # Tier 1: Always included
    if len(numeric_cols) >= 2:
        questions.append({
            "id": str(uuid.uuid4()),
            "template": "Which metric should be the headline figure for your presentation?",
            "context": f"Your data contains {len(numeric_cols)} numeric columns: {', '.join(numeric_cols[:5])}",
            "suggestion_chips": numeric_cols[:6],
            "tier": 1,
        })

    questions.append({
        "id": str(uuid.uuid4()),
        "template": "Who is the primary audience for this presentation?",
        "context": "Understanding your audience helps tailor the narrative tone and detail level.",
        "suggestion_chips": ["Board of Directors", "Investors", "Executive Team", "Operations Team"],
        "tier": 1,
    })

    # Tier 2: Included only if ambiguous/relevant
    if datetime_cols and numeric_cols:
        questions.append({
            "id": str(uuid.uuid4()),
            "template": "What time period should we compare against?",
            "context": f"Temporal column detected: {datetime_cols[0]}. Numeric columns available for comparison.",
            "suggestion_chips": ["Previous Quarter", "Year-over-Year", "Month-over-Month", "Custom Range"],
            "tier": 2,
        })

    if high_cardinality_cols:
        questions.append({
            "id": str(uuid.uuid4()),
            "template": "How many top items should we highlight?",
            "context": f"Column '{high_cardinality_cols[0]}' has high cardinality (many unique values).",
            "suggestion_chips": ["Top 5", "Top 10", "Top 20", "All"],
            "tier": 2,
        })

    if has_data_gaps:
        gap_count = len([i for i in issues if i.get("count", 0) > 0])
        questions.append({
            "id": str(uuid.uuid4()),
            "template": "How should we handle missing or incomplete data?",
            "context": f"Quality report identified {gap_count} data issue(s) exceeding 5% threshold.",
            "suggestion_chips": ["Exclude incomplete rows", "Fill with averages", "Flag in presentation", "Ignore gaps"],
            "tier": 2,
        })

    # If fewer than 2 numeric cols, add a fallback headline question
    if len(numeric_cols) < 2 and len(numeric_cols) == 1:
        questions.insert(0, {
            "id": str(uuid.uuid4()),
            "template": "Which metric should be the headline figure for your presentation?",
            "context": f"Your data contains the numeric column: {numeric_cols[0]}",
            "suggestion_chips": numeric_cols,
            "tier": 1,
        })

    # Ensure we have 4-5 questions; add priority question if we have room and mixed signals
    if len(questions) < 4 and len(numeric_cols) >= 2:
        questions.append({
            "id": str(uuid.uuid4()),
            "template": "What is the key message you want to convey?",
            "context": "Multiple metrics detected. Clarifying priority helps focus the narrative.",
            "suggestion_chips": ["Growth Story", "Profitability Focus", "Cost Reduction", "Market Position"],
            "tier": 2,
        })

    # H3/H4: Fallback questions to guarantee at least 4 for sparse schemas
    existing_templates = {q["template"] for q in questions}
    fallback_questions = [
        {
            "template": "What is the key message you want to convey?",
            "context": "Clarifying priority helps focus the narrative.",
            "suggestion_chips": ["Growth Story", "Profitability Focus", "Cost Reduction", "Market Position"],
        },
        {
            "template": "What time frame is most relevant for your analysis?",
            "context": "Defining the time scope helps structure the presentation flow.",
            "suggestion_chips": ["Last Quarter", "Year-to-Date", "Last 12 Months", "Custom Range"],
        },
        {
            "template": "Are there any specific data points you want to highlight?",
            "context": "Highlighting key data points ensures the most important insights stand out.",
            "suggestion_chips": ["Highest Values", "Outliers", "Trends", "Comparisons"],
        },
        {
            "template": "What level of detail does your audience prefer?",
            "context": "Matching detail level to audience expectations improves presentation impact.",
            "suggestion_chips": ["High-Level Summary", "Detailed Analysis", "Key Metrics Only", "Full Breakdown"],
        },
    ]
    for fallback in fallback_questions:
        if len(questions) >= 4:
            break
        if fallback["template"] not in existing_templates:
            questions.append({
                "id": str(uuid.uuid4()),
                "template": fallback["template"],
                "context": fallback["context"],
                "suggestion_chips": fallback["suggestion_chips"],
                "tier": 2,
            })

    # Cap at 5 questions, Tier 1 first (already ordered by insertion)
    questions.sort(key=lambda q: q["tier"])
    return questions[:5]
