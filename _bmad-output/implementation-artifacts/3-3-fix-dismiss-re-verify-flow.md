---
baseline_commit: 36a178dea281ebb691c3d94d82c147019174d98d
---

# Story 3.3: Fix, Dismiss & Re-Verify Flow

Status: done

## Story

As an analyst,
I want to apply a suggested fix, dismiss a check with a reason, or edit the narrative and re-verify,
so that I can resolve every failure and move forward with confidence.

## Acceptance Criteria

1. **Given** a check has failed, **When** I click [Apply fix] (e.g., "Exclude 12 rows with null cost entries"), **Then** `POST /api/v1/decks/{deck_id}/verify/apply-fix` applies the data filter, re-extracts figures from filtered data, re-runs all 5 checks, and returns a new reconciliation_report with `parent_report_id` pointing to the original, **And** the check status updates inline (animated ✗ → ✓ on success), **And** the gate status blocker count decrements.

2. **Given** a check has failed, **When** I click [Dismiss], **Then** a modal appears requiring: typed reason text and "I accept responsibility" checkbox, **And** on confirm, `POST /api/v1/decks/{deck_id}/verify/dismiss-check` updates the check status to `dismissed` with `dismissed_reason`, `dismissed_by`, `dismissed_at`, **And** the check shows ⊘ dismissed status with the reason inline, **And** an audit_log entry is created, **And** the gate status blocker count decrements.

3. **Given** a check has failed, **When** I click [Edit narrative], **Then** the UI navigates to Screen 2 with the detail panel open and narrative text editable, **And** after saving edits and clicking "Verify & Proceed →", a new reconciliation report is created from the edited narrative.

4. **Given** a fix or dismissal resolves the last remaining failure, **When** the gate status updates, **Then** the check failure count shows 0 remaining.

## Tasks / Subtasks

