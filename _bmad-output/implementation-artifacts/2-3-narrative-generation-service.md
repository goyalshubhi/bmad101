# Story 2.3: Narrative Generation Service

Status: ready-for-dev

## Story

As an analyst,
I want the system to generate 2-3 data-grounded narrative options based on my answers and detected patterns,
so that I can choose the interpretation that best frames my data story.

## Acceptance Criteria

1. **Given** a completed question session with parsed answers, **When** the narrative generation service runs, **Then** story angles are detected from data using: linear regression (trend), rolling std deviation (disruption), composition shifts (composition), outlier detection >3 sigma (anomaly), categorical breakdown (comparison), **And** 2-3 narrative templates are selected based on the combination of detected angles and parsed user intent, **And** each narrative is generated using template-filling logic (no live LLM API calls): "{metric} has {changed} from {period1} to {period2}. Key drivers: {top_3_factors}. Status: {risk_level}".

2. **Given** narratives are generated, **When** confidence scores are computed, **Then** each narrative has `overall_confidence = data_completeness * angle_strength * user_intent_match` (all 0-1 floats).

3. **Given** narratives are generated, **When** assumptions are extracted, **Then** every inference is flagged: EXPLICIT (in data, 100%), PATTERN (statistical pattern, 75%), INFERRED (contextual, 40%), **And** SPECULATIVE assumptions (0%) are blocked -- never included in output, **And** each narrative includes a `viz_recommendation` with chart type and justification.

4. **Given** narrative generation completes, **When** results are stored, **Then** 2-3 rows are created in the `narratives` table with `story_angle`, `narrative_text`, `viz_recommendation`, `assumptions_json`, `overall_confidence`, **And** `GET /api/v1/decks/{deck_id}/narratives` returns all options, **And** generation completes in < 2 seconds.

## Tasks / Subtasks

