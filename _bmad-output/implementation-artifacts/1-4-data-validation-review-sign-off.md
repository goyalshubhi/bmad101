---
baseline_commit: 1dc3933fe26c6e430c6674907e473e2815019b28
---

# Story 1.4: Data Validation Review & Sign-Off

Status: done

## Story

As an analyst,
I want to see the quality report on screen, acknowledge any issues, and sign off to proceed to questions,
so that I trust the data is clean enough before the system asks me about it.

## Acceptance Criteria

1. **Given** an ingest job has completed with status CLEAN, **When** I view the ingestion screen, **Then** I see the schema summary (columns, types, row count) and a green status indicating no issues, **And** the "Proceed to Questions" button is enabled.
2. **Given** an ingest job has completed with status ISSUES_BLOCKING, **When** I view the ingestion screen, **Then** I see each quality issue with severity, description, count, and sample rows.
3. **Given** I am viewing blocking issues, **When** I can acknowledge each issue individually, **And** `POST /api/v1/decks/{deck_id}/validate-acknowledge` updates the status to ISSUES_ACKNOWLEDGED, **Then** the "Proceed to Questions" button enables only after acknowledgment.
4. **Given** the user has signed off on data validation, **When** the sign-off is recorded, **Then** an audit_log entry is created with action `data_validated` and the user_id + timestamp, **And** the ingest_job `validated_at` timestamp is set.

## Tasks / Subtasks

