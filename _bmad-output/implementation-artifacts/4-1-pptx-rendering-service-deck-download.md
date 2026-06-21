---
baseline_commit: 36a178dea281ebb691c3d94d82c147019174d98d
---

# Story 4.1: PPTX Rendering Service & Deck Download

Status: done

## Story

As an analyst,
I want my verified narrative rendered into a structured PPTX deck that I can download and present,
so that I have a boardroom-ready deliverable within minutes of uploading my data.

## Acceptance Criteria

1. **Given** all verification checks are resolved and "Proceed to Render" was clicked, **When** the render service runs via `POST /api/v1/decks/{deck_id}/render`, **Then** python-pptx generates a PPTX file with this slide structure:
   - Slide 1: Title (deck name, date, data source filename)
   - Slide 2: Executive Summary (1-2 sentence narrative from selected narrative_text)
   - Slides 3-N: Data visualizations (chart placeholder + data table per viz_recommendation)
   - Slide N+1: Assumptions & Inference Flags (bulleted list from assumptions_json with flag type labels)
   - Slide N+2: Q&A (questions asked + answers given from question_sessions)
   - Final Slide: Appendix (data quality notes from quality_report, reconciliation status summary, verification timestamp)

2. **Given** the PPTX is generated, **When** metadata is embedded, **Then** each slide includes narrative_confidence and assumptions_count in slide notes, **And** footnotes appear on data slides for any data limitations (e.g., "Based on Q1-Q3 data; Q4 not available").

3. **Given** rendering completes, **When** the output is stored, **Then** a deck_outputs row is created with version number and pptx_url (MinIO/S3 signed URL), **And** an audit_log entry records `deck_rendered` with deck_id, version, user_id, timestamp, **And** rendering completes in < 1 second.

4. **Given** the user is on Screen 3 (read-only mode post-render), **When** they click [Download PPTX], **Then** the browser downloads the generated PPTX file, **And** the progress rail shows "Render ✓" as the final completed step.

## Tasks / Subtasks