- [ ] Task 1: Database model and migration for narratives table (AC: #4)
  - [ ] 1.1 Create `backend/app/models/narrative.py` -- SQLAlchemy async model:
    - `id` (UUID PK, default uuid4)
    - `deck_id` (UUID FK -> decks.id, not null, indexed)
    - `question_session_id` (UUID FK -> question_sessions.id, not null) -- links narrative to the session that produced it
    - `story_angle` (String(50), not null) -- one of: "trend", "disruption", "composition", "anomaly", "comparison"
    - `narrative_text` (Text, not null) -- the generated narrative paragraph
    - `viz_recommendation` (JSONB, nullable) -- `{ chart_type: str, justification: str }`
    - `assumptions_json` (JSONB, nullable) -- `[{ text: str, flag_type: "EXPLICIT"|"PATTERN"|"INFERRED", confidence: float, source_reference: str }]`
    - `overall_confidence` (Float, not null) -- computed as data_completeness * angle_strength * user_intent_match
    - `created_at` (DateTime, server_default=func.now())
  - [ ] 1.2 Register model in `backend/app/models/__init__.py` -- add `Narrative` to imports and `__all__`
  - [ ] 1.3 Create Alembic migration `backend/alembic/versions/004_add_narratives.py` -- creates `narratives` table with index on `deck_id` and `question_session_id`

- [ ] Task 2: Story angle detection module (AC: #1)
  - [ ] 2.1 Create `backend/app/services/narratives/__init__.py`
  - [ ] 2.2 Create `backend/app/services/narratives/angle_detector.py` -- `detect_angles(df: pd.DataFrame, schema: dict) -> list[dict]`
    - Input: the ingested DataFrame (loaded from file_url via storage service or reconstructed) and schema_json
    - Detect up to 5 angle types from numeric columns in the data:
      - **trend**: For each numeric column with a paired datetime column, run `scipy.stats.linregress` (or numpy polyfit). If |slope| is significant relative to mean and R-squared > 0.3, flag as trend. Store: `{ angle: "trend", column: str, direction: "up"|"down", r_squared: float, strength: float }`
      - **disruption**: For each numeric column, compute rolling std deviation (window=max(3, len//10)). If latest window std > 2x overall std, flag as disruption. Store: `{ angle: "disruption", column: str, recent_volatility: float, baseline_volatility: float, strength: float }`
      - **composition**: If there are categorical columns with associated numeric columns, compute proportional shares. If top category > 40% of total or bottom category < 2%, flag composition. Store: `{ angle: "composition", category_column: str, value_column: str, top_category: str, top_share: float, strength: float }`
      - **anomaly**: For each numeric column, detect values > 3 standard deviations from mean. If any exist, flag as anomaly. Store: `{ angle: "anomaly", column: str, outlier_count: int, threshold: float, strength: float }`
      - **comparison**: If 2+ numeric columns exist, compute pairwise correlations. If any pair has correlation > 0.7 or < -0.3, flag as comparison opportunity. Store: `{ angle: "comparison", columns: [str, str], correlation: float, strength: float }`
    - Each angle gets a `strength` score (0-1) based on statistical significance
    - Return sorted by strength descending, top 3-5 angles
    - IMPORTANT: Use numpy for statistical operations (already a transitive dependency via pandas). For linregress, use `numpy.polyfit(x, y, 1)` rather than adding scipy as a dependency. Compute R-squared manually: `1 - (SS_res / SS_tot)`

- [ ] Task 3: Narrative template engine (AC: #1, #3)
  - [ ] 3.1 Create `backend/app/services/narratives/template_engine.py` -- `generate_narratives(angles: list[dict], parsed_answers: dict, schema: dict, df: pd.DataFrame) -> list[dict]`
    - Input: detected angles, parsed answer data (from question_sessions.answers_json), schema, and DataFrame
    - Select 2-3 narrative templates based on strongest angles + user intent alignment:
      - Map parsed_intent from answers to angle relevance (e.g., PROFIT intent + trend angle = strong match, GROWTH intent + disruption angle = moderate match)
      - Score each angle-intent combo: `intent_match = 1.0 if direct match, 0.7 if related, 0.4 if unrelated`
    - Template patterns (fill from actual data values):
      - **trend**: "{metric} has {increased/decreased} by {pct_change}% from {period1} to {period2}. Key drivers: {top_factors}. The trajectory suggests {risk_level}."
      - **disruption**: "Recent volatility in {metric} signals a shift: {recent_std} vs historical {baseline_std}. This {metric} disruption is driven by {factors}."
      - **composition**: "{top_category} dominates {metric} at {share}% of total. The remaining {n} categories account for {remainder}%."
      - **anomaly**: "{outlier_count} anomalous values detected in {metric}, exceeding {threshold} threshold. Notable: {top_outlier_description}."
      - **comparison**: "{col1} and {col2} show {strong/moderate} {positive/negative} correlation ({corr_value}). Changes in {col1} are associated with {direction} movement in {col2}."
    - Fill templates with actual computed values from the DataFrame
    - Each generated narrative includes `narrative_text`, `story_angle`, `viz_recommendation`
  - [ ] 3.2 Viz recommendation logic:
    - trend -> `{ chart_type: "line", justification: "Shows temporal progression of {metric}" }`
    - disruption -> `{ chart_type: "line_with_bands", justification: "Highlights volatility deviation from baseline" }`
    - composition -> `{ chart_type: "stacked_bar", justification: "Shows proportional breakdown of {metric} by {category}" }`
    - anomaly -> `{ chart_type: "scatter", justification: "Highlights outlier values against normal distribution" }`
    - comparison -> `{ chart_type: "dual_axis", justification: "Shows correlation between {col1} and {col2}" }`

- [ ] Task 4: Assumption extraction and flagging (AC: #3)
  - [ ] 4.1 Create `backend/app/services/narratives/assumption_extractor.py` -- `extract_assumptions(narrative_text: str, angles: list[dict], schema: dict, df: pd.DataFrame) -> list[dict]`
    - For each statement in the narrative, classify the inference type:
      - **EXPLICIT** (confidence=1.0): Direct data facts -- values that exist verbatim in data (e.g., "Revenue was $5M" when $5M is in the data). Source: "Row X, Column Y"
      - **PATTERN** (confidence=0.75): Statistical patterns -- derived from analysis (e.g., "Revenue shows an upward trend"). Source: "Linear regression R²={value}"
      - **INFERRED** (confidence=0.40): Contextual inferences -- not directly in data but reasonable (e.g., "Key drivers include seasonal demand"). Source: "Inferred from {pattern}"
      - **SPECULATIVE** (confidence=0.0): Pure speculation -- BLOCKED, never include in output
    - Each assumption: `{ text: str, flag_type: "EXPLICIT"|"PATTERN"|"INFERRED", confidence: float, source_reference: str }`
    - Implementation approach: Parse the narrative text sentence by sentence. For each sentence, check if values match data (EXPLICIT), derive from angle detection output (PATTERN), or are fill-in contextual phrases (INFERRED). Filter out any with flag_type SPECULATIVE

- [ ] Task 5: Confidence scoring (AC: #2)
  - [ ] 5.1 Add confidence computation in `backend/app/services/narratives/template_engine.py` or as a separate function:
    - `compute_confidence(schema: dict, df: pd.DataFrame, angle: dict, parsed_answers: dict) -> float`
    - `data_completeness` (0-1): `1.0 - (total_null_cells / total_cells)` across all columns used in this angle
    - `angle_strength` (0-1): directly from the angle's `strength` field computed in angle_detector
    - `user_intent_match` (0-1): how well the user's parsed answers align with this angle (from intent mapping in Task 3)
    - `overall_confidence = data_completeness * angle_strength * user_intent_match`
    - Clamp to [0.0, 1.0]

- [ ] Task 6: Data loading utility (AC: #1)
  - [ ] 6.1 Create `backend/app/services/narratives/data_loader.py` -- `load_dataframe(ingest_job: IngestJob) -> pd.DataFrame`
    - Load the CSV/data file from MinIO/S3 using the `file_url` stored on the ingest_job
    - Reuse the storage service pattern from `backend/app/services/storage.py` for S3 download
    - Parse into pandas DataFrame using the same adapter logic from `backend/app/services/ingest/csv_adapter.py`
    - IMPORTANT: For MVP, the ingest service stores files in MinIO. The `file_url` field on IngestJob has the S3 key. Use `boto3` to download the file to a temp path, then read with pandas
    - If file_url is None or download fails, raise a clear error

- [ ] Task 7: API endpoints (AC: #4)
  - [ ] 7.1 Create `backend/app/api/v1/endpoints/narratives.py` with router
  - [ ] 7.2 `POST /api/v1/decks/{deck_id}/generate-narratives` endpoint:
    - Fetch latest question_session for deck_id where `answers_json IS NOT NULL` (must have completed questions)
    - Fetch latest validated ingest_job for deck_id (need schema_json and file_url)
    - Load DataFrame via data_loader
    - Call `detect_angles(df, schema)`
    - Call `generate_narratives(angles, answers, schema, df)`
    - For each generated narrative, call `extract_assumptions()` and `compute_confidence()`
    - Create Narrative rows in DB
    - Return `{ narratives: [{ id, story_angle, narrative_text, viz_recommendation, assumptions, overall_confidence }] }`
    - Entire generation must complete in < 2 seconds (NFR3)
  - [ ] 7.3 `GET /api/v1/decks/{deck_id}/narratives` endpoint:
    - Fetch all Narrative rows for deck_id, ordered by overall_confidence DESC
    - Return `{ narratives: [{ id, story_angle, narrative_text, viz_recommendation, assumptions_json, overall_confidence }] }`
    - If no narratives exist, return empty list (not 404)
  - [ ] 7.4 Create `backend/app/api/v1/schemas/narratives.py` -- Pydantic models:
    - `AssumptionResponse`: `{ text: str, flag_type: str, confidence: float, source_reference: str }`
    - `VizRecommendation`: `{ chart_type: str, justification: str }`
    - `NarrativeResponse`: `{ id: str, story_angle: str, narrative_text: str, viz_recommendation: VizRecommendation | None, assumptions: list[AssumptionResponse], overall_confidence: float }`
    - `NarrativesListResponse`: `{ narratives: list[NarrativeResponse] }`
  - [ ] 7.5 Register narratives router in `backend/app/api/v1/router.py` -- add `from app.api.v1.endpoints import narratives` and `api_router.include_router(narratives.router, tags=["narratives"])`

- [ ] Task 8: Tests (AC: all)
  - [ ] 8.1 Create `backend/tests/test_narratives.py`
  - [ ] 8.2 Test angle detection -- trend: provide DataFrame with clear linear trend in a numeric column paired with datetime. Verify trend angle detected with positive strength
  - [ ] 8.3 Test angle detection -- anomaly: provide DataFrame with outlier values >3 sigma. Verify anomaly angle detected
  - [ ] 8.4 Test angle detection -- composition: provide DataFrame with categorical column where one category dominates. Verify composition angle detected
  - [ ] 8.5 Test angle detection -- comparison: provide DataFrame with 2 correlated numeric columns. Verify comparison angle detected
  - [ ] 8.6 Test narrative generation: given detected angles and parsed answers, verify 2-3 narratives returned with non-empty narrative_text
  - [ ] 8.7 Test confidence scoring: verify `overall_confidence` is product of 3 factors, clamped to [0, 1]
  - [ ] 8.8 Test assumption extraction: verify EXPLICIT assumptions have confidence=1.0, PATTERN have 0.75, INFERRED have 0.40, no SPECULATIVE in output
  - [ ] 8.9 Test POST /generate-narratives endpoint: given valid deck with answered questions, verify narratives created in DB and returned
  - [ ] 8.10 Test POST /generate-narratives with no answered questions: verify 400 error
  - [ ] 8.11 Test GET /narratives endpoint: verify returns all narratives for deck, sorted by confidence
  - [ ] 8.12 Test GET /narratives with no narratives: verify returns empty list

## Dev Notes

### Previous Story Intelligence (from Stories 2.1 and 2.2)

**Established patterns to follow:**
- FastAPI async endpoints with `asyncio.to_thread` for CPU-bound synchronous work (use this for pandas/numpy statistical operations)
- SQLAlchemy async models in `backend/app/models/` with UUID primary keys, `server_default=func.now()` for timestamps
- Alembic migrations in `backend/alembic/versions/` with sequential numbering (next: 004)
- Tests in `backend/tests/` using `pytest-asyncio` with `httpx` `ASGITransport`
- Pydantic models in `backend/app/api/v1/schemas/`
- API router pattern: endpoints in `backend/app/api/v1/endpoints/`, register in `backend/app/api/v1/router.py`
- Auth deferred -- use `user_id` in request body as temporary approach
- `with_for_update()` for concurrent safety on state transitions
- Null-coalescing for optional JSONB fields: `field or {}`, `.get("key", default)`

**Review findings from Story 2.1:**
- Guard against unexpected status values with allowlist checks
- Question session `answers_json` shape (output from parser.py): `{ "parsed": [{ "question_id", "raw_answer", "parsed_intent", "confidence", "defaulted"? }], "ready_to_generate": bool }`
- Questions shape (from generator.py): `[{ "id", "template", "context", "suggestion_chips", "tier" }]`

### Existing Code State (files being modified)

**`backend/app/api/v1/router.py`** (MODIFY) -- Currently imports health, ingest, questions routers. Add narratives router import and include.

**`backend/app/models/__init__.py`** (MODIFY) -- Currently exports User, Deck, IngestJob, AuditLog, QuestionSession. Add Narrative.

**`backend/app/services/ingest/schema_detector.py`** (READ ONLY) -- Schema shape produced:
```python
{col_name: {"type": "numeric"|"datetime"|"text"|"boolean", "nullability": float, "cardinality": int, "date_format"?: str}}
```

**`backend/app/services/questions/parser.py`** (READ ONLY) -- Returns:
```python
{"parsed": [{"question_id": str, "raw_answer": str, "parsed_intent": str, "confidence": float, "defaulted"?: bool}], "ready_to_generate": bool}
```
Key intents: PROFIT, GROWTH, COST, MARKET, BOARD, INVESTORS, EXECUTIVE, OPERATIONS, DEFAULT, UNKNOWN.

**`backend/app/services/storage.py`** (READ ONLY) -- MinIO/S3 upload service. Reuse `boto3` client pattern for downloading files. Check how `file_url` is stored -- it's the S3 object key.

**`backend/app/models/ingest_job.py`** (READ ONLY) -- Fields needed: `file_url` (str, S3 key), `schema_json` (JSONB dict), `quality_report` (JSONB dict), `validated_at` (DateTime).

**`backend/app/models/question_session.py`** (READ ONLY) -- Fields needed: `deck_id`, `questions_json` (JSONB list), `answers_json` (JSONB dict with "parsed" and "ready_to_generate").

### Architecture Compliance

**API contracts (from Architecture Section 5):**
```
POST /api/v1/decks/{deck_id}/generate-narratives
  Trigger narrative generation from answered questions
  Returns: { narratives: [{ id, story_angle, narrative_text, viz_recommendation, assumptions, overall_confidence }] }

GET /api/v1/decks/{deck_id}/narratives
  Get generated narrative options
  Returns: { narratives: [{ id, story_angle, narrative_text, viz_recommendation, assumptions_json, overall_confidence }] }
```

**Database schema (from Architecture Section 4):**
```sql
CREATE TABLE narratives (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deck_id UUID REFERENCES decks NOT NULL,
  question_session_id UUID REFERENCES question_sessions NOT NULL,
  story_angle VARCHAR(50) NOT NULL,
  narrative_text TEXT NOT NULL,
  viz_recommendation JSONB,
  assumptions_json JSONB,
  overall_confidence FLOAT NOT NULL,
  created_at TIMESTAMP DEFAULT now()
);
```

**Narrative Engine (from Architecture Section 3.3 / FR10-FR13):**
- Template-based generation ONLY -- NO live LLM API calls
- Story angle detection via statistical analysis (numpy, not scipy)
- Confidence = data_completeness * angle_strength * user_intent_match
- Assumption flag types: EXPLICIT (1.0), PATTERN (0.75), INFERRED (0.40), SPECULATIVE (0.0 -- blocked)
- Performance target: < 2 seconds (NFR3)

**Data flow:**
```
IngestJob.file_url -> download from MinIO -> pd.DataFrame
IngestJob.schema_json -> dict (column types, cardinality, etc.)
QuestionSession.answers_json -> dict (parsed intents, confidence)
  |
  v
detect_angles(df, schema) -> [{ angle, column, strength, ... }]
  |
  v
generate_narratives(angles, answers, schema, df) -> [{ narrative_text, story_angle, viz_rec }]
  |
  v
extract_assumptions(narrative_text, angles, schema, df) -> [{ text, flag_type, confidence }]
compute_confidence(schema, df, angle, answers) -> float
  |
  v
Narrative rows saved to DB
```

### Technical Stack

- **Backend:** Python 3.11, FastAPI async, SQLAlchemy async, Alembic
- **Database:** PostgreSQL 15 with JSONB
- **Data processing:** pandas (already installed), numpy (transitive dependency via pandas)
- **Testing:** pytest + pytest-asyncio + httpx ASGITransport
- **No new pip dependencies needed** -- numpy comes with pandas; use numpy.polyfit for linear regression instead of scipy

### Directory Structure

```
backend/app/
  models/narrative.py (NEW)
  models/__init__.py (MODIFIED -- add Narrative)
  services/narratives/__init__.py (NEW)
  services/narratives/angle_detector.py (NEW)
  services/narratives/template_engine.py (NEW)
  services/narratives/assumption_extractor.py (NEW)
  services/narratives/data_loader.py (NEW)
  api/v1/endpoints/narratives.py (NEW)
  api/v1/schemas/narratives.py (NEW)
  api/v1/router.py (MODIFIED -- add narratives router)
backend/alembic/versions/004_add_narratives.py (NEW)
backend/tests/test_narratives.py (NEW)
```

### Anti-Patterns to Avoid

- Do NOT use LLM/AI for narrative generation -- this is template-based ONLY (FR11)
- Do NOT add scipy as a dependency -- use numpy.polyfit for regression, compute R-squared manually
- Do NOT add Celery/async job queue -- narrative generation is synchronous and must complete in < 2 seconds inline; use `asyncio.to_thread()` for CPU-bound pandas/numpy work
- Do NOT create frontend components -- Screen 2 (Narrative Picker) is Story 2.4
- Do NOT implement narrative selection/editing -- that's Story 2.4
- Do NOT include SPECULATIVE assumptions in output -- filter them out completely (FR13)
- Do NOT create a new database session pattern -- reuse `get_db` from `app.core.database`
- Do NOT hardcode metric names or data values in templates -- fill dynamically from the DataFrame
- Do NOT add Redis caching for narratives -- keep it simple for MVP
- Do NOT create a deck_selections table yet -- that's Story 2.4's responsibility (narrative selection + user edits)

### Testing Requirements

- Use same test infrastructure as previous stories: pytest-asyncio, httpx ASGITransport
- Test angle detection independently with synthetic DataFrames (create in-test DataFrames with known patterns)
- Test template engine with known angles and mock parsed answers
- Test assumption extraction: verify correct flag_type assignment
- Test confidence scoring: verify multiplicative formula and clamping
- Test endpoints: POST /generate-narratives with a complete flow (need ingest_job + question_session fixtures), GET /narratives for retrieval
- Test edge cases: no numeric columns (should still generate at least 1 narrative from categorical analysis), single-column DataFrame, DataFrame with all nulls in a column

### Project Structure Notes

- New service module at `backend/app/services/narratives/` mirrors the `backend/app/services/questions/` pattern
- New model at `backend/app/models/narrative.py` follows existing model patterns (UUID PK, JSONB fields, deck_id FK)
- Migration numbering continues at 004 (after 003_add_question_sessions.py)
- Endpoint and schema files follow existing naming conventions

### References

- [Source: epics.md#Story 2.3 -- Full acceptance criteria and user story]
- [Source: epics.md#FR10-FR13 -- Story angle detection, narrative generation, confidence scoring, assumption flagging]
- [Source: epics.md#NFR3 -- Narrative generation < 2 seconds]
- [Source: epics.md#Additional Requirements -- Template-based, no LLM; pandas; PostgreSQL JSONB]
- [Source: 2-1-question-generation-answer-parsing-service.md -- Established patterns, API contracts, data shapes]
- [Source: backend/app/services/questions/parser.py -- Parsed answer shapes (parsed_intent values, confidence, defaulted)]
- [Source: backend/app/services/questions/generator.py -- Question shapes (tier, suggestion_chips)]
- [Source: backend/app/services/ingest/schema_detector.py -- Schema shape (type, nullability, cardinality)]
- [Source: backend/app/services/storage.py -- MinIO/S3 client pattern for file download]
- [Source: backend/app/models/ingest_job.py -- file_url, schema_json, quality_report fields]
- [Source: backend/app/models/question_session.py -- answers_json JSONB field]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