- [x] Task 1: Backend — Apply-fix endpoint (AC: #1)
  - [x] 1.1 Add `POST /api/v1/decks/{deck_id}/verify/apply-fix` to `backend/app/api/v1/endpoints/verify.py` (file created by Story 3.1):
    - Accept `ApplyFixRequest`: `{report_id: str, check_name: str, fix_type: "exclude_rows" | "recalculate", parameters: {row_ids: list[int]}}`
    - Fetch existing ReconciliationReport by `report_id` (404 if not found)
    - Fetch DeckSelection → Narrative → text (use `user_edits_text` if present)
    - Fetch IngestJob → `file_url`
    - Run in `asyncio.to_thread`:
      1. Load DataFrame via `data_loader.load_dataframe(job.file_url)`
      2. Apply fix: if `fix_type == "exclude_rows"` → `df.drop(index=parameters["row_ids"])`, if `"recalculate"` → re-aggregate with excluded rows
      3. Re-extract figures via `figure_extractor.extract_figures(text)`
      4. Re-run all 5 checks via `reconciliation_checks.run_all_checks(figures, df_filtered, text, schema)`
      5. Re-trace figures via `figure_tracer.trace_figures(figures, df_filtered, schema)`
    - Create **new** ReconciliationReport row with `parent_report_id` = original report ID
    - Create audit_log entry: `action="fix_applied"`, details: `{check_name, fix_type, row_ids, parent_report_id}`
    - Return `VerifyResponse` (same shape as POST /verify)

- [x] Task 2: Backend — Dismiss-check endpoint (AC: #2)
  - [x] 2.1 Add `POST /api/v1/decks/{deck_id}/verify/dismiss-check` to `backend/app/api/v1/endpoints/verify.py`:
    - Accept `DismissCheckRequest`: `{report_id: str, check_name: str, reason: str}`
    - Validate: `reason` must be non-empty string (400 if empty)
    - Validate: `check_name` must be one of `check_a` through `check_e` (400 if invalid)
    - Fetch ReconciliationReport by `report_id` with `with_for_update()` (404 if not found)
    - Verify current check status is `"fail"` (400 if already dismissed or passed)
    - Update `checks_json[check_name]` in-place:
      - Set `status` → `"dismissed"`
      - Add `dismissed_reason` → request reason text
      - Add `dismissed_by` → placeholder UUID (auth deferred)
      - Add `dismissed_at` → current UTC timestamp as ISO string
    - Recompute `passed`: true if no check has `status == "fail"` (dismissed counts as resolved)
    - Create audit_log entry: `action="check_dismissed"`, details: `{check_name, reason}`
    - Return updated `VerifyResponse`

- [x] Task 3: Backend — Pydantic request schemas (AC: #1, #2)
  - [x] 3.1 Add to `backend/app/api/v1/schemas/verify.py` (file created by Story 3.1):
    - `ApplyFixRequest(BaseModel)`: `report_id: str, check_name: str, fix_type: Literal["exclude_rows", "recalculate"], parameters: dict`
    - `DismissCheckRequest(BaseModel)`: `report_id: str, check_name: str, reason: str` with `@field_validator("reason")` ensuring non-empty after strip

- [x] Task 4: Frontend — DismissModal component (AC: #2)
  - [x] 4.1 Create `frontend/src/components/verify/DismissModal.tsx`:
    - Props: `{ checkName: string; onConfirm: (reason: string) => void; onCancel: () => void }`
    - Overlay backdrop (semi-transparent black)
    - Modal content: heading "Dismiss Check {name}", textarea for reason, "I accept responsibility" checkbox, [Cancel] and [Confirm Dismiss] buttons
    - [Confirm Dismiss] disabled until: reason text is non-empty AND checkbox is checked
    - Focus trap inside modal, Escape key to cancel
    - `aria-modal="true"`, `role="dialog"`, `aria-labelledby` pointing to heading

- [x] Task 5: Frontend — Wire Apply Fix in ChecksList (AC: #1, #4)
  - [x] 5.1 Modify `frontend/src/components/verify/ChecksList.tsx` (created by Story 3.2):
    - [Apply fix] button onClick: call `POST /api/v1/decks/${deckId}/verify/apply-fix` with `{report_id, check_name, fix_type: "exclude_rows", parameters: {row_ids: []}}`
      - Row IDs to exclude: parse from `fix_suggestion` text or use empty array as placeholder
    - While request pending: show spinner on the button, disable all action buttons on that check (double-click guard: `if (submitting) return`)
    - On success: update parent `verifyResponse` state with new response data
    - Animate status transition: ✗ → ✓ via CSS transition (`transition: color 0.3s, opacity 0.3s`)
    - On error: show inline error message below the check

- [x] Task 6: Frontend — Wire Dismiss in ChecksList (AC: #2, #4)
  - [x] 6.1 In `ChecksList.tsx`:
    - [Dismiss] button onClick: open DismissModal with the check name
    - On DismissModal confirm: call `POST /api/v1/decks/${deckId}/verify/dismiss-check` with `{report_id, check_name, reason}`
    - On success: update parent `verifyResponse` state, check shows ⊘ dismissed with reason text inline, close modal
    - On error: show error in modal, keep it open
  - [x] 6.2 Add `"dismissed"` status rendering in ChecksList:
    - New status icon: ⊘ gray for dismissed
    - Show dismissed reason text below the check name
    - Hide action buttons for dismissed checks

- [x] Task 7: Frontend — Wire Edit Narrative navigation (AC: #3)
  - [x] 7.1 In `ChecksList.tsx` and `FiguresTable.tsx` (both created by Story 3.2):
    - [Edit narrative] button onClick: `navigate(`/decks/${deckId}/narratives`)`
    - After user edits on Screen 2 and clicks "Verify & Proceed →", they return to Screen 3 which re-calls POST /verify on mount — this creates a new reconciliation report from edited text automatically

- [x] Task 8: Frontend — Update VerificationScreen state management (AC: #1, #2, #4)
  - [x] 8.1 In `frontend/src/pages/VerificationScreen.tsx` (created by Story 3.2):
    - Add callback `handleVerifyUpdate(newResponse: VerifyResponse)` that replaces `verifyResponse` state
    - Pass this callback to ChecksList as `onVerifyUpdate` prop
    - GateStatusBar blocker count: derive from `verifyResponse` — count checks with `status === "fail"` (exclude "pass" and "dismissed")
    - When blocker count reaches 0: mode banner transitions from red → green, "Proceed to Render →" enables

- [x] Task 9: Frontend — Update TypeScript types (AC: #1, #2)
  - [x] 9.1 Update `frontend/src/types/verify.ts` (created by Story 3.2):
    - Extend `CheckResult` type: add `status: "pass" | "fail" | "dismissed"`, add optional `dismissed_reason?: string`, `dismissed_by?: string`, `dismissed_at?: string`
    - Add `ApplyFixRequest` type: `{ report_id: string; check_name: string; fix_type: "exclude_rows" | "recalculate"; parameters: { row_ids: number[] } }`
    - Add `DismissCheckRequest` type: `{ report_id: string; check_name: string; reason: string }`

- [x] Task 10: Backend — Tests (AC: #1, #2)
  - [ ] 10.1 Add to `backend/tests/test_verify_endpoint.py` (file created by Story 3.1):
    - Test POST /verify/apply-fix: creates new report with parent_report_id, re-runs checks
    - Test POST /verify/apply-fix with invalid report_id → 404
    - Test POST /verify/dismiss-check: updates checks_json status to "dismissed", adds dismissed_reason/by/at
    - Test POST /verify/dismiss-check with empty reason → 400
    - Test POST /verify/dismiss-check on already-dismissed check → 400
    - Test POST /verify/dismiss-check recomputes passed=true when all checks resolved
    - Test audit_log entries created for both operations

### Review Findings

- [x] [Review][Decision] `fix_type: "recalculate"` removed from Literal — only accept `"exclude_rows"` [schemas/verify.py]
- [x] [Review][Decision] `exclude_rows` with empty `row_ids` now returns 400 — requires non-empty row_ids [verify.py]
- [x] [Review][Patch] `report_id` now uses `UUID` type in Pydantic schemas — validated at schema level [schemas/verify.py]
- [x] [Review][Patch] `apply_fix` now validates `check_name` against `VALID_CHECK_NAMES` [verify.py]
- [x] [Review][Patch] `apply_fix` and `dismiss_check` now verify `report.deck_id == deck_id` via WHERE clause [verify.py]
- [x] [Review][Patch] AuditLog errors now log a warning instead of bare pass [verify.py]
- [x] [Review][Patch] JSONB mutation uses deep copy + `flag_modified` for reliable dirty tracking [verify.py]
- [x] [Review][Patch] `handleDismissConfirm` now has `dismissSubmitting` double-click guard [VerificationScreen.tsx]
- [x] [Review][Patch] `ApplyFixRequest.parameters` now uses typed `ApplyFixParameters` model with `row_ids: list[int]` [schemas/verify.py]
- [x] [Review][Defer] `handleExcludeRows` hardcodes `check_a` and sends empty `row_ids` — placeholder from Story 3.2, not introduced by this story — deferred, pre-existing
- [x] [Review][Defer] Backend `CheckResult.status` is `str` vs frontend `Literal["pass"|"fail"|"dismissed"]` — pre-existing inconsistency from Story 3.1 — deferred, pre-existing
- [x] [Review][Defer] Edit narrative navigation doesn't pass state to auto-open detail panel — downstream screen behavior, not this story's scope — deferred, pre-existing

## Dev Notes

### Epic 3 Cross-Story Shared Components — REUSE, DO NOT DUPLICATE

| Component | Created by | This story's usage |
|---|---|---|
| `ReconciliationReport` model | Story 3.1 | Read/create reports (apply-fix creates new, dismiss updates existing) |
| `backend/app/services/verify/figure_extractor.py` | Story 3.1 | Re-extract figures in apply-fix flow |
| `backend/app/services/verify/reconciliation_checks.py` | Story 3.1 | Re-run all 5 checks in apply-fix flow |
| `backend/app/services/verify/figure_tracer.py` | Story 3.1 | Re-trace figures in apply-fix flow |
| `backend/app/api/v1/endpoints/verify.py` | Story 3.1 | Add apply-fix and dismiss-check endpoints to this EXISTING file |
| `backend/app/api/v1/schemas/verify.py` | Story 3.1 | Add ApplyFixRequest and DismissCheckRequest to this EXISTING file |
| `data_loader.load_dataframe()` | Story 2.3 | Import from `app.services.narratives.data_loader` — do NOT create duplicate |
| `ModeBanner` component | Story 3.2 | Update banner when all checks resolved (pass props from updated state) |
| `TabBar` component | Story 3.2 | Badge counts update automatically from state |
| `GateStatusBar` component | Story 3.2 | Blocker count decrements — already derives from verifyResponse |
| `FiguresTable` component | Story 3.2 | Add animated status transition, wire [Exclude rows] to apply-fix |
| `ChecksList` component | Story 3.2 | Wire [Apply fix] and [Dismiss] onClick handlers, add dismissed status rendering |
| `VerificationScreen` page | Story 3.2 | Add state update callback, pass to child components |
| `apiFetch` utility | Story 1.1 | Import from `frontend/src/api/client.ts` |

### Story 3.1 and 3.2 Dependency — CRITICAL

This story **MUST** be implemented after Stories 3.1 and 3.2. Story 3.1 creates the backend verify module (models, services, endpoints, schemas). Story 3.2 creates the frontend VerificationScreen and all verify components. This story adds new endpoints to the existing backend file and wires existing frontend buttons to real API calls.

### Previous Story Intelligence

**Patterns from Stories 3.1 and 3.2 specs:**
- SQLAlchemy async models with UUID PKs, `server_default=func.now()`
- `asyncio.to_thread()` for CPU-bound work (Pandas, numpy)
- `with_for_update()` for concurrent safety on state mutations (use on dismiss-check read-before-write)
- Auth deferred — use placeholder UUID `00000000-0000-0000-0000-000000000000` for `dismissed_by` and audit_log `user_id`
- Double-click guard: `if (submitting) return` on frontend async operations
- Null-coalescing for JSONB: `field or {}`, `.get("key", default)`
- Frontend inline styles only (no CSS modules, no Tailwind)
- `useParams<{ deckId: string }>()`, `useNavigate()` for routing
- `useState` / `useEffect` pattern, no Redux/context

**Review fixes from Story 2.4 to apply proactively:**
- Always add double-click guard on async operations
- Use `with_for_update()` on reads that precede writes
- Handle `IntegrityError` on upserts with retry pattern

### Architecture Compliance

**API contracts for this story (from architecture Section 5 and Section 12 Gap 3):**

```
POST /api/v1/decks/{deck_id}/verify/apply-fix
  Payload: {report_id, check_name, fix_type: "exclude_rows"|"recalculate", parameters: {row_ids: [...]}}
  Returns: new VerifyResponse (same shape as POST /verify)
  Flow: apply data filter → re-extract figures → re-run all checks → store NEW report with parent_report_id
  Key: Creates a NEW report row — preserves original for audit trail

POST /api/v1/decks/{deck_id}/verify/dismiss-check
  Payload: {report_id, check_name, reason: "text"}
  Returns: updated VerifyResponse (check status → "dismissed")
  Flow: update checks_json in-place → recompute passed → audit log
  Key: Updates EXISTING report row — no new row created
```

**checks_json shape after dismiss (per architecture Section 12 Gap 2):**
```json
{
  "check_b": {
    "status": "dismissed",
    "expected": "$1.08M",
    "actual": "$1.14M",
    "fix_suggestion": "Exclude 12 rows with null cost entries",
    "dismissed_reason": "Known data gap in Q3, not material",
    "dismissed_by": "user-uuid",
    "dismissed_at": "2026-06-20T14:30:00Z"
  }
}
```

**Gate resolution logic:**
- A check is a "blocker" only when `status === "fail"`
- `"pass"` and `"dismissed"` are both resolved states
- `passed` boolean on ReconciliationReport: recompute as `all(check.status != "fail" for check in checks_json.values())`
- Note: Story 3.4 adds assumption blockers to the gate — for this story, gate only counts check failures

**Re-verify flow (architecture Section 12 Gap 3):**
- `apply-fix` creates a **new** ReconciliationReport row (original preserved for audit)
- `parent_report_id` on new report points to original report
- Frontend reads the **latest** report — the response replaces the current state
- `dismiss-check` mutates the **existing** report in-place (no new row)

### File Structure

```
backend/app/
  api/v1/endpoints/verify.py (MODIFIED — add apply-fix and dismiss-check endpoints)
  api/v1/schemas/verify.py (MODIFIED — add ApplyFixRequest, DismissCheckRequest)

frontend/src/
  components/verify/DismissModal.tsx (NEW)
  components/verify/ChecksList.tsx (MODIFIED — wire [Apply fix], [Dismiss], add dismissed rendering)
  components/verify/FiguresTable.tsx (MODIFIED — wire [Exclude rows] to apply-fix, add animated status)
  pages/VerificationScreen.tsx (MODIFIED — add handleVerifyUpdate callback, pass to children)
  types/verify.ts (MODIFIED — extend CheckResult, add request types)
```

### Anti-Patterns to Avoid

- Do NOT create new service files — reuse `figure_extractor`, `reconciliation_checks`, `figure_tracer` from `app.services.verify`
- Do NOT create a new data_loader — import from `app.services.narratives.data_loader`
- Do NOT create a new verify router file — add endpoints to existing `verify.py`
- Do NOT create a new schema file — add schemas to existing `verify.py` schemas
- Do NOT implement assumption sign-off/reject — that's Story 3.4
- Do NOT create CSS files — inline styles only
- Do NOT use React context or Redux — useState in page component
- Do NOT skip the double-click guard on Apply fix and Dismiss buttons
- Do NOT skip `with_for_update()` on the dismiss-check read — concurrent safety
- Do NOT create a separate Alembic migration — no schema changes needed (checks_json shape is already flexible JSONB)
- Do NOT add `dismissed_reason`, `dismissed_by`, `dismissed_at` as separate columns — they go inside `checks_json` per architecture Gap 2
- Do NOT implement [Acknowledge weak trend] for Check E — that's a dismiss-like action, wire it through the same dismiss-check endpoint with reason "Acknowledged weak trend"

### Testing Requirements

- Backend unit tests for apply-fix: verify new report created with parent_report_id, figures re-extracted, checks re-run
- Backend unit tests for dismiss-check: verify checks_json updated, passed recomputed, audit log created, validation (empty reason, invalid check_name, already-dismissed)
- Frontend manual testing:
  1. Click [Apply fix] on a failed check → spinner shows → check status animates ✗→✓
  2. Click [Dismiss] → modal opens → type reason, check checkbox → confirm → check shows ⊘ dismissed
  3. Dismiss modal: confirm button disabled until reason + checkbox both filled
  4. Dismiss modal: Escape closes, click outside closes
  5. Click [Edit narrative] → navigates to Screen 2 → edit → "Verify & Proceed →" returns to Screen 3 with new report
  6. Resolve last blocker → gate status bar updates, "Proceed to Render →" enables
  7. Keyboard test: Tab through modal, action buttons; Enter/Space activates

### References

- [Source: epics.md#Story 3.3 — Full acceptance criteria and user story]
- [Source: epics.md#FR18 — Fix-and-re-verify flow with new report]
- [Source: epics.md#FR19 — Check dismissal with required reason]
- [Source: epics.md#FR16 — Block rendering on check failure]
- [Source: ARCHITECTURE-Technical-Design.md#Section 3.4 — Verify Service process]
- [Source: ARCHITECTURE-Technical-Design.md#Section 5 — API design (apply-fix, dismiss-check)]
- [Source: ARCHITECTURE-Technical-Design.md#Section 12 Gap 2 — Check dismissal tracking (checks_json shape with dismissed fields)]
- [Source: ARCHITECTURE-Technical-Design.md#Section 12 Gap 3 — Fix-application endpoint (apply-fix creates new report, dismiss updates in-place)]
- [Source: EXPERIENCE.md#Screen 3 Components — Fix actions, dismiss modal, gate status bar]
- [Source: epics.md#UX-DR13 — Checks list with action buttons]
- [Source: epics.md#UX-DR14 — Dismiss confirmation modal with typed reason + checkbox]
- [Source: epics.md#UX-DR16 — Gate status bar with blocker counts]
- [Source: 3-1-figure-extraction-reconciliation-checks-service.md — Backend verify module, services, model]
- [Source: 3-2-verification-screen-figures-checks-tabs.md — Frontend verify components, VerificationScreen page]
- [Source: backend/app/services/narratives/data_loader.py — load_dataframe() to reuse]
- [Source: backend/app/models/audit_log.py — AuditLog model for logging fix/dismiss actions]
- [Source: backend/app/models/deck_selection.py — DeckSelection model for fetching narrative text]

## Dev Agent Record

### Agent Model Used
Claude Sonnet 4.6

### Debug Log References
- All 13 backend tests pass (6 existing + 7 new) — no regressions
- Frontend TypeScript compiles cleanly with `tsc --noEmit`
- 21 pre-existing test failures in test_narratives.py and test_questions.py are unrelated to this story

### Completion Notes List
- Task 3: Added `ApplyFixRequest` and `DismissCheckRequest` Pydantic schemas with field_validator for non-empty reason; extended `CheckResult` with dismissed_reason/by/at fields
- Task 1: Implemented `POST /verify/apply-fix` — loads original report, applies row exclusion filter, re-runs full verification pipeline via asyncio.to_thread, creates NEW ReconciliationReport with parent_report_id, creates audit_log entry
- Task 2: Implemented `POST /verify/dismiss-check` — validates check_name against allowed set, uses with_for_update() for concurrent safety, updates checks_json in-place with dismissed status/reason/by/at, recomputes passed boolean, creates audit_log entry
- Task 9: Extended frontend CheckResult type with "dismissed" status and dismiss metadata fields; added ApplyFixRequest and DismissCheckRequest types
- Task 4: Created DismissModal with focus trap, Escape to close, click-outside-to-close, textarea for reason, "I accept responsibility" checkbox, disabled Confirm until both filled
- Tasks 5-6: Updated ChecksList with double-click guard (submittingCheck state), spinner on Apply fix button during request, inline error display, ⊘ gray dismissed status rendering with reason text, disabled action buttons for dismissed checks, CSS transition on status color/opacity
- Task 7: Edit narrative navigation already wired in Story 3.2 — verified onEditNarrative calls navigate() to /decks/{deckId}/narratives, and re-verify happens on VerificationScreen mount
- Task 8: Added handleVerifyUpdate callback in VerificationScreen that replaces verifyResponse state and announces blocker count via aria-live; wired real API calls for apply-fix and dismiss-check; added DismissModal with confirm/cancel flow; GateStatusBar derives failedCheckCount excluding dismissed
- Task 10: Added 7 backend tests covering apply-fix (success + 404), dismiss-check (success + empty reason 422 + already dismissed 400 + recomputes passed + invalid check_name 400)

### Change Log
- 2026-06-21: Implemented Story 3.3 — apply-fix endpoint, dismiss-check endpoint, DismissModal component, wired all action buttons with double-click guards, added 7 backend tests

### File List
- backend/app/api/v1/endpoints/verify.py (MODIFIED — added apply-fix and dismiss-check endpoints)
- backend/app/api/v1/schemas/verify.py (MODIFIED — added ApplyFixRequest, DismissCheckRequest, extended CheckResult)
- backend/tests/test_verify_endpoint.py (MODIFIED — added 7 new tests)
- frontend/src/components/verify/DismissModal.tsx (NEW)
- frontend/src/components/verify/ChecksList.tsx (MODIFIED — dismissed status rendering, double-click guard, spinner, inline errors)
- frontend/src/pages/VerificationScreen.tsx (MODIFIED — handleVerifyUpdate, real API calls, DismissModal integration)
- frontend/src/types/verify.ts (MODIFIED — extended CheckResult, added request types)
