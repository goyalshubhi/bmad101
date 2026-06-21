---
baseline_commit: 1dc3933fe26c6e430c6674907e473e2815019b28
---

# Story 2.1: Question Generation & Answer Parsing Service

Status: review

## Story

As an analyst,
I want the system to generate targeted questions based on my data structure and parse my answers with confidence scoring,
so that the system understands my intent before generating narratives.

## Acceptance Criteria

1. **Given** a validated ingest job with schema_json and quality_report, **When** I call `GET /api/v1/decks/{deck_id}/questions`, **Then** the system returns 4-5 questions generated from templates based on detected data patterns (multiple numeric columns -> headline metric question, temporal + numeric -> comparison period question, mixed deltas -> priority question, high cardinality -> top-N question, data gaps -> fill/exclude question), **And** questions are prioritized: Tier 1 (primary metric, audience) always included, Tier 2 (conflicting signals, data gaps) included only if ambiguous, **And** each question includes `{id, template, context, suggestion_chips}` where chips are derived from column names and detected patterns, **And** a `question_sessions` row is created with `questions_json`, **And** generation completes in < 500ms.

2. **Given** the user submits free-text answers via `POST /api/v1/decks/{deck_id}/answer-questions`, **When** the rule-based parser processes each answer, **Then** each answer returns `{question_id, raw_answer, parsed_intent, confidence}` using keyword matching (profit/margin -> PROFIT 0.9, revenue/sales -> GROWTH 0.85, etc.), **And** the response includes `ready_to_generate: true` when all Tier 1 questions are answered or skipped, **And** the `question_sessions` row is updated with `answers_json`.

## Tasks / Subtasks

