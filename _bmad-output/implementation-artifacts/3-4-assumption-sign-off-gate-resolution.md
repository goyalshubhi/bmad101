---
baseline_commit: 36a178dea281ebb691c3d94d82c147019174d98d
---

# Story 3.4: Assumption Sign-Off & Gate Resolution

Status: done

## Story

As an analyst,
I want to review every assumption the system made, sign off or reject each one, and only proceed to rendering when everything is resolved,
so that the deck has full human accountability for every inference.

## Acceptance Criteria

1. **Given** I view the Assumptions tab, **When** assumptions are displayed, **Then** they are grouped by flag type: EXPLICIT (display only, no action), PATTERN (requires acknowledgment), INFERRED (requires sign-off), **And** each shows the assumption text, confidence percentage, and source reference.

2. **Given** I see a PATTERN assumption, **When** I click [Acknowledge], **Then** `POST /api/v1/decks/{deck_id}/verify/assumption-action` records `{assumption_index, action: "acknowledged", user_id, created_at}` in `assumption_actions_json`, **And** the assumption shows a acknowledged state.

3. **Given** I see a PATTERN assumption, **When** I click [Challenge], **Then** the UI navigates to Screen 2 with `?highlight=assumption-{index}`, the detail panel opens with narrative text editable near the relevant passage, **And** after editing and returning to Screen 3, re-verification runs on the edited text.

4. **Given** I see an INFERRED assumption, **When** I click [Sign off], **Then** the action is recorded as `signed_off` with user attribution and timestamp.

5. **Given** I see an INFERRED assumption, **When** I click [Reject -- edit narrative], **Then** the rejection is recorded, the UI navigates to Screen 2 for narrative editing, and returning triggers re-verification.

6. **Given** the gate status bar at the bottom of Screen 3, **When** I view it, **Then** it shows remaining blockers: failed/undismissed check count + unresolved PATTERN/INFERRED assumption count, **And** "Proceed to Render" is disabled while any blocker remains, **And** it enables only when all checks pass (or dismissed) AND all PATTERN assumptions acknowledged AND all INFERRED assumptions signed off.

7. **Given** all blockers are resolved, **When** I click "Proceed to Render", **Then** an audit_log entry records `verification_completed` and the system transitions to rendering.

8. **Given** I return to Screen 3 post-render (via progress rail), **When** the screen loads in read-only mode, **Then** all action buttons are hidden, the banner shows "Verified [timestamp] - All checks pass", dismissed items show their dismissal reason, and [Download PPTX] is visible.

## Tasks / Subtasks

