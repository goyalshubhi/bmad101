---
baseline_commit: 36a178dea281ebb691c3d94d82c147019174d98d
---

# Story 3.1: Figure Extraction & Reconciliation Checks Service

Status: done

## Story

As an analyst,
I want every number in my selected narrative automatically verified against the source data,
so that I know whether the deck's figures are accurate before it goes to leadership.

## Acceptance Criteria

1. **Given** a narrative has been selected (with or without user edits), **When** verification runs via `POST /api/v1/decks/{deck_id}/verify`, **Then** the system extracts every figure from the narrative text via regex (`\d+[.,]\d+%?`, `\$\d+[KMB]?`) and stores each with `{value, context_sentence, narrative_position}`.

2. **Given** figures are extracted, **When** the 5 reconciliation checks run, **Then** Check A (Sum-of-Parts) verifies component figures sum to reported totals ± 1%, **And** Check B (Data Consistency) traces each figure to source rows and verifies ± 0.1%, **And** Check C (Time Series Continuity) verifies no missing periods when narrative claims continuity, **And** Check D (Comparison Validity) verifies same dates in both periods for YoY/MoM claims, **And** Check E (Statistical Significance) verifies R² > 0.6 for any trend claims.

3. **Given** checks complete, **When** the reconciliation report is created, **Then** each check stores `{status: "pass"|"fail", expected, actual, fix_suggestion}` in `checks_json`, **And** each figure trace stores `{figure_value, source_rows, formula, match_status, variance_pct}` where `match_status` is `exact` (0%), `within_tolerance` (≤1%), or `mismatch` (>1%), **And** the report `passed` boolean is false if any check has `status: "fail"`, **And** reconciliation completes in < 1 second.

## Tasks / Subtasks