- [x] Task 1: GET endpoint for ingest job details (AC: #1, #2)
  - [x] 1.1 Create `GET /api/v1/decks/{deck_id}/ingest-status` endpoint in `backend/app/api/v1/endpoints/ingest.py` — returns latest ingest job for a deck with schema_json, quality_report, status
  - [x] 1.2 Add `IngestStatusResponse` schema in `backend/app/api/v1/schemas/ingest.py` with fields: ingest_job_id, schema, quality_report, status, validated_at
  - [x] 1.3 Write test for GET endpoint — CLEAN status, ISSUES_BLOCKING status, no ingest job (404)

- [x] Task 2: Validate-acknowledge endpoint (AC: #3, #4)
  - [x] 2.1 Create `POST /api/v1/decks/{deck_id}/validate-acknowledge` endpoint in `backend/app/api/v1/endpoints/ingest.py`
  - [x] 2.2 Request body: `AcknowledgeRequest` with `user_id: UUID` (temporary until auth is implemented)
  - [x] 2.3 Endpoint logic: find latest ingest_job for deck_id, verify status is ISSUES_BLOCKING, update status to ISSUES_ACKNOWLEDGED, set validated_at to now()
  - [x] 2.4 Create audit_log entry: `{deck_id, user_id, action: "data_validated", details: {ingest_job_id, previous_status, acknowledged_issues_count}}`
  - [x] 2.5 If status is already CLEAN, set validated_at and create audit_log (no status change needed)
  - [x] 2.6 If status is already ISSUES_ACKNOWLEDGED, return 409 Conflict
  - [x] 2.7 If no ingest_job exists, return 404
  - [x] 2.8 Add `AcknowledgeRequest` and `AcknowledgeResponse` schemas in `backend/app/api/v1/schemas/ingest.py`
  - [x] 2.9 Write tests: acknowledge blocking issues, acknowledge clean data, re-acknowledge (409), no job (404)

- [x] Task 3: Frontend — Data Validation Screen (AC: #1, #2, #3)
  - [x] 3.1 Create `frontend/src/pages/ValidationReview.tsx` — main screen component
  - [x] 3.2 Schema summary section: display columns, types, row count from schema_json
  - [x] 3.3 Quality issues section: list each issue with severity badge (high=red, medium=amber, low=gray), description, count, sample rows
  - [x] 3.4 Status banner: green "No Issues Found" for CLEAN, red "N Issues Require Acknowledgment" for ISSUES_BLOCKING, blue "Issues Acknowledged" for ISSUES_ACKNOWLEDGED
  - [x] 3.5 Acknowledge button: calls POST validate-acknowledge, refreshes status on success
  - [x] 3.6 "Proceed to Questions" button: enabled when status is CLEAN or ISSUES_ACKNOWLEDGED, disabled otherwise
  - [x] 3.7 Integrate ProgressRail with Ingest step active, using existing `ProgressRail` component

- [x] Task 4: Frontend routing and integration (AC: #1)
  - [x] 4.1 Install `react-router-dom` (add to frontend/package.json)
  - [x] 4.2 Create `frontend/src/pages/Home.tsx` — move current App.tsx content here
  - [x] 4.3 Update `frontend/src/App.tsx` — add React Router with routes: `/` (Home), `/decks/:deckId/validate` (ValidationReview)
  - [x] 4.4 Add API client utility `frontend/src/api/client.ts` — fetch wrapper for backend API calls with base URL from env

- [x] Task 5: Tests (AC: #1-4)
  - [x] 5.1 Backend: integration test for full flow — ingest CSV → GET status → acknowledge → verify audit_log
  - [x] 5.2 Backend: unit test for audit_log creation with correct action and details

### Review Findings

- [x] [Review][Decision] #1 No guard against unexpected status values in validate-acknowledge — RESOLVED: added allowlist check, rejects non-CLEAN/ISSUES_BLOCKING with 400
- [x] [Review][Decision] #2 CLEAN jobs can be re-validated indefinitely — RESOLVED: skip if already validated, return existing data without new audit log
- [x] [Review][Patch] #3 Race condition on concurrent acknowledge requests — FIXED: added with_for_update() [ingest.py:114]
- [x] [Review][Patch] #4 StatusBanner masks unknown status as green "No Issues Found" — FIXED: amber warning fallback [ValidationReview.tsx]
- [x] [Review][Patch] #5 quality_report.issues.length crashes if issues key missing — FIXED: added null-coalescing [ValidationReview.tsx]
- [x] [Review][Patch] #6 handleAcknowledge swallows non-ApiError exceptions silently — FIXED: added else branch [ValidationReview.tsx]
- [x] [Review][Patch] #7 fetchStatus doesn't guard against undefined deckId — FIXED: added early return [ValidationReview.tsx]
- [x] [Review][Patch] #8 useEffect missing fetchStatus in dependency array — FIXED: inlined with cleanup [ValidationReview.tsx]
- [x] [Review][Defer] #9 Content-Type header forced to JSON on all requests — breaks future FormData uploads [client.ts:6-8] — deferred, pre-existing pattern
- [x] [Review][Defer] #10 File read into memory before size check in ingest endpoint [ingest.py:44-48] — deferred, pre-existing from Story 1.2
- [x] [Review][Defer] #11 No 404 catch-all route in React Router [App.tsx] — deferred, not in story scope
- [x] [Review][Defer] #12 apiFetch assumes all success responses are JSON [client.ts:17] — deferred, no current 204 endpoints

## Dev Notes

### Previous Story Intelligence (from Story 1.2)

**Established patterns to follow:**
- FastAPI async endpoints with `asyncio.to_thread` for synchronous I/O (boto3 calls)
- SQLAlchemy async models in `backend/app/models/`
- Alembic migrations in `backend/alembic/versions/` with sequential numbering (001, 002...)
- Tests in `backend/tests/` using pytest-asyncio with httpx `ASGITransport`
- Pydantic Settings in `backend/app/core/config.py` for env-based config
- API router pattern: endpoints in `backend/app/api/v1/endpoints/`, schemas in `backend/app/api/v1/schemas/`
- Ingest router already registered in `router.py` — new endpoints go in existing `ingest.py`

**Review findings from Story 1.2 relevant to this story:**
- Auth deferred — use `user_id` in request body as temporary approach
- Status logic: CLEAN = no issues, ISSUES_BLOCKING = any high-severity issue. This story adds ISSUES_ACKNOWLEDGED transition.

### Existing Code State (files being modified)

**`backend/app/api/v1/endpoints/ingest.py`** — Currently has `POST /decks/{deck_id}/ingest`. Add two new endpoints in the same file:
- `GET /decks/{deck_id}/ingest-status` — returns latest ingest job
- `POST /decks/{deck_id}/validate-acknowledge` — acknowledges issues and sets validated_at

**`backend/app/api/v1/schemas/ingest.py`** — Currently has `QualityIssue` and `IngestResponse`. Add:
- `IngestStatusResponse` — for GET endpoint
- `AcknowledgeRequest` — with user_id field
- `AcknowledgeResponse` — with updated status, validated_at

**`backend/app/models/ingest_job.py`** — Has all needed columns already: `status` (String(30)), `validated_at` (DateTime). No migration needed.

**`backend/app/models/audit_log.py`** — Has all needed columns: `deck_id`, `user_id`, `action` (String(100)), `details` (JSONB). Ready to use.

**`frontend/src/App.tsx`** — Currently a simple placeholder. Will become the router entry point.

**`frontend/src/components/ProgressRail.tsx`** — Already implemented with `Step` type: `{label, status: "completed" | "active" | "inactive"}`. Use it in ValidationReview with steps: `[{label: "Ingest", status: "completed"}, {label: "Questions", status: "inactive"}, ...]`.

### Architecture Compliance

**API contract** (from Architecture Section 5):
```
POST /api/v1/decks/{deck_id}/validate-acknowledge
  User acknowledges data quality issues
  Returns: ready to proceed
```

**Database:** No new tables or migrations. Uses existing `ingest_jobs` (update status, validated_at) and `audit_log` (insert row).

**Audit logging requirement** (NFR7, NFR8): Every action logged with user attribution and timestamp. The `audit_log` table has immutable entries (PostgreSQL triggers prevent DELETE per architecture).

### Technical Stack

- **Backend:** FastAPI async, SQLAlchemy async, existing patterns from Story 1.2
- **Frontend:** React, no component library. Use inline styles (established pattern from ProgressRail.tsx)
- **Routing:** `react-router-dom` — needed for first time as this is the first page beyond the placeholder
- **API calls:** Use `fetch` API with a simple wrapper — no axios needed for MVP

### Directory Structure

```
backend/app/api/v1/
  endpoints/ingest.py (MODIFIED — add 2 endpoints)
  schemas/ingest.py (MODIFIED — add 3 schemas)
backend/tests/
  test_validate_acknowledge.py (NEW)
frontend/src/
  api/client.ts (NEW — fetch wrapper)
  pages/Home.tsx (NEW — moved from App.tsx)
  pages/ValidationReview.tsx (NEW — main screen)
  App.tsx (MODIFIED — add React Router)
  package.json (MODIFIED — add react-router-dom)
```

### Anti-Patterns to Avoid

- Do NOT create a new router file — add endpoints to existing `ingest.py` (they're all ingest-related)
- Do NOT create new database models or migrations — all columns exist
- Do NOT implement the Questions screen — that belongs to Story 2.2
- Do NOT implement per-issue acknowledgment tracking — the MVP acknowledges all issues at once (the endpoint transitions ISSUES_BLOCKING → ISSUES_ACKNOWLEDGED)
- Do NOT add auth middleware — auth is deferred. Accept user_id in request body
- Do NOT use a CSS framework or component library — follow inline styles pattern from ProgressRail.tsx
- Do NOT implement file upload on this screen — that was Story 1.2

### Testing Requirements

- Backend: test acknowledge endpoint (happy path: ISSUES_BLOCKING → ISSUES_ACKNOWLEDGED)
- Backend: test acknowledge on CLEAN status (should set validated_at, create audit_log)
- Backend: test re-acknowledge (409 Conflict)
- Backend: test missing ingest job (404)
- Backend: test audit_log entry has correct action ("data_validated") and details
- Backend: test GET ingest-status returns correct schema and quality report
- Use pytest with `pytest-asyncio` and `httpx` ASGITransport (same as Story 1.2)

### UX Requirements (from EXPERIENCE.md)

The data ingestion + validation is noted as "exists, out of scope" for the 3-screen UX spec, but the spec references:
- **Data context strip** on Screen 1 shows: filename, row/column counts, acknowledged quality issues count
- **Progress rail** with "Ingest ✓" as first step — this screen is the transition point where Ingest becomes ✓

Minimum viable UX for this screen:
- Schema summary table (column name, type, nullability %)
- Quality issues list with severity badges
- Status banner (green/red/blue)
- Single "Acknowledge All Issues" button (not per-issue for MVP)
- "Proceed to Questions" button (disabled until validated)
- Progress rail on left sidebar showing Ingest as active step

### References

- [Source: epics.md#Story 1.4 — Acceptance Criteria]
- [Source: ARCHITECTURE-Technical-Design.md#Section 5 — API Design: POST validate-acknowledge]
- [Source: ARCHITECTURE-Technical-Design.md#Section 3.1 — Ingest Service: validation status flow]
- [Source: ARCHITECTURE-Technical-Design.md#Section 4 — Database Schema: ingest_jobs, audit_log]
- [Source: EXPERIENCE.md — Data context strip, Progress rail]
- [Source: 1-2-csv-data-ingestion-schema-detection.md — Review findings, established patterns]

## Dev Agent Record

### Agent Model Used
Claude Sonnet 4.6

### Debug Log References
None — all tests passed on first implementation.

### Completion Notes List
- Implemented GET /api/v1/decks/{deck_id}/ingest-status endpoint returning latest ingest job with schema, quality report, and status
- Implemented POST /api/v1/decks/{deck_id}/validate-acknowledge endpoint with full status transition logic (ISSUES_BLOCKING → ISSUES_ACKNOWLEDGED, CLEAN → validated, 409 for re-acknowledge, 404 for missing job)
- Added audit_log creation with action "data_validated" and detailed metadata (ingest_job_id, previous_status, acknowledged_issues_count)
- Created ValidationReview.tsx with schema summary table, quality issues list with severity badges, status banner (green/red/blue), acknowledge button, and "Proceed to Questions" button
- Added React Router with routes for Home (/) and ValidationReview (/decks/:deckId/validate)
- Created API client utility with fetch wrapper and error handling
- Made AppShell accept optional steps prop for per-page ProgressRail customization
- 9 backend tests covering all endpoints, edge cases, and integration flow
- Frontend TypeScript builds cleanly, Vite production build succeeds

### File List
- backend/app/api/v1/endpoints/ingest.py (MODIFIED — added GET ingest-status and POST validate-acknowledge endpoints)
- backend/app/api/v1/schemas/ingest.py (MODIFIED — added IngestStatusResponse, AcknowledgeRequest, AcknowledgeResponse)
- backend/tests/test_validate_acknowledge.py (NEW — 9 tests for both endpoints + integration flow)
- frontend/src/App.tsx (MODIFIED — added React Router with routes)
- frontend/src/layouts/AppShell.tsx (MODIFIED — added optional steps prop)
- frontend/src/pages/Home.tsx (NEW — moved original App content)
- frontend/src/pages/ValidationReview.tsx (NEW — data validation review screen)
- frontend/src/api/client.ts (NEW — API fetch wrapper)
- frontend/src/vite-env.d.ts (NEW — Vite type declarations)
- frontend/package.json (MODIFIED — added react-router-dom dependency)

## Change Log
- 2026-06-18: Implemented Story 1.4 — Data Validation Review & Sign-Off. Added backend GET/POST endpoints for ingest status and acknowledgment with audit logging. Created frontend ValidationReview screen with schema summary, quality issues, status banners, and routing.