- [x] Task 1: Backend -- DeckOutput model + Alembic migration (AC: #3)
  - [x] 1.1 Create `backend/app/models/deck_output.py`:
    - `id: UUID` primary key (default uuid4)
    - `deck_id: UUID` FK to decks.id, nullable=False, indexed
    - `version: int` (Integer, nullable=False)
    - `pptx_url: str | None` (String, nullable=True) -- S3/MinIO object key
    - `rendered_at: datetime` (DateTime, server_default=func.now())
    - `created_at: datetime` (DateTime, server_default=func.now())
  - [x] 1.2 Add `DeckOutput` to `backend/app/models/__init__.py` imports and `__all__`
  - [x] 1.3 Create Alembic migration `008_add_deck_outputs.py`:
    - Create `deck_outputs` table with all columns above
    - Add index on `deck_id`

- [x] Task 2: Backend -- python-pptx dependency + PPTX rendering service (AC: #1, #2)
  - [x] 2.1 Add `python-pptx>=0.6.23` to `backend/requirements.txt`
  - [x] 2.2 Create `backend/app/services/render/__init__.py` (empty)
  - [x] 2.3 Create `backend/app/services/render/pptx_builder.py`:
    - Function `build_pptx(context: RenderContext) -> bytes` (returns PPTX file bytes)
    - `RenderContext` dataclass:
      - `deck_name: str`
      - `data_source_filename: str`
      - `narrative_text: str`
      - `narrative_confidence: float`
      - `story_angle: str`
      - `viz_recommendation: dict | None`
      - `assumptions: list[dict]` -- from Narrative.assumptions_json
      - `questions_and_answers: list[dict]` -- from QuestionSession.questions_json + answers_json
      - `quality_notes: list[dict]` -- from IngestJob.quality_report["issues"]
      - `reconciliation_summary: dict` -- checks pass/fail summary from ReconciliationReport
      - `verified_at: str` -- timestamp from ReconciliationReport
    - Slide-building functions (all use python-pptx):
      - `_add_title_slide(prs, context)` -- Slide 1: deck_name, current date, data_source_filename
      - `_add_executive_summary_slide(prs, context)` -- Slide 2: first 2 sentences of narrative_text, story_angle subtitle, confidence score in notes
      - `_add_data_slides(prs, context)` -- Slides 3-N: one slide per viz_recommendation entry. Each slide: chart type label as title, placeholder text box "Chart: {chart_type} — {description}", data table if tabular data available. Add footnotes for data limitations from quality_notes. Add notes: `confidence: {narrative_confidence}, assumptions: {len(assumptions)}`
      - `_add_assumptions_slide(prs, context)` -- Slide N+1: title "Assumptions & Inference Flags", bulleted list grouped by flag_type (EXPLICIT, PATTERN, INFERRED), each with confidence % and flag type badge label
      - `_add_qa_slide(prs, context)` -- Slide N+2: title "Questions & Answers", bulleted Q&A pairs from questions_and_answers
      - `_add_appendix_slide(prs, context)` -- Final slide: title "Appendix", sections: Data Quality Notes (bulleted quality issues), Reconciliation Summary (checks pass/fail counts), Verification Timestamp
    - Use a blank presentation layout (no external template file for MVP)
    - Standard slide dimensions (10" x 7.5" widescreen)
    - Font: Calibri, 11pt body, 28pt title, 18pt subtitle
    - Colors: dark text (#1a1a2e), accent blue (#2563eb), muted gray (#6b7280)

- [x] Task 3: Backend -- Render endpoint + download endpoint (AC: #1, #3, #4)
  - [x] 3.1 Create `backend/app/api/v1/schemas/render.py`:
    - `RenderResponse`: `deck_id: str`, `version: int`, `pptx_url: str`, `status: str`
  - [x] 3.2 Create `backend/app/api/v1/endpoints/render.py`:
    - `POST /api/v1/decks/{deck_id}/render`:
      1. Fetch DeckSelection for deck_id (404 if not found)
      2. Fetch the selected Narrative via deck_selection.narrative_id
      3. Use `deck_selection.user_edits_text or narrative.narrative_text` as the final narrative text
      4. Fetch the QuestionSession for deck_id (latest by created_at)
      5. Fetch IngestJob for deck_id (latest)
      6. Fetch latest ReconciliationReport for deck_id where passed=True (or all checks resolved) -- verify that verification is complete by checking for audit_log entry with action="verification_completed" for this deck
      7. Fetch Deck for deck name
      8. Extract data_source_filename from ingest_job.file_url (parse the filename from s3:// path)
      9. Build RenderContext from all fetched data
      10. Call `build_pptx(context)` via `asyncio.to_thread()` (CPU-bound)
      11. Upload PPTX bytes to MinIO via `storage.upload_file(pptx_bytes, f"{deck_id}/deck_v{version}.pptx")`
      12. Compute version: count existing DeckOutput rows for deck_id + 1
      13. Create DeckOutput row with deck_id, version, pptx_url
      14. Create audit_log entry: action="deck_rendered", details={version, narrative_id, deck_output_id}
      15. Return RenderResponse
    - `GET /api/v1/decks/{deck_id}/render/download`:
      1. Fetch latest DeckOutput for deck_id (404 if none)
      2. Extract object_key from pptx_url (strip "s3://bucket/" prefix)
      3. Download PPTX bytes from MinIO via `storage.download_file(object_key)`
      4. Return `StreamingResponse` with `media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"`, `Content-Disposition: attachment; filename="deck_v{version}.pptx"`
  - [x] 3.3 Register render router in `backend/app/api/v1/router.py`:
    - `from app.api.v1.endpoints import render`
    - `api_router.include_router(render.router, tags=["render"])`

- [x] Task 4: Frontend -- RenderScreen page + route (AC: #4)
  - [x] 4.1 Add route `/decks/:deckId/render` -> `RenderScreen` in `frontend/src/App.tsx`
  - [x] 4.2 Create `frontend/src/pages/RenderScreen.tsx`:
    - Use `AppShell` with pipeline steps: Ingest ✓, Questions ✓, Narratives ✓, Verify ✓, Render active
    - Accept `deckId` from `useParams`
    - On mount: call `POST /api/v1/decks/${deckId}/render` to trigger rendering
    - Show loading state: "Generating boardroom-ready deck..." with spinner
    - On success: show success card with:
      - Green checkmark icon
      - "Your deck is ready!"
      - Deck version number
      - [Download PPTX] button -- calls `GET /api/v1/decks/${deckId}/render/download` and triggers browser download (use `window.open` or create an `<a>` tag with download attribute)
      - [Back to Verification] link -- navigates to `/decks/${deckId}/verify?mode=readonly`
    - On error: show error message with retry button
    - After successful render, update pipeline steps to show Render ✓
    - Inline styles only (project convention)

- [x] Task 5: Frontend -- Wire download button on VerificationScreen (AC: #4)
  - [x] 5.1 In `frontend/src/components/verify/GateStatusBar.tsx`:
    - In readonly mode, add a [Download PPTX] button next to the "Verified {timestamp}" text
    - Button calls `onDownloadPptx` prop (new prop: `onDownloadPptx?: () => void`)
  - [x] 5.2 In `frontend/src/pages/VerificationScreen.tsx`:
    - Add `handleDownloadPptx` function: opens `/api/v1/decks/${deckId}/render/download` in a new window or creates a hidden anchor element to trigger download
    - Pass `onDownloadPptx={handleDownloadPptx}` to GateStatusBar when mode="readonly"

- [x] Task 6: Backend -- Tests (AC: #1, #2, #3, #4)
  - [x] 6.1 Create `backend/tests/test_render_endpoint.py`:
    - Test POST /render creates DeckOutput row and returns RenderResponse with version
    - Test POST /render creates audit_log entry with action="deck_rendered"
    - Test POST /render returns 404 when no DeckSelection exists
    - Test POST /render generates valid PPTX file (verify bytes start with PK zip signature)
    - Test GET /render/download returns PPTX file with correct content-type
    - Test GET /render/download returns 404 when no DeckOutput exists
    - Test PPTX contains expected slide count (minimum 6: title, summary, data, assumptions, Q&A, appendix)
    - Test version increments on re-render
  - [x] 6.2 Add pptx_builder unit tests in `backend/tests/test_pptx_builder.py`:
    - Test build_pptx returns valid bytes
    - Test slide structure matches expected order
    - Test title slide contains deck name and date
    - Test assumptions slide groups by flag type
    - Test Q&A slide contains question-answer pairs
    - Test appendix slide contains quality notes

## Dev Notes

### Epic 4 Dependencies on Epic 1-3 Code -- CRITICAL

This story depends on ALL of Epics 1-3 being complete. Specifically:

| Dependency | Source Epic/Story | What's needed | Model/File |
|---|---|---|---|
| Deck model | Epic 1, Story 1.1 | `decks.name` for title slide | `backend/app/models/deck.py` |
| IngestJob model | Epic 1, Story 1.2 | `file_url` for filename, `quality_report` for appendix | `backend/app/models/ingest_job.py` |
| QuestionSession model | Epic 2, Story 2.1 | `questions_json` + `answers_json` for Q&A slide | `backend/app/models/question_session.py` |
| Narrative model | Epic 2, Story 2.3 | `narrative_text`, `assumptions_json`, `viz_recommendation`, `overall_confidence`, `story_angle` | `backend/app/models/narrative.py` |
| DeckSelection model | Epic 2, Story 2.4 | `selected_narrative_id`, `user_edits_text` | `backend/app/models/deck_selection.py` |
| ReconciliationReport model | Epic 3, Story 3.1 | `checks_json`, `figure_traces`, `passed`, `verified_at` | `backend/app/models/reconciliation_report.py` |
| AuditLog model | Epic 1, Story 1.1 | Write audit entries | `backend/app/models/audit_log.py` |
| Storage service | Epic 1, Story 1.2 | `upload_file()` and `download_file()` for MinIO | `backend/app/services/storage.py` |
| verify/complete endpoint | Epic 3, Story 3.4 | Must have been called before render (verification gate) | `backend/app/api/v1/endpoints/verify.py` |

### Gaps Between Epic 1-3 and Epic 4 Needs

1. **DeckOutput model does NOT exist yet** -- must be created (Task 1). No existing model or migration.
2. **`python-pptx` is NOT in requirements.txt** -- must be added. Current dependencies are FastAPI, Pandas, SQLAlchemy, etc.
3. **No render endpoint exists** -- `backend/app/api/v1/endpoints/render.py` is entirely new.
4. **No RenderScreen page exists** -- frontend currently navigates to `/decks/${deckId}/render` from VerificationScreen (line 265) but that route doesn't exist.
5. **GateStatusBar readonly mode has no download button** -- currently shows "Verified {timestamp}" text only, needs [Download PPTX] button added.
6. **Narrative.viz_recommendation is JSONB** -- the shape is `{chart_type: str, justification: str}` per narrative. The render service must handle this being null (no data slides if no viz_recommendation).
7. **data_source_filename extraction** -- IngestJob.file_url stores S3 paths like `s3://bucket/uuid/filename.csv`. Must parse the original filename from this path.
8. **storage.download_file is synchronous** -- unlike `upload_file` which has an async wrapper, `download_file` is sync-only. Either call via `asyncio.to_thread()` or use it directly since the download endpoint can be sync.

### Shared Utilities Across Epic 4 Stories

Epic 4 only has one story (4-1), so there are no cross-story shared utilities within Epic 4. However, this story reuses extensively from prior epics:

| Utility | Source | Usage in Story 4.1 |
|---|---|---|
| `storage.upload_file()` | Story 1.2 | Upload generated PPTX to MinIO |
| `storage.download_file()` | Story 1.2 | Download PPTX for client download |
| `apiFetch` | Story 1.1 | Frontend API calls |
| `AppShell` + `ProgressRail` | Story 1.1 | Layout with pipeline steps |
| `PLACEHOLDER_USER_ID` | Story 3.1+ | Auth-deferred user_id for audit_log |
| `asyncio.to_thread()` | Story 3.1+ pattern | Offload CPU-bound PPTX generation |

### Previous Story Intelligence

**Key patterns from Epic 3 stories to follow:**
- `asyncio.to_thread()` for CPU-bound work (Pandas/numpy in verify, python-pptx here)
- `PLACEHOLDER_USER_ID = "00000000-0000-0000-0000-000000000000"` for auth-deferred user_id
- Audit log creation in try/except with warning log on failure (verify.py pattern)
- `useParams<{ deckId: string }>()`, `useNavigate()` for routing
- Inline styles only (no CSS modules, no Tailwind)
- `useState` / `useEffect` pattern, no Redux/context
- `apiFetch` from `frontend/src/api/client.ts`
- Loading states with descriptive text + spinner

**Review fixes from Stories 3.1-3.4 to apply proactively:**
- Always validate deck_id matches when cross-referencing models
- Double-click guard on async button operations (prevent duplicate renders)
- Log audit errors with warning, don't bare `pass`
- `cancelled` flag in useEffect async to prevent state updates on unmounted component

### Architecture Compliance

**API contract (from Architecture Section 5):**
```
POST /api/v1/decks/{deck_id}/render
  Generate PPTX
  Returns: {pptx_url, status}
```

This story extends the spec to include version number and a download endpoint (not in original spec but needed for browser download).

**PPTX slide structure (from Architecture Section 3.5):**
```
Slide 1: Title (Company, Deck Title, Date, Data Source)
Slide 2: Executive Summary (1-2 sentence narrative)
Slide N: Data visualization (chart + data table)
Slide N+1: Assumptions + Inference Flags
Slide N+2: Q&A (Questions asked + Answers given)
Slide Final: Appendix (Data Quality Notes, Reconciliation Status)
```

**deck_outputs table (from Architecture Section 4):**
```sql
CREATE TABLE deck_outputs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deck_id UUID REFERENCES decks NOT NULL,
  version INT,
  pptx_url TEXT,
  html_content TEXT,  -- NOT implemented for MVP (PPTX only)
  rendered_at TIMESTAMP DEFAULT now()
);
```
Note: `html_content` column is in the architecture but NOT in MVP scope. The model should include it as nullable for forward compatibility, or omit it entirely. Decision: omit it -- no unused columns.

**Performance target (from Architecture Section 7.1):**
- PPTX rendering: < 1 second
- python-pptx generates in-memory (no external tool calls), so this is achievable

**Alembic migration numbering:**
- Next migration is `008` (007 is the latest: `007_audit_log_nullable_user_id.py`)

### File Structure

```
backend/app/
  models/deck_output.py (NEW)
  models/__init__.py (MODIFIED -- add DeckOutput import)
  services/render/__init__.py (NEW -- empty)
  services/render/pptx_builder.py (NEW)
  api/v1/schemas/render.py (NEW)
  api/v1/endpoints/render.py (NEW)
  api/v1/router.py (MODIFIED -- add render router)

backend/alembic/versions/
  008_add_deck_outputs.py (NEW)

backend/requirements.txt (MODIFIED -- add python-pptx)

frontend/src/
  pages/RenderScreen.tsx (NEW)
  App.tsx (MODIFIED -- add /render route)
  components/verify/GateStatusBar.tsx (MODIFIED -- add download button in readonly mode)
  pages/VerificationScreen.tsx (MODIFIED -- add handleDownloadPptx handler)
```

### Anti-Patterns to Avoid

- Do NOT create an external PPTX template file -- use python-pptx's blank presentation (no file dependency)
- Do NOT implement HTML rendering -- MVP is PPTX only (per epics scope constraints)
- Do NOT create Celery/async job queue -- synchronous rendering within the request is sufficient for MVP (< 1s target)
- Do NOT create CSS files -- inline styles only (project convention)
- Do NOT use React context or Redux -- useState in page component (project convention)
- Do NOT create a separate download page -- the download is a direct file response from the API
- Do NOT add `html_content` column to DeckOutput -- not in MVP scope
- Do NOT import render router if the file doesn't exist yet -- create it first, then register
- Do NOT skip the verification gate check -- POST /render should verify that verification_completed audit_log exists for this deck
- Do NOT use `json.dumps` for PPTX text content -- python-pptx handles strings directly
- Do NOT create new Pydantic models for internal data passing -- use a simple dataclass for RenderContext

### Testing Requirements

- Backend unit tests for render endpoint: creates DeckOutput, creates audit_log, returns 404 on missing selection, generates valid PPTX bytes
- Backend unit tests for download endpoint: returns PPTX with correct content-type, returns 404 when no output exists
- Backend unit tests for pptx_builder: valid output, correct slide count, correct slide content
- Frontend manual testing:
  1. Complete verification flow -> click "Proceed to Render" -> verify RenderScreen loads
  2. Wait for rendering -> verify success card with download button appears
  3. Click [Download PPTX] -> verify browser downloads a .pptx file
  4. Open downloaded .pptx -> verify slide structure (title, summary, data, assumptions, Q&A, appendix)
  5. Navigate back to verify screen (readonly) -> verify [Download PPTX] button works
  6. Verify progress rail shows all 5 steps completed
  7. Verify slide notes contain confidence and assumption count metadata
  8. Test error case: try rendering without completed verification -> verify appropriate error

### References

- [Source: epics.md#Story 4.1 -- Full acceptance criteria and user story]
- [Source: epics.md#FR22 -- PPTX generation with structured slides]
- [Source: epics.md#FR23 -- Slide metadata and footnotes]
- [Source: epics.md#NFR5 -- PPTX rendering < 1 second]
- [Source: ARCHITECTURE-Technical-Design.md#Section 3.5 -- Rendering Service process and slide structure]
- [Source: ARCHITECTURE-Technical-Design.md#Section 4 -- deck_outputs table schema]
- [Source: ARCHITECTURE-Technical-Design.md#Section 5 -- POST /render API endpoint]
- [Source: ARCHITECTURE-Technical-Design.md#Section 7.1 -- Performance target < 1 second]
- [Source: backend/app/models/narrative.py -- Narrative model with narrative_text, assumptions_json, viz_recommendation, overall_confidence]
- [Source: backend/app/models/deck_selection.py -- DeckSelection model with selected_narrative_id, user_edits_text]
- [Source: backend/app/models/reconciliation_report.py -- ReconciliationReport model with checks_json, figure_traces, passed, verified_at]
- [Source: backend/app/models/question_session.py -- QuestionSession model with questions_json, answers_json]
- [Source: backend/app/models/ingest_job.py -- IngestJob model with file_url, quality_report]
- [Source: backend/app/models/deck.py -- Deck model with name]
- [Source: backend/app/services/storage.py -- upload_file() and download_file() for MinIO]
- [Source: backend/app/api/v1/router.py -- Router registration pattern]
- [Source: backend/app/api/v1/endpoints/verify.py -- verify/complete endpoint pattern]
- [Source: frontend/src/pages/VerificationScreen.tsx:261-269 -- handleProceedToRender navigates to /render]
- [Source: frontend/src/components/verify/GateStatusBar.tsx -- readonly mode needs download button]
- [Source: frontend/src/App.tsx -- Route registration pattern]
- [Source: 3-4-assumption-sign-off-gate-resolution.md -- Latest story patterns and conventions]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6

### Debug Log References

- All 20 new tests pass (13 pptx_builder + 7 render endpoint) -- zero regressions
- 21 pre-existing test failures in test_narratives.py and test_questions.py are unrelated to this story (same as documented in Story 3.4)
- Frontend TypeScript compiles cleanly with `tsc --noEmit`
- Full backend suite: 145 passed, 21 failed (all pre-existing)

### Completion Notes List

- Task 1: Created DeckOutput model with id, deck_id (FK indexed), version, pptx_url, rendered_at, created_at. Added to models/__init__.py. Created Alembic migration 008_add_deck_outputs.py.
- Task 2: Added python-pptx>=0.6.23 to requirements.txt. Created render service module with pptx_builder.py containing RenderContext dataclass and build_pptx function. Generates 6-slide PPTX: Title, Executive Summary, Data Visualizations (chart placeholders), Assumptions & Inference Flags (grouped by EXPLICIT/PATTERN/INFERRED), Q&A, Appendix. Each slide includes notes with confidence and assumption count metadata. Handles null viz_recommendation (skips data slides), empty assumptions, empty Q&A.
- Task 3: Created RenderResponse Pydantic schema. Created render.py endpoint with POST /render (fetches all upstream data, builds PPTX via asyncio.to_thread, uploads to MinIO, creates DeckOutput row, creates audit_log entry) and GET /render/download (fetches latest DeckOutput, downloads from MinIO, returns StreamingResponse with correct PPTX content-type). Registered render router in router.py.
- Task 4: Created RenderScreen.tsx with loading spinner, success card (green checkmark, version number, Download PPTX button, Back to Verification link), error state with retry. Added /render route to App.tsx. Follows project conventions: inline styles, AppShell, useParams, apiFetch, aria-live announcements.
- Task 5: Added onDownloadPptx optional prop to GateStatusBar. In readonly mode, renders Download PPTX button next to "Verified" text. Added handleDownloadPptx handler in VerificationScreen that triggers browser download via anchor element.
- Task 6: Created 7 render endpoint tests (create output, audit log, 404 no selection, valid PPTX bytes, download with correct content-type, download 404, version increment). Created 13 pptx_builder unit tests (valid bytes, slide counts with/without viz, title content, executive summary, assumptions grouping, Q&A pairs, appendix content, slide notes metadata, multiple viz, empty states).

### Change Log

- 2026-06-21: Implemented Story 4.1 -- PPTX Rendering Service & Deck Download. Created DeckOutput model, python-pptx rendering service with 6-slide structure, POST/GET render endpoints, RenderScreen frontend page, download button on VerificationScreen readonly mode, 20 backend tests.

### File List

- backend/app/models/deck_output.py (NEW)
- backend/app/models/__init__.py (MODIFIED -- added DeckOutput import)
- backend/alembic/versions/008_add_deck_outputs.py (NEW)
- backend/requirements.txt (MODIFIED -- added python-pptx)
- backend/app/services/render/__init__.py (NEW -- empty)
- backend/app/services/render/pptx_builder.py (NEW)
- backend/app/api/v1/schemas/render.py (NEW)
- backend/app/api/v1/endpoints/render.py (NEW)
- backend/app/api/v1/router.py (MODIFIED -- added render router)
- backend/tests/test_pptx_builder.py (NEW)
- backend/tests/test_render_endpoint.py (NEW)
- frontend/src/pages/RenderScreen.tsx (NEW)
- frontend/src/App.tsx (MODIFIED -- added /render route)
- frontend/src/components/verify/GateStatusBar.tsx (MODIFIED -- added onDownloadPptx prop and download button in readonly mode)
- frontend/src/pages/VerificationScreen.tsx (MODIFIED -- added handleDownloadPptx handler, passed to GateStatusBar)

### Review Findings

- [x] [Review][Decision] Slide dimensions 13.333" wide vs spec's 10" — Resolved: keep 16:9 widescreen (13.333x7.5), matches modern PowerPoint default and "widescreen" intent. Spec's numeric value was 4:3 which contradicts its own "widescreen" label.
- [x] [Review][Patch] CRITICAL: Race condition on version numbering — Added UniqueConstraint on (deck_id, version) to DeckOutput model and migration 008. [backend/app/models/deck_output.py, backend/alembic/versions/008_add_deck_outputs.py]
- [x] [Review][Patch] CRITICAL: Missing verification gate check — Added audit_log query for verification_completed before rendering. Returns 409 if not found. Added test. [backend/app/api/v1/endpoints/render.py]
- [x] [Review][Patch] S3 URL parsing fragile + empty pptx_url crash — Added None/empty pptx_url guard (404), malformed S3 URL guard (500). [backend/app/api/v1/endpoints/render.py]
- [x] [Review][Patch] datetime.now() without timezone on title slide — Changed to datetime.now(timezone.utc). [backend/app/services/render/pptx_builder.py]
- [x] [Review][Patch] S3 download error propagates as raw 500 — Added try/except ClientError returning 502. [backend/app/api/v1/endpoints/render.py]
- [x] [Review][Patch] Retry handler: no loading guard, no cancelled flag, dead event dispatch — Added ref guard, cancelled flag pattern, removed dead event dispatch. [frontend/src/pages/RenderScreen.tsx]
- [x] [Review][Patch] _build_reconciliation_summary assumes dict but checks_json could be list — Added isinstance check, handles both dict and list. [backend/app/api/v1/endpoints/render.py]
- [x] [Review][Patch] narrative_text/story_angle could be None causing AttributeError — Added `or ""` guards before .replace() calls. [backend/app/services/render/pptx_builder.py]
- [x] [Review][Patch] Response instead of StreamingResponse — Changed to StreamingResponse with async generator. [backend/app/api/v1/endpoints/render.py]
- [x] [Review][Defer] No access control / auth on render and download endpoints — pre-existing PLACEHOLDER_USER_ID pattern across all endpoints, not introduced by this story. [backend/app/api/v1/endpoints/render.py:27] — deferred, pre-existing
- [x] [Review][Defer] Download anchor-click bypasses future auth headers — both RenderScreen and VerificationScreen download via anchor element instead of apiFetch+blob, will break when auth is added. [frontend/src/pages/RenderScreen.tsx:82, frontend/src/pages/VerificationScreen.tsx:273] — deferred, pre-existing pattern
- [x] [Review][Defer] No composite index on (deck_id, rendered_at) for download ORDER BY — adequate at current scale, degrades with many renders per deck. [backend/app/api/v1/endpoints/render.py:205] — deferred, perf optimization
- [x] [Review][Defer] Q&A/assumptions slides overflow with large datasets — all items render into single fixed-height text frame with no pagination. [backend/app/services/render/pptx_builder.py:267,214] — deferred, presentation quality at scale

### Review Findings (Round 2)

- [x] [Review][Decision] Data slides missing "data table per viz_recommendation" — Dismissed: spec deviation. viz_recommendation only contains {chart_type, justification}, no tabular data exists to render. [backend/app/services/render/pptx_builder.py:150-201]
- [x] [Review][Patch] CRITICAL: Race condition on version numbering still exploitable under concurrent requests — Added retry-on-IntegrityError loop (max 3 attempts) with rollback. Returns 409 after exhaustion. [backend/app/api/v1/endpoints/render.py:172-215]
- [x] [Review][Patch] No Content-Length header on download StreamingResponse — Added Content-Length header from len(pptx_bytes). [backend/app/api/v1/endpoints/render.py:258-262]
- [x] [Review][Patch] quality_report data shape safety — Changed truthiness check to isinstance(ingest_job.quality_report, dict) guard. [backend/app/api/v1/endpoints/render.py:143-144]
- [x] [Review][Defer] assumptions_json model typed as dict|None but used as list[dict] — Narrative model type annotation says dict|None but all upstream code stores list[dict]. Runtime works but type hint is misleading. [backend/app/models/narrative.py:24] — deferred, pre-existing model annotation
- [x] [Review][Defer] answers_json model typed as dict|None but _merge_qa expects list — QuestionSession model type annotation says dict|None but actual data is always list. [backend/app/models/question_session.py:18] — deferred, pre-existing model annotation
- [x] [Review][Defer] S3-DB transaction inconsistency — if upload_file succeeds but db.commit() fails, orphaned file in S3 with no DB record. No transactional coordination. [backend/app/api/v1/endpoints/render.py:178-202] — deferred, architectural
- [x] [Review][Defer] Audit log failure silently swallowed — try/except around AuditLog creation means render can succeed without audit trail. Pre-existing pattern from Story 3.1+ verify.py. [backend/app/api/v1/endpoints/render.py:197-200] — deferred, pre-existing pattern
- [x] [Review][Defer] No performance validation of < 1 second rendering target — no timing measurement, logging, or test asserts execution time. AC3 requirement unvalidated. [backend/app/api/v1/endpoints/render.py:170] — deferred, separate concern
- [x] [Review][Defer] Frontend download anchor-click bypasses auth headers — both RenderScreen and VerificationScreen use anchor element instead of apiFetch+blob. Will break when auth is added. [frontend/src/pages/RenderScreen.tsx:82, frontend/src/pages/VerificationScreen.tsx:273] — deferred, pre-existing pattern
- [x] [Review][Defer] Large viz_recommendation list creates unbounded slides — no cap on slide count from JSONB data. [backend/app/services/render/pptx_builder.py:150-201] — deferred, presentation quality at scale
- [x] [Review][Defer] handleApplyFix/handleAcknowledge re-throw errors without catch — unhandled promise rejections in VerificationScreen. [frontend/src/pages/VerificationScreen.tsx:177-179] — deferred, pre-existing