- [x] Task 1: Backend -- Assumption-action endpoint and schema (AC: #2, #3, #4, #5)
  - [x] 1.1 Add `AssumptionActionRequest` to `backend/app/api/v1/schemas/verify.py`:
    - `report_id: UUID`
    - `assumption_index: int`
    - `action: Literal["acknowledged", "signed_off", "rejected"]`
  - [x] 1.2 Add `AssumptionItem` response schema to `backend/app/api/v1/schemas/verify.py`:
    - `text: str`, `flag_type: str`, `confidence: float`, `source_reference: str`
  - [x] 1.3 Extend `VerifyResponse` in schemas to include `assumptions: list[AssumptionItem]` and `assumption_actions: list[dict]` (both default `[]`)
  - [x] 1.4 Add `POST /api/v1/decks/{deck_id}/verify/assumption-action` to `backend/app/api/v1/endpoints/verify.py`:
    - Fetch ReconciliationReport by `report_id` with `with_for_update()` (same pattern as dismiss-check)
    - Verify `report.deck_id == deck_id` via WHERE clause
    - Fetch the Narrative for this report via `report.narrative_id` to get `assumptions_json`
    - Validate `assumption_index` is within bounds of `assumptions_json` list (400 if out of range)
    - Validate the assumption at that index has `flag_type` compatible with the action: PATTERN -> acknowledged/rejected, INFERRED -> signed_off/rejected (400 if mismatch)
    - Deep-copy `assumption_actions_json` (or init `[]` if null), append `{assumption_index, action, user_id: PLACEHOLDER_USER_ID, created_at: utc_now_iso}`
    - `flag_modified(report, "assumption_actions_json")`
    - Create audit_log entry: action=`"assumption_action"`, details: `{assumption_index, action, flag_type}`
    - Return updated VerifyResponse (include assumptions + assumption_actions from the narrative and report)
  - [x] 1.5 Update the existing `verify_deck` and `apply_fix` endpoints to include `assumptions` and `assumption_actions` in their VerifyResponse:
    - After creating the report, fetch the narrative's `assumptions_json` (already loaded as `narrative`)
    - Return `assumptions=[AssumptionItem(**a) for a in (narrative.assumptions_json or [])]`
    - Return `assumption_actions=report.assumption_actions_json or []`
  - [x] 1.6 Update the existing `dismiss_check` endpoint similarly to include assumptions and assumption_actions in its response

- [x] Task 2: Frontend -- TypeScript types for assumptions (AC: #1-#6)
  - [x] 2.1 Add to `frontend/src/types/verify.ts`:
    - `AssumptionItem`: `{ text: string; flag_type: "EXPLICIT" | "PATTERN" | "INFERRED"; confidence: number; source_reference: string }`
    - `AssumptionAction`: `{ assumption_index: number; action: "acknowledged" | "signed_off" | "rejected"; user_id: string; created_at: string }`
    - `AssumptionActionRequest`: `{ report_id: string; assumption_index: number; action: "acknowledged" | "signed_off" | "rejected" }`
  - [x] 2.2 Extend `VerifyResponse` type: add `assumptions: AssumptionItem[]` and `assumption_actions: AssumptionAction[]`

- [x] Task 3: Frontend -- AssumptionsList component (AC: #1, #2, #3, #4, #5)
  - [x] 3.1 Create `frontend/src/components/verify/AssumptionsList.tsx`:
    - Props: `{ assumptions: AssumptionItem[]; assumptionActions: AssumptionAction[]; onAcknowledge: (index: number) => Promise<void>; onSignOff: (index: number) => Promise<void>; onChallenge: (index: number) => void; onReject: (index: number) => Promise<void>; mode: "blocking" | "readonly" }`
    - Group assumptions by `flag_type` in order: EXPLICIT, PATTERN, INFERRED
    - For each group, render a section header with group name and count
    - EXPLICIT group: display-only items (text, confidence "100%", source reference), no action buttons
    - PATTERN group: each shows text, confidence "75%", source reference, and buttons [Acknowledge] [Challenge]. If action exists for this index with action="acknowledged", show checkmark acknowledged state, hide buttons
    - INFERRED group: each shows text, confidence "40%", source reference, and buttons [Sign off] [Reject -- edit narrative]. If action exists for this index with action="signed_off", show checkmark signed-off state, hide buttons
    - Rejected assumptions: show strikethrough with "Rejected" badge (user will edit narrative on Screen 2 and re-verify)
    - Double-click guard: `submittingIndex` state to prevent concurrent actions on same assumption
    - Spinner on button while request pending
    - Inline error display on failure
    - `aria-label` on all action buttons with assumption context
    - Keyboard accessible (Tab, Enter/Space to activate)

- [x] Task 4: Frontend -- Wire AssumptionsList into VerificationScreen (AC: #1-#8)
  - [x] 4.1 Import AssumptionsList in `frontend/src/pages/VerificationScreen.tsx`
  - [x] 4.2 Replace the assumptions tab placeholder with `<AssumptionsList>` component
  - [x] 4.3 Add handler `handleAssumptionAction(index: number, action: string)`:
    - Call `POST /api/v1/decks/${deckId}/verify/assumption-action` with `{report_id, assumption_index: index, action}`
    - On success: call `handleVerifyUpdate(result)` with the updated VerifyResponse
  - [x] 4.4 Add handler `handleChallenge(index: number)`:
    - First call `handleAssumptionAction(index, "rejected")` to record the challenge
    - Then navigate to `/decks/${deckId}/narratives?highlight=assumption-${index}`
  - [x] 4.5 Add handler `handleReject(index: number)`:
    - Call `handleAssumptionAction(index, "rejected")` to record the rejection
    - Then navigate to `/decks/${deckId}/narratives?highlight=assumption-${index}`
  - [x] 4.6 Compute `unsignedAssumptionCount` from `verifyResponse`:
    - Count assumptions where `flag_type` is PATTERN or INFERRED AND no matching action exists in `assumption_actions` with action `acknowledged`/`signed_off`
    - Pass this count to TabBar and GateStatusBar (replace hardcoded `0`)
  - [x] 4.7 Update `handleVerifyUpdate` to announce assumption-related state changes via aria-live

- [x] Task 5: Frontend -- Audit log entry on gate resolution (AC: #7)
  - [x] 5.1 Update `handleProceedToRender` in VerificationScreen:
    - Before navigating to render, call `POST /api/v1/decks/${deckId}/verify/assumption-action` or add a dedicated audit endpoint
    - Alternative (simpler): add audit logging to the backend -- create a `POST /api/v1/decks/{deck_id}/verify/complete` endpoint that logs `verification_completed` to audit_log and returns 200
  - [x] 5.2 Add the `POST /api/v1/decks/{deck_id}/verify/complete` backend endpoint:
    - Fetch latest ReconciliationReport for deck
    - Validate all checks resolved (no status="fail") and all PATTERN/INFERRED assumptions have actions
    - Create audit_log entry: action=`"verification_completed"`, details: `{report_id, checks_summary, assumptions_summary}`
    - Return `{status: "ok"}`
  - [x] 5.3 Wire frontend: `handleProceedToRender` calls this endpoint, then on success navigates to `/decks/${deckId}/render`

- [x] Task 6: Backend -- Tests (AC: #2, #4, #5, #7)
  - [x] 6.1 Add tests to `backend/tests/test_verify_endpoint.py`:
    - Test POST /verify/assumption-action with valid acknowledged action -> returns updated assumption_actions
    - Test POST /verify/assumption-action with valid signed_off action
    - Test POST /verify/assumption-action with invalid assumption_index -> 400
    - Test POST /verify/assumption-action with mismatched action/flag_type (e.g., signed_off on PATTERN) -> 400
    - Test POST /verify/assumption-action with invalid report_id -> 404
    - Test POST /verify/complete -> creates audit_log entry
    - Test POST /verify/complete with unresolved blockers -> 400
    - Test that verify_deck response now includes assumptions and assumption_actions fields

### Review Findings

- [x] [Review][Patch] Read-only mode post-render never activated — stubbed via `?mode=readonly` query param. VerificationScreen reads param, passes `mode="readonly"` to AssumptionsList/GateStatusBar/ModeBanner. Epic 4 passes the param when navigating back. [VerificationScreen.tsx]
- [x] [Review][Patch] `verify_complete` returns "ok" even when `db.commit()` fails — added `raise HTTPException(500)` in except block [verify.py]
- [x] [Review][Patch] Challenge button bypasses double-click guard — added `challengeSubmitting` state guard in handleChallenge [VerificationScreen.tsx]
- [x] [Review][Patch] Duplicate actions on same assumption index not prevented — added check for existing acknowledged/signed_off action before appending [verify.py]
- [x] [Review][Defer] Stale assumption_actions after re-verify reference current narrative assumptions — architectural pattern: assumptions stored on Narrative, not snapshotted on report — deferred, pre-existing design
- [x] [Review][Defer] `verify_complete` TOCTOU race — no `with_for_update()` on report fetch, concurrent modifications possible — deferred, MVP acceptable
- [x] [Review][Defer] `verify_complete` uses "latest" report not user-viewed report — no `report_id` parameter, relies on ordering by `verified_at DESC` — deferred, MVP acceptable
- [x] [Review][Defer] Audit log creation pattern may cause commit failure — `db.add(audit_entry)` inside try but `db.commit()` outside — deferred, pre-existing pattern from Stories 3.1-3.3
- [x] [Review][Defer] `passed` field inconsistent comparison across endpoints — `verify_deck` uses `== "pass"`, others use `!= "fail"` — deferred, pre-existing from Story 3.1
- [x] [Review][Defer] `verify_complete` sets no completion flag on report — audit log serves as record, no `completed_at` field — deferred, design enhancement beyond scope

## Dev Notes

### Epic 3 Cross-Story Shared Components -- REUSE, DO NOT DUPLICATE

| Component | Created by | This story's usage |
|---|---|---|
| `ReconciliationReport` model | Story 3.1 | Read/update `assumption_actions_json` field (already exists, currently null) |
| `ReconciliationReport.assumption_actions_json` | Story 3.1 (column), Story 3.4 (populates) | Append action entries to this JSONB array |
| `backend/app/api/v1/endpoints/verify.py` | Story 3.1 | Add assumption-action and verify-complete endpoints to this EXISTING file |
| `backend/app/api/v1/schemas/verify.py` | Story 3.1 | Add AssumptionActionRequest, AssumptionItem to this EXISTING file; extend VerifyResponse |
| `Narrative.assumptions_json` | Story 2.3 | Read assumptions from the narrative model -- do NOT duplicate |
| `backend/app/services/narratives/assumption_extractor.py` | Story 2.3 | Produces assumption dicts with shape: `{text, flag_type, confidence, source_reference}` |
| `ModeBanner` component | Story 3.2 | No changes needed |
| `TabBar` component | Story 3.2 | Badge count updates automatically from props |
| `GateStatusBar` component | Story 3.2 | Already accepts `unsignedAssumptionCount` and factors it into blocker calculation |
| `ChecksList` component | Story 3.2 + 3.3 | No changes needed |
| `VerificationScreen` page | Story 3.2 + 3.3 | Replace assumptions placeholder, compute real assumption counts, add handlers |
| `apiFetch` utility | Story 1.1 | Import from `frontend/src/api/client.ts` |
| `DismissModal` component | Story 3.3 | No changes needed |

### Stories 3.1-3.3 Dependency -- CRITICAL

This story MUST be implemented after Stories 3.1, 3.2, and 3.3. They create:
- Story 3.1: ReconciliationReport model (with `assumption_actions_json` field), verify services, POST /verify endpoint
- Story 3.2: VerificationScreen page, all verify components (TabBar, GateStatusBar, etc.), placeholder Assumptions tab
- Story 3.3: Apply-fix and dismiss-check endpoints, DismissModal, wired action buttons

### Previous Story Intelligence

**Key patterns from Stories 3.1-3.3 to follow:**
- `with_for_update()` for concurrent safety on state mutations (dismiss_check pattern)
- Deep copy JSONB + `flag_modified()` for reliable dirty tracking (dismiss_check pattern in verify.py lines 324-343)
- `PLACEHOLDER_USER_ID = "00000000-0000-0000-0000-000000000000"` for auth-deferred user_id
- `asyncio.to_thread()` for CPU-bound work (not needed here -- assumption-action is lightweight DB ops)
- Double-click guard: `if (submitting) return` on frontend async operations
- Inline styles only (no CSS modules, no Tailwind)
- `useState` / `useEffect` pattern, no Redux/context
- `useParams<{ deckId: string }>()`, `useNavigate()` for routing
- Audit log creation in try/except with warning log on failure (verify.py pattern lines 90-100)
- Inline error display in frontend components (ChecksList pattern)
- `import json as _json; checks = _json.loads(_json.dumps(...))` for deep copy of JSONB (verify.py line 324-325)

**Review fixes from Stories 3.1-3.3 to apply proactively:**
- Always validate `report.deck_id == deck_id` via WHERE clause (not just report_id)
- Always add double-click guard on async operations
- Use `with_for_update()` on reads that precede writes
- Log audit errors with warning, don't bare `pass`
- Use `flag_modified()` after any JSONB mutation

### Architecture Compliance

**API contract for assumption-action (from Architecture Section 5):**
```
POST /api/v1/decks/{deck_id}/verify/assumption-action
  Payload: {report_id: UUID, assumption_index: int, action: "acknowledged"|"signed_off"|"rejected"}
  Returns: updated VerifyResponse (with assumptions and assumption_actions included)
```

**assumption_actions_json shape (from Architecture Section 12, Gap 1):**
```json
[
  {
    "assumption_index": 0,
    "action": "acknowledged",
    "user_id": "00000000-0000-0000-0000-000000000000",
    "created_at": "2026-06-21T14:30:00Z"
  }
]
```

**Assumptions from Narrative.assumptions_json shape (from assumption_extractor.py):**
```json
[
  {
    "text": "Analysis is based on 500 rows and 12 columns.",
    "flag_type": "EXPLICIT",
    "confidence": 1.0,
    "source_reference": "data_loader: dataset dimensions"
  },
  {
    "text": "'revenue' shows increasing trend (R-squared: 0.832).",
    "flag_type": "PATTERN",
    "confidence": 0.75,
    "source_reference": "angle_detector: trend on revenue"
  },
  {
    "text": "Analysis covers 5 of 12 columns. 7 column(s) may contain additional insights.",
    "flag_type": "INFERRED",
    "confidence": 0.40,
    "source_reference": "angle_detector: column coverage"
  }
]
```

**Gate resolution logic (complete):**
- Check blockers: count checks with `status === "fail"` (pass and dismissed are resolved)
- Assumption blockers: count assumptions where `flag_type` is PATTERN or INFERRED AND no matching entry in `assumption_actions` with `action` being `acknowledged` or `signed_off`
- EXPLICIT assumptions require NO action (display only)
- Rejected assumptions are NOT blockers -- the user is expected to edit the narrative on Screen 2 and re-verify, which creates a new report with fresh assumptions
- "Proceed to Render" enables when check blockers + assumption blockers === 0

**Challenge/Reject flow (Architecture Section 12, Gap 5):**
1. User clicks [Challenge] (PATTERN) or [Reject] (INFERRED)
2. Action recorded in `assumption_actions_json` as `rejected`
3. UI navigates to Screen 2: `/decks/${deckId}/narratives?highlight=assumption-${index}`
4. User edits narrative text manually, saved to `deck_selections.user_edits_text`
5. User clicks "Verify & Proceed" -> returns to Screen 3
6. VerificationScreen re-runs POST /verify on mount -> creates new ReconciliationReport from edited text
7. New report has fresh assumptions (re-extracted from edited narrative), `assumption_actions_json` starts null

**VerifyResponse extension -- include assumptions data:**
The current VerifyResponse does NOT include assumptions. This story must extend it:
- Add `assumptions: list[AssumptionItem]` -- sourced from `Narrative.assumptions_json` via `report.narrative_id`
- Add `assumption_actions: list[dict]` -- sourced from `ReconciliationReport.assumption_actions_json`
- ALL endpoints that return VerifyResponse must include these fields (verify_deck, apply_fix, dismiss_check, assumption_action)

### File Structure

```
backend/app/
  api/v1/endpoints/verify.py (MODIFIED -- add assumption-action and verify-complete endpoints; update verify_deck, apply_fix, dismiss_check to include assumptions in response)
  api/v1/schemas/verify.py (MODIFIED -- add AssumptionActionRequest, AssumptionItem; extend VerifyResponse)

frontend/src/
  components/verify/AssumptionsList.tsx (NEW)
  pages/VerificationScreen.tsx (MODIFIED -- replace placeholder, compute assumption counts, add handlers)
  types/verify.ts (MODIFIED -- add assumption types, extend VerifyResponse)
```

### Anti-Patterns to Avoid

- Do NOT create a new router file for assumption endpoints -- add to existing `verify.py`
- Do NOT create a new schema file -- add to existing `schemas/verify.py`
- Do NOT duplicate `Narrative.assumptions_json` loading -- fetch it via the narrative model already loaded
- Do NOT create CSS files -- inline styles only
- Do NOT use React context or Redux -- useState in page component
- Do NOT skip `with_for_update()` on the assumption-action report read
- Do NOT skip `flag_modified()` after mutating `assumption_actions_json`
- Do NOT use `json.dumps/loads` import at top level -- follow existing pattern of `import json as _json` inside function
- Do NOT mark EXPLICIT assumptions as blockers in the gate count -- they are display-only
- Do NOT treat rejected assumptions as blockers -- the re-verify after narrative edit will produce fresh assumptions
- Do NOT create a separate Alembic migration -- `assumption_actions_json` column already exists (Story 3.1)
- Do NOT implement read-only mode toggle from scratch -- GateStatusBar already supports `mode="readonly"` prop
- Do NOT hardcode assumption counts to 0 anymore -- compute from verifyResponse data

### Testing Requirements

- Backend unit tests for assumption-action: valid acknowledge on PATTERN, valid sign_off on INFERRED, rejected action, invalid index (400), mismatched action/flag_type (400), invalid report_id (404)
- Backend unit tests for verify-complete: creates audit_log, rejects when blockers remain (400)
- Backend test that verify_deck response includes assumptions and assumption_actions
- Frontend manual testing:
  1. Open Assumptions tab -- verify EXPLICIT/PATTERN/INFERRED grouping
  2. Click [Acknowledge] on PATTERN -- verify checkmark state, button disappears
  3. Click [Sign off] on INFERRED -- verify checkmark state, button disappears
  4. Click [Challenge] on PATTERN -- verify navigation to Screen 2 with highlight param
  5. Click [Reject] on INFERRED -- verify navigation to Screen 2
  6. After editing narrative on Screen 2 and returning, verify fresh assumptions load
  7. Resolve all assumptions + checks -- verify gate status bar updates, "Proceed to Render" enables
  8. Click "Proceed to Render" -- verify audit_log entry and navigation to render page
  9. Keyboard test: Tab through assumption items and buttons, Enter/Space to activate
  10. Tab badge: verify Assumptions tab badge shows correct unsigned count

### References

- [Source: epics.md#Story 3.4 -- Full acceptance criteria and user story]
- [Source: epics.md#FR20 -- Per-assumption sign-off tracking]
- [Source: epics.md#FR21 -- Assumption rejection -> narrative edit -> re-verify round-trip]
- [Source: epics.md#FR16 -- Block rendering on check failure (extended with assumption blockers)]
- [Source: epics.md#UX-DR15 -- Assumptions list grouped by flag type with action buttons]
- [Source: epics.md#UX-DR16 -- Gate status bar with assumption + check blocker counts]
- [Source: ARCHITECTURE-Technical-Design.md#Section 5 -- POST /verify/assumption-action endpoint spec]
- [Source: ARCHITECTURE-Technical-Design.md#Section 12 Gap 1 -- assumption_actions_json shape and column]
- [Source: ARCHITECTURE-Technical-Design.md#Section 12 Gap 5 -- Challenge/reject -> narrative edit round-trip flow]
- [Source: EXPERIENCE.md#Screen 3 Assumptions tab -- UX layout with grouped assumptions and action buttons]
- [Source: EXPERIENCE.md#Screen 3 Gate status bar -- Blocker counts include unsigned assumptions]
- [Source: backend/app/services/narratives/assumption_extractor.py -- Assumption shape: {text, flag_type, confidence, source_reference}]
- [Source: backend/app/models/narrative.py -- Narrative.assumptions_json field]
- [Source: backend/app/models/reconciliation_report.py -- ReconciliationReport.assumption_actions_json field (already exists, nullable)]
- [Source: backend/app/api/v1/endpoints/verify.py -- Existing verify endpoints to extend]
- [Source: backend/app/api/v1/schemas/verify.py -- Existing verify schemas to extend]
- [Source: frontend/src/pages/VerificationScreen.tsx -- Current placeholder at line 347-360, hardcoded unsignedAssumptionCount=0 at lines 306 and 375]
- [Source: frontend/src/components/verify/GateStatusBar.tsx -- Already accepts unsignedAssumptionCount prop]
- [Source: frontend/src/types/verify.ts -- Types to extend with assumption types]
- [Source: 3-3-fix-dismiss-re-verify-flow.md -- with_for_update, flag_modified, deep-copy JSONB patterns]
- [Source: 3-2-verification-screen-figures-checks-tabs.md -- VerificationScreen structure, component architecture]
- [Source: 3-1-figure-extraction-reconciliation-checks-service.md -- ReconciliationReport model, verify endpoint]

## Dev Agent Record

### Agent Model Used
Claude Sonnet 4.6

### Debug Log References
- All 26 backend verify tests pass (15 existing + 11 new) -- zero regressions
- 21 pre-existing test failures in test_narratives.py and test_questions.py are unrelated to this story
- Frontend TypeScript compiles cleanly with `tsc --noEmit`
- Full backend suite: 125 passed, 21 failed (all pre-existing)

### Completion Notes List
- Task 1: Added AssumptionActionRequest and AssumptionItem Pydantic schemas; extended VerifyResponse with assumptions and assumption_actions fields; added POST /verify/assumption-action endpoint with with_for_update(), flag_modified(), validation of flag_type/action compatibility; added POST /verify/complete endpoint with gate resolution validation (checks + assumptions); updated verify_deck, apply_fix, dismiss_check endpoints to include assumptions in response via shared _build_verify_response helper and _load_narrative_assumptions utility
- Task 2: Added AssumptionItem, AssumptionAction, AssumptionActionRequest TypeScript types; extended VerifyResponse type
- Task 3: Created AssumptionsList component with EXPLICIT/PATTERN/INFERRED grouping, action buttons per flag type, double-click guard (submittingIndex state), acknowledged/signed-off/rejected state rendering, inline error display, aria-labels on all buttons
- Task 4: Wired AssumptionsList into VerificationScreen replacing placeholder; computed real unsignedAssumptionCount from verifyResponse; added handleAssumptionAction, handleAcknowledge, handleSignOff, handleChallenge, handleReject handlers; updated handleVerifyUpdate to announce assumption state changes; replaced hardcoded 0 with computed count in TabBar and GateStatusBar
- Task 5: handleProceedToRender now calls POST /verify/complete before navigating to render; backend endpoint validates all checks resolved and all PATTERN/INFERRED assumptions have actions before creating audit_log entry
- Task 6: Added 11 new tests -- assumption-action (acknowledge, sign_off, rejected, invalid_index 400, mismatched action/flag_type 400, explicit_no_action 400, invalid_report 404), verify-complete (creates audit_log, 400 unresolved checks, 400 unresolved assumptions), verify_response_includes_assumptions

### Change Log
- 2026-06-21: Implemented Story 3.4 -- Assumption Sign-Off & Gate Resolution. Added assumption-action endpoint, verify-complete endpoint, AssumptionsList component, real assumption count computation, challenge/reject navigation flow, 11 backend tests

### File List
- backend/app/api/v1/schemas/verify.py (MODIFIED -- added AssumptionActionRequest, AssumptionItem; extended VerifyResponse)
- backend/app/api/v1/endpoints/verify.py (MODIFIED -- added assumption-action and verify-complete endpoints; added _build_verify_response and _load_narrative_assumptions helpers; updated verify_deck, apply_fix, dismiss_check to include assumptions)
- backend/tests/test_verify_endpoint.py (MODIFIED -- added 11 new tests for assumption-action and verify-complete)
- frontend/src/types/verify.ts (MODIFIED -- added AssumptionItem, AssumptionAction, AssumptionActionRequest; extended VerifyResponse)
- frontend/src/components/verify/AssumptionsList.tsx (NEW)
- frontend/src/pages/VerificationScreen.tsx (MODIFIED -- replaced placeholder, computed assumption counts, added assumption handlers, updated handleVerifyUpdate announcements)