- [x] Task 1: Backend — ReconciliationReport model and migration (AC: #3)
  - [x] 1.1 Create `backend/app/models/reconciliation_report.py` — SQLAlchemy async model:
    - `id` (UUID PK, default uuid4)
    - `deck_id` (UUID FK -> decks.id, not null, indexed)
    - `narrative_id` (UUID FK -> narratives.id, not null, indexed)
    - `parent_report_id` (UUID FK -> reconciliation_reports.id, nullable) — for re-verify after fix (Story 3.3)
    - `checks_json` (JSONB, nullable) — shape: `{"check_a": {"status": "pass"|"fail", "expected": val, "actual": val, "fix_suggestion": str|null}, ...}`
    - `figure_traces` (JSONB, nullable) — shape: `[{"figure_value": str, "source_rows": str, "formula": str, "match_status": "exact"|"within_tolerance"|"mismatch", "variance_pct": float}]`
    - `assumption_actions_json` (JSONB, nullable, default null) — reserved for Story 3.4
    - `passed` (Boolean, not null)
    - `verified_at` (DateTime, server_default=func.now())
  - [x] 1.2 Register model in `backend/app/models/__init__.py` — add `ReconciliationReport` to imports and `__all__`
  - [x] 1.3 Create Alembic migration `backend/alembic/versions/006_add_reconciliation_reports.py` — creates `reconciliation_reports` table with indexes on `deck_id`, `narrative_id`, FK self-reference on `parent_report_id`

- [x] Task 2: Backend — Figure extraction service (AC: #1)
  - [x] 2.1 Create `backend/app/services/verify/__init__.py` (empty)
  - [x] 2.2 Create `backend/app/services/verify/figure_extractor.py`:
    - Function `extract_figures(narrative_text: str) -> list[dict]`
    - Regex patterns to match: `\$[\d,]+\.?\d*[KMB]?`, `\d+[.,]\d+%`, `\d{2,}[.,]\d+`, and standalone integers in numeric context
    - For each match, return `{"value": str, "context_sentence": str, "narrative_position": int}`
    - `context_sentence`: the full sentence containing the figure (split on `.` or `!` or `?`)
    - `narrative_position`: character offset of the figure in the narrative text
    - Deduplicate figures with same value appearing in same sentence

- [x] Task 3: Backend — Reconciliation checks service (AC: #2)
  - [x] 3.1 Create `backend/app/services/verify/reconciliation_checks.py`:
    - Function `run_all_checks(figures: list[dict], df: pd.DataFrame, narrative_text: str, schema: dict) -> dict`
    - Returns `{"check_a": {...}, "check_b": {...}, ..., "check_e": {...}}`
  - [x] 3.2 Implement Check A (Sum-of-Parts):
    - Identify groups of figures that appear to be components + total (heuristic: look for figures in same sentence or adjacent sentences where one ≈ sum of others)
    - Verify: sum of parts == total ± 1%
    - If no sum-of-parts pattern detected, status = "pass" (vacuously true)
    - `fix_suggestion`: "Recalculate total as sum of components" if fail
  - [x] 3.3 Implement Check B (Data Consistency):
    - For each extracted figure, attempt to trace to source data columns
    - Use column-matching heuristic: compare figure value against SUM, AVG, COUNT, MIN, MAX of numeric columns
    - If match found within ± 0.1%, status = "pass" for that figure
    - Return first figure that fails as the check's failure detail
    - `fix_suggestion`: "Exclude N rows with null/invalid entries" if nulls are likely cause
  - [x] 3.4 Implement Check C (Time Series Continuity):
    - Detect temporal claims in narrative (keywords: "quarters", "months", "years", "consecutive", "continuous", "growing N periods")
    - If datetime column exists in df, verify no gaps in the detected period range
    - If no temporal claims, status = "pass"
    - `fix_suggestion`: "Data has gaps in [period]. Consider noting data limitations."
  - [x] 3.5 Implement Check D (Comparison Validity):
    - Detect comparison claims (keywords: "YoY", "MoM", "year-over-year", "month-over-month", "compared to", "vs", "versus")
    - If datetime column exists, verify both comparison periods have data rows
    - If no comparison claims, status = "pass"
    - `fix_suggestion`: "Period X has no data — comparison invalid"
  - [x] 3.6 Implement Check E (Statistical Significance):
    - Detect trend claims (keywords: "trend", "growing", "declining", "increasing", "decreasing", "consistent")
    - If trend claim found AND numeric + datetime columns exist, fit linear regression and compute R²
    - Pass if R² > 0.6, fail if R² ≤ 0.6
    - If no trend claims, status = "pass"
    - `fix_suggestion`: "R²={value} — trend claim is statistically weak. Consider softening language."
    - Use `numpy.polyfit` or `scipy.stats.linregress` (prefer numpy since already a pandas dependency)

- [x] Task 4: Backend — Figure tracing service (AC: #3)
  - [x] 4.1 Create `backend/app/services/verify/figure_tracer.py`:
    - Function `trace_figures(figures: list[dict], df: pd.DataFrame, schema: dict) -> list[dict]`
    - For each extracted figure, attempt to match against source data aggregations
    - Return `{"figure_value": str, "source_rows": str, "formula": str, "match_status": "exact"|"within_tolerance"|"mismatch", "variance_pct": float}`
    - `source_rows`: row range string like "1-847" or "12-340"
    - `formula`: detected operation like "SUM(column_name)" or "AVG(column_name)"
    - Tolerance thresholds: `exact` = 0%, `within_tolerance` = ≤1%, `mismatch` = >1%

- [x] Task 5: Backend — Verify endpoint (AC: #1, #2, #3)
  - [x] 5.1 Create `backend/app/api/v1/endpoints/verify.py`:
    - `POST /api/v1/decks/{deck_id}/verify` endpoint
    - Fetch the DeckSelection for this deck (404 if none)
    - Fetch the selected Narrative (use `user_edits_text` from DeckSelection if present, else `narrative_text` from Narrative)
    - Fetch the validated IngestJob for the deck (400 if none)
    - Run in `asyncio.to_thread`:
      1. Load DataFrame via `data_loader.load_dataframe(job.file_url)`
      2. Extract figures via `figure_extractor.extract_figures(text)`
      3. Run checks via `reconciliation_checks.run_all_checks(figures, df, text, schema)`
      4. Trace figures via `figure_tracer.trace_figures(figures, df, schema)`
    - Create ReconciliationReport row with results
    - Create audit_log entry: action="verification_run"
    - Return response
  - [x] 5.2 Create Pydantic schemas in `backend/app/api/v1/schemas/verify.py`:
    - `FigureTrace`: `{figure_value: str, source_rows: str, formula: str, match_status: str, variance_pct: float}`
    - `CheckResult`: `{status: str, expected: Any = None, actual: Any = None, fix_suggestion: str | None = None}`
    - `VerifyResponse`: `{report_id: str, deck_id: str, narrative_id: str, passed: bool, checks: dict[str, CheckResult], figure_traces: list[FigureTrace]}`
  - [x] 5.3 Register verify router in `backend/app/api/v1/router.py`:
    - Add `from app.api.v1.endpoints import verify`
    - Add `api_router.include_router(verify.router, tags=["verify"])`

- [x] Task 6: Backend — Tests (AC: #1, #2, #3)
  - [x] 6.1 Create `backend/tests/test_figure_extractor.py`:
    - Test regex extracts dollar amounts, percentages, large numbers
    - Test context_sentence extraction
    - Test deduplication
  - [x] 6.2 Create `backend/tests/test_reconciliation_checks.py`:
    - Test each check (A-E) with pass and fail cases
    - Test vacuous pass when no relevant pattern detected
  - [x] 6.3 Create `backend/tests/test_verify_endpoint.py`:
    - Test POST /verify returns report with checks and figure traces
    - Test 404 when no narrative selected
    - Test 400 when no validated ingest job
    - Test `passed` is false when any check fails

## Dev Notes

### Epic 3 Cross-Story Shared Components

**IMPORTANT: The following components are shared across Stories 3.1-3.4. Build them once in this story so later stories reuse, not duplicate.**

1. **ReconciliationReport model** (Task 1) — Used by Stories 3.1, 3.3 (apply-fix creates new report with parent_report_id), 3.4 (assumption_actions_json)
2. **`backend/app/services/verify/` module** — All verify service code lives here. Stories 3.2-3.4 add endpoints but reuse these services
3. **`backend/app/api/v1/endpoints/verify.py`** — Single router file for ALL verify endpoints. Story 3.3 adds `apply-fix`, `dismiss-check`; Story 3.4 adds `assumption-action`
4. **`backend/app/api/v1/schemas/verify.py`** — Single schema file for ALL verify schemas. Stories 3.3-3.4 extend with additional request/response models
5. **Figure extractor and tracer** — Reused by Story 3.3's re-verify flow (apply-fix re-extracts figures from filtered data)
6. **`data_loader.load_dataframe()`** — Already exists in `backend/app/services/narratives/data_loader.py`. Reuse it, do NOT create a duplicate

### Previous Story Intelligence (from Story 2.4)

**Established patterns to follow:**
- SQLAlchemy async models with UUID PKs, `server_default=func.now()`
- Alembic migrations sequential numbering (next migration: **006**)
- `asyncio.to_thread()` for CPU-bound work (Pandas, numpy operations)
- `with_for_update()` for concurrent safety on state mutations
- Auth deferred — no user_id validation on endpoints
- Null-coalescing for JSONB: `field or {}`, `.get("key", default)`

**Review fixes from Story 2.4 to apply proactively:**
- Always add double-click guard on async operations: `if (submitting) return`
- Don't return null for empty states — show user-friendly errors
- Use `with_for_update()` on reads that precede writes
- Handle `IntegrityError` on upserts with retry pattern

### Architecture Compliance

**API contract for this story (NEW):**
```
POST /api/v1/decks/{deck_id}/verify
  Prereqs: DeckSelection must exist (narrative selected on Screen 2)
  Process: extract figures → run 5 checks → trace figures → store report
  Returns: {
    report_id: str,
    deck_id: str,
    narrative_id: str,
    passed: bool,
    checks: {
      check_a: {status, expected?, actual?, fix_suggestion?},
      check_b: {...},
      check_c: {...},
      check_d: {...},
      check_e: {...}
    },
    figure_traces: [{figure_value, source_rows, formula, match_status, variance_pct}]
  }
```

**Endpoints this story does NOT implement (deferred to Stories 3.3-3.4):**
- `POST /api/v1/decks/{deck_id}/verify/apply-fix` → Story 3.3
- `POST /api/v1/decks/{deck_id}/verify/dismiss-check` → Story 3.3
- `POST /api/v1/decks/{deck_id}/verify/assumption-action` → Story 3.4

**Database schema per architecture Section 3.4 and Section 12 (Gap Resolutions):**
- `reconciliation_reports` table matches architecture Section 4 exactly
- `checks_json` uses the extended object shape from Gap 2 resolution (not boolean)
- `figure_traces` includes `match_status` and `variance_pct` per Gap 4 resolution
- `assumption_actions_json` column is created but left null (populated by Story 3.4)
- Tolerance thresholds: exact=0%, within_tolerance=≤1%, mismatch=>1% (Gap 4)

**Data flow:**
```
DeckSelection (from Story 2.4)
  → narrative_id → Narrative.narrative_text (or DeckSelection.user_edits_text if edited)
  → IngestJob.file_url → load DataFrame
  → extract figures from narrative text
  → run 5 checks against DataFrame
  → trace each figure to source rows
  → store ReconciliationReport
```

### Technical Requirements

**Dependencies (already installed — no new packages):**
- `pandas` — DataFrame operations, already used by narrative services
- `numpy` — `numpy.polyfit` for linear regression in Check E (transitive dep of pandas)
- `re` — regex for figure extraction (stdlib)

**Reuse existing code:**
- `backend/app/services/narratives/data_loader.py` → `load_dataframe(object_key)` — import directly, do NOT copy
- `backend/app/core/database.py` → `get_db`, `Base` — same patterns as all prior models
- `backend/app/models/audit_log.py` → `AuditLog` model for logging verification actions

### File Structure

```
backend/app/
  models/reconciliation_report.py (NEW)
  models/__init__.py (MODIFIED — add ReconciliationReport)
  services/verify/__init__.py (NEW, empty)
  services/verify/figure_extractor.py (NEW)
  services/verify/reconciliation_checks.py (NEW)
  services/verify/figure_tracer.py (NEW)
  api/v1/endpoints/verify.py (NEW)
  api/v1/schemas/verify.py (NEW)
  api/v1/router.py (MODIFIED — add verify router)
backend/alembic/versions/006_add_reconciliation_reports.py (NEW)
backend/tests/test_figure_extractor.py (NEW)
backend/tests/test_reconciliation_checks.py (NEW)
backend/tests/test_verify_endpoint.py (NEW)
```

### Anti-Patterns to Avoid

- Do NOT implement Screen 3 UI — that's Story 3.2
- Do NOT implement apply-fix, dismiss-check, or assumption-action endpoints — those are Stories 3.3 and 3.4
- Do NOT create a new data_loader — import from `app.services.narratives.data_loader`
- Do NOT use CSS files or frontend code — this is a backend-only story
- Do NOT hardcode figure values in tests — use parameterized data
- Do NOT make Check E fail when no trend claims exist — return "pass" (vacuous truth)
- Do NOT add dismissed_reason, dismissed_by, dismissed_at fields to checks_json yet — Story 3.3 will add those when the dismiss endpoint is implemented; for now checks_json only has `{status, expected, actual, fix_suggestion}`
- Do NOT block on SPECULATIVE assumption handling — that's filtered at narrative generation time (Story 2.3)

### Testing Requirements

- Unit tests for figure_extractor: various narrative texts with dollar amounts, percentages, mixed formats
- Unit tests for reconciliation_checks: each check with synthetic DataFrames — pass and fail scenarios
- Integration test for POST /verify endpoint: mock DB with DeckSelection + Narrative + IngestJob, verify response shape
- Performance: verify reconciliation completes in < 1 second for a 100k-row DataFrame (assert on timing in test)

### References

- [Source: epics.md#Story 3.1 — Full acceptance criteria and user story]
- [Source: epics.md#FR14-FR17 — Figure extraction and reconciliation requirements]
- [Source: ARCHITECTURE-Technical-Design.md#Section 3.4 — Verify Service process and data model]
- [Source: ARCHITECTURE-Technical-Design.md#Section 4 — reconciliation_reports table schema]
- [Source: ARCHITECTURE-Technical-Design.md#Section 5 — API design (POST /verify, apply-fix, dismiss-check, assumption-action)]
- [Source: ARCHITECTURE-Technical-Design.md#Section 12 — Gap resolutions 1-5 (assumption_actions_json, checks_json shape, per-figure match_status)]
- [Source: 2-4-narrative-picker-screen.md — Established patterns: SQLAlchemy async, Alembic 006, asyncio.to_thread]
- [Source: backend/app/models/deck_selection.py — DeckSelection model (consumed by verify endpoint)]
- [Source: backend/app/models/narrative.py — Narrative model (narrative_text, assumptions_json)]
- [Source: backend/app/services/narratives/data_loader.py — load_dataframe() to reuse]
- [Source: backend/app/api/v1/router.py — Router registration pattern]
- [Source: EXPERIENCE.md#Screen 3 — UX data flow and component behavior]

## Dev Agent Record

### Agent Model Used
Claude Sonnet 4.6

### Debug Log References
- All 33 new tests pass (13 figure_extractor, 10 reconciliation_checks, 4 verify_endpoint, 6 integration)
- 19 pre-existing test_narratives.py failures confirmed unrelated (AttributeError in angle_detector.py — tests pass wrong schema type)
- Zero regressions introduced

### Completion Notes List
- Task 1: Created ReconciliationReport model with all specified fields (UUID PK, FKs to decks/narratives/self, JSONB for checks/traces/assumptions, Boolean passed, DateTime verified_at). Alembic migration 006 with proper indexes.
- Task 2: Figure extractor with 4 regex patterns ($amounts, percentages, large decimals, standalone integers). Deduplication by (value, sentence) pair. Context sentence extraction via sentence splitting.
- Task 3: All 5 reconciliation checks implemented — Sum-of-Parts (combinatorial search ±1%), Data Consistency (SUM/AVG/COUNT/MIN/MAX ±0.1%), Time Series Continuity (gap detection via freq inference), Comparison Validity (multi-period verification), Statistical Significance (numpy polyfit R² > 0.6). All return vacuous pass when no relevant claims detected.
- Task 4: Figure tracer matches figures against column aggregations, reports match_status (exact/within_tolerance/mismatch) and variance_pct. Falls back to direct value matching in columns.
- Task 5: POST /api/v1/decks/{deck_id}/verify endpoint using asyncio.to_thread for CPU-bound work. Reuses data_loader.load_dataframe from narratives service. Proper 404/400 error handling.
- Task 6: 33 tests — unit tests for extractor (dollar, percentage, large numbers, context, dedup, mixed), reconciliation checks (each check A-E pass/fail/vacuous), endpoint integration (success, 404, 400, passed=false).
- Note: Audit log entry creation was omitted from endpoint because AuditLog requires user_id (FK to users) and auth is deferred — no user context available. This can be added when auth is implemented.

### File List
- backend/app/models/reconciliation_report.py (NEW)
- backend/app/models/__init__.py (MODIFIED)
- backend/alembic/versions/006_add_reconciliation_reports.py (NEW)
- backend/app/services/verify/__init__.py (NEW)
- backend/app/services/verify/figure_extractor.py (NEW)
- backend/app/services/verify/reconciliation_checks.py (NEW)
- backend/app/services/verify/figure_tracer.py (NEW)
- backend/app/api/v1/endpoints/verify.py (NEW)
- backend/app/api/v1/schemas/verify.py (NEW)
- backend/app/api/v1/router.py (MODIFIED)
- backend/tests/test_figure_extractor.py (NEW)
- backend/tests/test_reconciliation_checks.py (NEW)
- backend/tests/test_verify_endpoint.py (NEW)

### Review Findings

- [x] [Review][Decision] Missing audit_log entry (action="verification_run") — Resolved: made AuditLog.user_id nullable (migration 007), endpoint now creates audit entry with user_id=None
- [x] [Review][Decision] Figure extraction regex deviates from AC spec patterns — Resolved: kept broader patterns with exclusion heuristics (filter years 1900-2099, short numbers)
- [x] [Review][Patch] Combinatorial explosion in Check A — O(2^N) with no figure count cap [reconciliation_checks.py:61-78] — Fixed: cap at 15 figures
- [x] [Review][Patch] `_parse_numeric` strips `%` but treats result as absolute number — Fixed: percentages excluded from Check A/B via `is_percentage()` helper
- [x] [Review][Patch] No error handling around `load_dataframe` / `np.polyfit` — Fixed: try/except in endpoint + np.polyfit catch
- [x] [Review][Patch] Negative numbers never extracted by regex and silently excluded from checks — Fixed: regex now supports leading `-`, Check B uses `!= 0` instead of `> 0`
- [x] [Review][Patch] Check B early-returns on first unmatched figure, ignoring remaining figures — Fixed: collects first failure but continues checking all figures
- [x] [Review][Patch] `_find_sentence` uses `text.find` which can mislocate repeated sentences — Fixed: improved offset tracking
- [x] [Review][Patch] Regex `(?<!\d)\d{3,}(?!\d)` matches years, zip codes, non-financial numbers — Fixed: added `_is_likely_non_financial` exclusion filter
- [x] [Review][Patch] Duplicated `_parse_numeric` in reconciliation_checks.py and figure_tracer.py — Fixed: extracted to shared `numeric_parser.py`
- [x] [Review][Patch] `flush()` before `commit()` is redundant; no rollback handler on failure — Fixed: removed flush(), commit() only
- [x] [Review][Patch] Empty narrative text passes all checks with `passed=True` and zero figures — Fixed: 400 error on empty narrative
- [x] [Review][Patch] Timezone-aware vs naive datetimes can crash `sort_values()` in Check C/D — Fixed: try/except TypeError around sort_values()
- [x] [Review][Patch] Non-integer DataFrame index breaks row number reporting in figure tracer — Fixed: safe index conversion with isinstance check
- [x] [Review][Defer] No idempotency — repeated POST creates duplicate reports [verify.py:68-78] — deferred, pre-existing pattern
- [x] [Review][Defer] No rate limiting on expensive verify endpoint [verify.py:24] — deferred, cross-cutting concern
- [x] [Review][Defer] Check A passes when no sum relationship found (fabricated totals pass vacuously) [reconciliation_checks.py:80] — deferred, spec-intended vacuous truth
- [x] [Review][Defer] `infer_datetime_format` deprecated in pandas 2.x [data_loader.py] — deferred, pre-existing in data_loader

### Change Log
- 2026-06-20: Implemented Story 3.1 — Figure Extraction & Reconciliation Checks Service. Added ReconciliationReport model, figure extractor, 5 reconciliation checks (A-E), figure tracer, POST /verify endpoint, Pydantic schemas, and 33 tests (all passing).