- [x] Task 1: Database model and migration for question_sessions (AC: #1, #2)
  - [x] 1.1 Create `backend/app/models/question_session.py` — SQLAlchemy async model matching architecture schema: `id` (UUID PK), `deck_id` (UUID FK->decks), `version` (INT default 1), `questions_json` (JSONB), `answers_json` (JSONB), `parent_session_id` (UUID FK->self, nullable), `created_at` (DateTime)
  - [x] 1.2 Register model in `backend/app/models/__init__.py`
  - [x] 1.3 Create Alembic migration `backend/alembic/versions/003_add_question_sessions.py` — creates `question_sessions` table with index on `deck_id`

- [x] Task 2: Question generation service (AC: #1)
  - [x] 2.1 Create `backend/app/services/questions/__init__.py`
  - [x] 2.2 Create `backend/app/services/questions/generator.py` — `generate_questions(schema: dict, quality_report: dict) -> list[dict]`
    - Input: `schema_json` from ingest_job (shape: `{col_name: {type, nullability, cardinality, date_format?}}`)
    - Input: `quality_report` from ingest_job (shape: `{issues: [...], status: str}`)
    - Detect data patterns from schema:
      - Count numeric columns -> if >=2, add "headline metric" question (Tier 1)
      - Check for datetime + numeric combo -> add "comparison period" question (Tier 2)
      - Check cardinality >1000 on any column -> add "top-N" question (Tier 2)
      - Check quality_report for missing data >5% -> add "fill/exclude" question (Tier 2)
      - Always add "audience" question (Tier 1)
    - Each question: `{id: str, template: str, context: str, suggestion_chips: list[str], tier: int}`
    - Chips derived from column names in schema (e.g., numeric column names as suggestions for headline metric)
    - Return 4-5 questions, Tier 1 first

- [x] Task 3: Answer parsing service (AC: #2)
  - [x] 3.1 Create `backend/app/services/questions/parser.py` — `parse_answers(questions: list[dict], answers: list[dict]) -> dict`
    - For each answer, apply rule-based keyword matching:
      - `profit|margin|profitability` -> `(PROFIT, 0.9)`
      - `revenue|sales|growth` -> `(GROWTH, 0.85)`
      - `cost|spending|efficiency` -> `(COST, 0.9)`
      - `market|share|position` -> `(MARKET, 0.8)`
      - `board|directors|governance` -> `(BOARD, 0.9)`
      - `investors|shareholders` -> `(INVESTORS, 0.85)`
      - `executive|leadership|c-suite` -> `(EXECUTIVE, 0.85)`
      - `operations|ops|team` -> `(OPERATIONS, 0.8)`
    - Use regex matching, case-insensitive
    - If no keyword match or ambiguous: confidence = 0.5 (triggers follow-up on frontend)
    - Return per answer: `{question_id, raw_answer, parsed_intent, confidence}`
    - Compute `ready_to_generate`: true if all Tier 1 questions have answers (not skipped or have confidence >= 0.0)
    - Handle `skip` answers: set `parsed_intent` to system default, mark `defaulted: true`

- [x] Task 4: API endpoints (AC: #1, #2)
  - [x] 4.1 Create `backend/app/api/v1/endpoints/questions.py` with router
  - [x] 4.2 `GET /decks/{deck_id}/questions` endpoint:
    - Fetch latest ingest_job for deck_id (must have `validated_at` set — return 400 if not validated)
    - Call `generate_questions(schema_json, quality_report)`
    - Create `question_sessions` row with `questions_json`
    - Return `{session_id, questions: [...]}` — generation must complete in < 500ms
  - [x] 4.3 `POST /decks/{deck_id}/answer-questions` endpoint:
    - Request body: `{session_id: UUID, answers: [{question_id: str, text: str}]}`
    - Fetch question_session by session_id (404 if not found)
    - Call `parse_answers(questions_json, answers)`
    - Update question_session.answers_json
    - Return `{parsed: [{question_id, raw_answer, parsed_intent, confidence}], ready_to_generate: bool}`
  - [x] 4.4 Create `backend/app/api/v1/schemas/questions.py` — Pydantic models:
    - `QuestionResponse`: `{id, template, context, suggestion_chips: list[str], tier: int}`
    - `QuestionsListResponse`: `{session_id: str, questions: list[QuestionResponse]}`
    - `AnswerInput`: `{question_id: str, text: str}`
    - `AnswerSubmitRequest`: `{session_id: UUID, answers: list[AnswerInput]}`
    - `ParsedAnswer`: `{question_id: str, raw_answer: str, parsed_intent: str, confidence: float}`
    - `AnswerSubmitResponse`: `{parsed: list[ParsedAnswer], ready_to_generate: bool}`
  - [x] 4.5 Register questions router in `backend/app/api/v1/router.py`

- [x] Task 5: Tests (AC: #1, #2)
  - [x] 5.1 Create `backend/tests/test_questions.py`
  - [x] 5.2 Test question generation: given a schema with 3 numeric cols + 1 datetime col, verify 4-5 questions returned with correct tiers and chips
  - [x] 5.3 Test question generation with minimal schema (1 col): verify Tier 1 questions still generated
  - [x] 5.4 Test answer parsing: "Focus on profit margins" -> PROFIT, confidence 0.9
  - [x] 5.5 Test answer parsing: ambiguous answer "maybe the numbers" -> confidence < 0.7
  - [x] 5.6 Test answer parsing: skip answer handling -> defaulted intent
  - [x] 5.7 Test GET /questions endpoint: verify session created, questions returned, 400 if not validated
  - [x] 5.8 Test POST /answer-questions endpoint: verify answers parsed, session updated, ready_to_generate computed
  - [x] 5.9 Test POST /answer-questions with invalid session_id: 404

## Dev Notes

### Previous Story Intelligence (from Story 1.4)

**Established patterns to follow:**
- FastAPI async endpoints with `asyncio.to_thread` for synchronous I/O
- SQLAlchemy async models in `backend/app/models/` with UUID primary keys, `server_default=func.now()` for timestamps
- Alembic migrations in `backend/alembic/versions/` with sequential numbering (001, 002, 003...)
- Tests in `backend/tests/` using `pytest-asyncio` with `httpx` `ASGITransport`
- Pydantic models in `backend/app/api/v1/schemas/` — use `model_config = {"populate_by_name": True}` and `Field(alias=...)` for reserved names like "schema"
- API router pattern: endpoints in `backend/app/api/v1/endpoints/`, register in `backend/app/api/v1/router.py`
- Auth deferred — use `user_id` in request body as temporary approach (same as Story 1.4)
- `with_for_update()` for concurrent safety on state transitions

**Review findings from Story 1.4:**
- Guard against unexpected status values — add allowlist checks
- Handle null-coalescing for optional JSONB fields (e.g., `quality_report.get("issues", [])`)
- No 404 catch-all route exists in React Router yet (deferred)
- Content-Type header forced to JSON on all requests in `client.ts` (will need fix for FormData in future)

### Existing Code State (files being modified)

**`backend/app/api/v1/router.py`** — Currently imports health and ingest routers. Add questions router import and include.

**`backend/app/models/__init__.py`** — Currently exports User, Deck, IngestJob, AuditLog. Add QuestionSession.

**`backend/app/api/v1/endpoints/ingest.py`** — READ ONLY. The GET /ingest-status endpoint (line 81-101) is used by the questions endpoint to check validation state. Reuse the same query pattern: `select(IngestJob).where(IngestJob.deck_id == deck_id).order_by(IngestJob.created_at.desc())`.

**`backend/app/models/ingest_job.py`** — READ ONLY. Fields used: `schema_json` (JSONB dict), `quality_report` (JSONB dict), `validated_at` (DateTime, nullable). Check `validated_at is not None` before generating questions.

### Architecture Compliance

**API contracts** (from Architecture Section 5):
```
GET /api/v1/decks/{deck_id}/questions
  Get 4-5 questions based on data
  Returns: {questions: [{id, template, context}]}

POST /api/v1/decks/{deck_id}/answer-questions
  Submit free-text answers
  Payload: {answers: [{question_id, text}]}
  Returns: {parsed: [{question_id, intent, confidence}], ready_to_generate: bool}
```

**Database schema** (from Architecture Section 4):
```sql
CREATE TABLE question_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deck_id UUID REFERENCES decks NOT NULL,
  version INT DEFAULT 1,
  questions_json JSONB,
  answers_json JSONB,
  parent_session_id UUID REFERENCES question_sessions,
  created_at TIMESTAMP DEFAULT now()
);
```

**Question Engine** (from Architecture Section 3.2):
- Template-based generation, NOT LLM
- Rule-based parsing with keyword matching
- Confidence < 0.7 triggers clarifying follow-up (handled by frontend in Story 2.2)
- Tier 1 always asked, Tier 2 only if ambiguous
- Performance target: < 500ms for generation (NFR2)

**Schema shape** (from `schema_detector.py`):
```python
{col_name: {"type": "numeric"|"datetime"|"text"|"boolean", "nullability": float, "cardinality": int, "date_format"?: str}}
```

**Quality report shape** (from `quality_checker.py`):
```python
{"issues": [{"severity": str, "description": str, "count": int, "sample_rows": list[int]}], "status": "CLEAN"|"ISSUES_BLOCKING"|"ISSUES_ACKNOWLEDGED"}
```

### Technical Stack

- **Backend:** Python 3.11, FastAPI async, SQLAlchemy async, Alembic
- **Database:** PostgreSQL 15 with JSONB
- **Testing:** pytest + pytest-asyncio + httpx ASGITransport
- **No new dependencies needed** — all keyword matching is pure Python regex

### Directory Structure

```
backend/app/
  models/question_session.py (NEW)
  models/__init__.py (MODIFIED — add QuestionSession)
  services/questions/__init__.py (NEW)
  services/questions/generator.py (NEW)
  services/questions/parser.py (NEW)
  api/v1/endpoints/questions.py (NEW)
  api/v1/schemas/questions.py (NEW)
  api/v1/router.py (MODIFIED — add questions router)
backend/alembic/versions/003_add_question_sessions.py (NEW)
backend/tests/test_questions.py (NEW)
```

### Anti-Patterns to Avoid

- Do NOT use LLM/AI for question generation — this is template-based only
- Do NOT create frontend components — that's Story 2.2
- Do NOT implement the narrative generation service — that's Story 2.3
- Do NOT add Redis caching for question history yet — keep it simple for MVP
- Do NOT create a new database session pattern — reuse `get_db` from `app.core.database`
- Do NOT add Celery/async job queue — question generation is synchronous and must complete in < 500ms
- Do NOT hardcode column names — derive suggestions from the schema_json dynamically
- Do NOT create a separate router file — follow the pattern of one router per endpoint file with `router = APIRouter()`

### Testing Requirements

- Use same test infrastructure as Story 1.4: pytest-asyncio, httpx ASGITransport
- Test question generation with varied schemas (many numeric cols, few cols, no datetime, high cardinality)
- Test parser with clear keywords, ambiguous text, empty answers, skip markers
- Test endpoint flow: validated ingest -> get questions -> submit answers -> verify session updated
- Test guard: GET /questions on a deck with no validated ingest_job returns 400

### UX Requirements (for later stories)

Story 2.2 will consume these endpoints for Screen 1 (Clarifying Questions). Key data contracts the frontend will expect:
- Questions list with suggestion_chips for pre-filling
- Parsed answers with confidence scores for confidence badges (green >= 70%, amber < 70%)
- `ready_to_generate` flag to enable/disable "Generate Narratives" button

### References

- [Source: epics.md#Story 2.1 — Acceptance Criteria and full story definition]
- [Source: ARCHITECTURE-Technical-Design.md#Section 3.2 — Question Engine: generation, parsing, data model]
- [Source: ARCHITECTURE-Technical-Design.md#Section 4 — Database Schema: question_sessions table]
- [Source: ARCHITECTURE-Technical-Design.md#Section 5 — API Design: GET questions, POST answer-questions]
- [Source: EXPERIENCE.md — Screen 1: question cards, suggestion chips, confidence badges, data context strip]
- [Source: 1-4-data-validation-review-sign-off.md — Established patterns, review findings]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6

### Debug Log References

No issues encountered during implementation.

### Completion Notes List

- Task 1: Created QuestionSession model with all architecture-specified fields (UUID PK, deck_id FK, version, questions_json JSONB, answers_json JSONB, parent_session_id self-FK, created_at). Registered in models/__init__.py. Migration 003 creates table with deck_id index.
- Task 2: Implemented template-based question generator. Detects data patterns from schema (numeric count, datetime+numeric combos, high cardinality, data gaps). Produces 4-5 questions with Tier 1 first. Suggestion chips derived dynamically from column names.
- Task 3: Implemented rule-based answer parser with 8 keyword patterns using regex. Handles skip/empty answers with defaulted intent. Computes ready_to_generate based on Tier 1 coverage.
- Task 4: Created GET /decks/{deck_id}/questions and POST /decks/{deck_id}/answer-questions endpoints. Validates ingest job exists and is validated before generating questions. Created all Pydantic schemas. Registered router.
- Task 5: Wrote 15 tests covering generator (rich schema, minimal schema, high cardinality, data gaps), parser (profit keyword, growth keyword, ambiguous, skip, empty, ready_to_generate logic), and endpoints (GET questions, 400 not validated, POST answers, 404 invalid session). All 52 project tests pass with zero regressions.

### File List

- backend/app/models/question_session.py (NEW)
- backend/app/models/__init__.py (MODIFIED)
- backend/alembic/versions/003_add_question_sessions.py (NEW)
- backend/app/services/questions/__init__.py (NEW)
- backend/app/services/questions/generator.py (NEW)
- backend/app/services/questions/parser.py (NEW)
- backend/app/api/v1/endpoints/questions.py (NEW)
- backend/app/api/v1/schemas/questions.py (NEW)
- backend/app/api/v1/router.py (MODIFIED)
- backend/tests/test_questions.py (NEW)

### Change Log

- 2026-06-19: Implemented Story 2.1 — Question Generation & Answer Parsing Service. Added QuestionSession model, template-based question generator, rule-based answer parser, two API endpoints (GET questions, POST answer-questions), Pydantic schemas, Alembic migration, and 15 tests.
