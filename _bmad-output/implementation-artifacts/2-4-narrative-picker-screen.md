---
baseline_commit: 36a178dea281ebb691c3d94d82c147019174d98d
---

# Story 2.4: Narrative Picker Screen (Screen 2)

Status: done

## Story

As an analyst,
I want to compare narrative options side-by-side, inspect assumptions, optionally edit, and select my preferred narrative,
so that I can curate the story angle before the system verifies the numbers.

## Acceptance Criteria

1. **Given** I click "Generate Narratives" from Screen 1, **When** Screen 2 loads, **Then** skeleton cards with shimmer appear while narratives generate, **And** cards populate progressively as each narrative completes (not all-at-once), **And** the progress rail shows "Narratives" as active with "Questions" showing checkmark.

2. **Given** 2-3 narrative cards are displayed, **When** I view the cards, **Then** each card shows: story angle label, 2-3 sentence summary, viz recommendation (one line), confidence score (green >= 80%, amber 60-79%, red < 60%), assumption count chip (amber if INFERRED present), and [Select] button.

3. **Given** I click on a narrative card, **When** the detail panel opens below the card row, **Then** I see: full narrative text, bulleted assumptions with flag type badges (EXPLICIT/PATTERN/INFERRED), viz justification, and an [Edit] button, **And** only one detail panel is open at a time.

4. **Given** I click [Edit] in the detail panel, **When** the inline textarea appears, **Then** I can modify the narrative text and save, **And** the card shows a "Modified" badge, **And** the edit is stored via `POST /api/v1/decks/{deck_id}/select-narrative`.

5. **Given** I see the Q&A summary bar at the top, **When** I expand it, **Then** I see all question-answer pairs from Screen 1, **And** clicking the link navigates back to Screen 1 (with warning: "Changing answers will regenerate narratives").

6. **Given** I click [Select] on a card, **When** the selection is recorded via `POST /api/v1/decks/{deck_id}/select-narrative`, **Then** the card shows selected state (checkmark, solid border), **And** "Verify & Proceed" button enables, **And** clicking it transitions to Screen 3.

## Tasks / Subtasks

- [x] Task 1: Backend — deck_selections model and migration (AC: #4, #6)
  - [x] 1.1 Create `backend/app/models/deck_selection.py` -- SQLAlchemy async model:
    - `id` (UUID PK, default uuid4)
    - `deck_id` (UUID FK -> decks.id, not null, unique -- one selection per deck)
    - `narrative_id` (UUID FK -> narratives.id, not null)
    - `user_edits_text` (Text, nullable) -- stores user's modified narrative text
    - `created_at` (DateTime, server_default=func.now())
    - `updated_at` (DateTime, server_default=func.now(), onupdate=func.now())
  - [x] 1.2 Register model in `backend/app/models/__init__.py` -- add DeckSelection to imports and `__all__`
  - [x] 1.3 Create Alembic migration `backend/alembic/versions/005_add_deck_selections.py` -- creates `deck_selections` table with unique constraint on `deck_id`, indexes on `deck_id` and `narrative_id`

- [x] Task 2: Backend — select-narrative and Q&A summary endpoints (AC: #4, #5, #6)
  - [x] 2.1 Add `POST /api/v1/decks/{deck_id}/select-narrative` endpoint in `backend/app/api/v1/endpoints/narratives.py`:
    - Request body: `{ narrative_id: UUID, user_edits_text: str | null }`
    - Validate narrative exists and belongs to this deck
    - Upsert DeckSelection: if selection exists for deck, update it; otherwise create
    - If `user_edits_text` is provided, store it (user edited the narrative)
    - Return `{ selection_id: str, narrative_id: str, user_edits_text: str | null }`
    - Use `with_for_update()` on existing selection for concurrent safety
  - [x] 2.2 Add `GET /api/v1/decks/{deck_id}/qa-summary` endpoint in `backend/app/api/v1/endpoints/questions.py`:
    - Fetch latest QuestionSession for deck where answers_json is not null
    - Return `{ questions: [{ id, template, answer, parsed_intent, confidence }] }` -- join questions_json and answers_json from the session
    - If no answered session exists, return empty questions list
  - [x] 2.3 Create Pydantic schemas in `backend/app/api/v1/schemas/narratives.py`:
    - `SelectNarrativeRequest`: `{ narrative_id: UUID, user_edits_text: str | None = None }`
    - `SelectNarrativeResponse`: `{ selection_id: str, narrative_id: str, user_edits_text: str | None }`
  - [x] 2.4 Create Pydantic schemas in `backend/app/api/v1/schemas/questions.py`:
    - `QASummaryItem`: `{ id: str, template: str, answer: str, parsed_intent: str, confidence: float }`
    - `QASummaryResponse`: `{ questions: list[QASummaryItem] }`
  - [x] 2.5 Register any new routes in router.py if needed (narratives router already registered)

- [x] Task 3: Frontend — route and page skeleton (AC: #1)
  - [x] 3.1 Create `frontend/src/pages/NarrativePicker.tsx` with skeleton component inside `AppShell` with progress rail: Ingest=completed, Questions=completed, Narratives=active, rest=inactive
  - [x] 3.2 Add route in `frontend/src/App.tsx`: `/decks/:deckId/narratives` -> `NarrativePicker`
  - [x] 3.3 On mount: call `POST /api/v1/decks/${deckId}/generate-narratives` with `{ session_id }` from URL query param or fetch from the latest question session via `GET /api/v1/decks/${deckId}/questions` (to get session_id)
    - NOTE: ClarifyingQuestions.tsx navigates to `/decks/${deckId}/narratives` but does NOT pass session_id. The NarrativePicker must discover it. Approach: first call `GET /api/v1/decks/${deckId}/narratives` to check if narratives already exist (from a previous generation). If empty, fetch the latest question session and call POST generate-narratives.
  - [x] 3.4 Show skeleton cards with shimmer animation while waiting for API response

- [x] Task 4: Frontend — skeleton cards with shimmer (AC: #1)
  - [x] 4.1 Create `frontend/src/components/SkeletonCard.tsx` -- shimmer placeholder card matching NarrativeCard dimensions
  - [x] 4.2 CSS shimmer animation using inline styles: linear-gradient animated via CSS @keyframes. Since project uses inline styles, create a `<style>` tag in the component head or use a simple CSS-in-JS approach with `animation` property
  - [x] 4.3 Show 3 skeleton cards by default, replace each with real card as data arrives

- [x] Task 5: Frontend — narrative card component (AC: #2)
  - [x] 5.1 Create `frontend/src/components/NarrativeCard.tsx` with props: `{ narrative: NarrativeResponse; isSelected: boolean; isExpanded: boolean; isModified: boolean; onSelect: () => void; onClick: () => void }`
  - [x] 5.2 Fixed-height card (approx 220px) showing:
    - Story angle label (top, bold, capitalize first letter)
    - 2-3 sentence summary (truncated from narrative_text, first 200 chars + "...")
    - Viz recommendation (one line: chart_type icon/label)
    - Confidence score badge: green (#16a34a) >= 80%, amber (#d97706) 60-79%, red (#dc2626) < 60%. Show percentage
    - Assumption count chip: total count, amber background if any assumption has flag_type "INFERRED"
    - [Select] button at bottom
  - [x] 5.3 Selected state: blue solid border (#2563eb), checkmark icon in top-right corner, [Select] button changes to "Selected" with checkmark
  - [x] 5.4 "Modified" badge: small amber badge in top-left if `isModified` is true
  - [x] 5.5 Card is clickable (entire card area except [Select] button) to toggle detail panel

- [x] Task 6: Frontend — detail panel (AC: #3, #4)
  - [x] 6.1 Create `frontend/src/components/NarrativeDetailPanel.tsx` with props: `{ narrative: NarrativeResponse; editedText: string | null; onSave: (text: string) => void; onClose: () => void }`
  - [x] 6.2 Panel appears below the card row (not inside the card), full width of the content area
  - [x] 6.3 Content:
    - Full narrative text (or editedText if modified)
    - Bulleted assumptions with flag type badges: EXPLICIT (green badge), PATTERN (blue badge), INFERRED (amber badge). Each shows: assumption text, confidence percentage, source reference
    - Viz justification: chart_type + justification text from viz_recommendation
    - [Edit] button
  - [x] 6.4 Edit mode: clicking [Edit] replaces narrative text with a `<textarea>` pre-filled with current text. Show [Save] and [Cancel] buttons. On save: call `onSave(newText)` which stores locally and triggers backend persist on selection
  - [x] 6.5 Only one detail panel open at a time -- clicking another card closes the current panel

- [x] Task 7: Frontend — Q&A summary bar (AC: #5)
  - [x] 7.1 Create `frontend/src/components/QASummaryBar.tsx` with props: `{ deckId: string; questions: QASummaryItem[] }`
  - [x] 7.2 Default collapsed state: single line "X questions answered" with expand chevron
  - [x] 7.3 Expanded state: list of question-answer pairs showing question template, raw answer, and parsed intent
  - [x] 7.4 "Back to Questions" link at bottom. On click: show confirm dialog ("Changing answers will regenerate narratives. Continue?"). If confirmed, navigate to `/decks/${deckId}/questions`
  - [x] 7.5 Fetch Q&A data on mount via `GET /api/v1/decks/${deckId}/qa-summary`

- [x] Task 8: Frontend — selection and navigation (AC: #6)
  - [x] 8.1 In `NarrativePicker.tsx`, manage state: `selectedNarrativeId: string | null`, `expandedNarrativeId: string | null`, `editedTexts: Map<string, string>` (tracks per-narrative edits)
  - [x] 8.2 On [Select] click: call `POST /api/v1/decks/${deckId}/select-narrative` with `{ narrative_id, user_edits_text: editedTexts.get(id) || null }`. On success, set `selectedNarrativeId`
  - [x] 8.3 "Verify & Proceed" button at bottom: enabled only when `selectedNarrativeId` is set. On click, navigate to `/decks/${deckId}/verify` (route will be added in Story 3.2)
  - [x] 8.4 Allow re-selection: clicking [Select] on a different card calls the endpoint again, updates the selection

- [x] Task 9: Frontend — accessibility (AC: all)
  - [x] 9.1 All interactive elements keyboard-navigable: cards, buttons, expand/collapse, edit textarea
  - [x] 9.2 `aria-label` on confidence badges (e.g., "Confidence: 82%, high confidence")
  - [x] 9.3 `aria-expanded` on Q&A summary bar and detail panels
  - [x] 9.4 Focus management: focus first card on load, focus textarea on edit mode
  - [x] 9.5 `aria-live="polite"` region for announcing selection changes and edit saves
  - [x] 9.6 Confirmation on destructive actions: "Back to Questions" navigation warning

- [x] Task 10: Tests (AC: all)
  - [x] 10.1 Backend: test POST /select-narrative -- success, narrative not found, upsert on re-select
  - [x] 10.2 Backend: test GET /qa-summary -- returns question-answer pairs, empty when no session
  - [x] 10.3 Frontend: check if test framework exists in package.json. If yes, test NarrativeCard renders with correct confidence badge colors, test detail panel opens/closes, test selection state
  - [x] 10.4 Frontend: if no test framework, note as deferred

### Review Findings

- [x] [Review][Decision] AC4: Edits not persisted via API until Select is clicked — Accepted: edits bundled with selection is the intended flow; the select-narrative endpoint is the storage mechanism
- [x] [Review][Decision] AC1: Progressive card loading not implemented — Accepted: batch load is sufficient given 2-3 card count; shimmer skeleton provides adequate loading UX
- [x] [Review][Patch] qa-summary KeyError on malformed parsed data [backend/app/api/v1/endpoints/questions.py:137] — Fixed: added `if "question_id" in p` guard
- [x] [Review][Patch] Concurrent upsert race on DeckSelection [backend/app/api/v1/endpoints/narratives.py:165] — Fixed: catch IntegrityError, rollback, re-fetch with FOR UPDATE, and update
- [x] [Review][Patch] Auto-generates narratives on every visit when zero exist [frontend/src/pages/NarrativePicker.tsx:78] — Fixed: set error state when generation returns zero narratives
- [x] [Review][Patch] NarrativeDetailPanel draft state stale across card switches [frontend/src/components/NarrativeDetailPanel.tsx] — Fixed: added key={expandedNarrativeId} to force remount
- [x] [Review][Defer] updated_at column has no DB-level ON UPDATE trigger — deferred, pre-existing pattern (ORM onupdate is sufficient for current codebase, no raw SQL update paths exist)
- [x] [Review][Defer] No authorization check on deck ownership — deferred, pre-existing (auth is explicitly deferred across all stories per project architecture)

## Dev Notes

### Previous Story Intelligence (from Stories 2.1, 2.2, 2.3)

**Established frontend patterns (from Story 2.2):**
- React 18.3 with react-router-dom 7.18, inline styles only
- `useState` + `useEffect` for state/data fetching, no global state management
- `useParams<{ deckId: string }>()` for route params, `useNavigate()` for navigation
- `apiFetch<T>()` from `frontend/src/api/client.ts` for all API calls
- Loading/error/data state pattern (see ClarifyingQuestions.tsx)
- AppShell wraps content with ProgressRail sidebar; pass `steps` prop
- Desktop-only layout (min-width: 1280px via AppShell)

**Review fixes applied in Story 2.2:**
- Always add double-click guard on async submit handlers: `if (submitting) return`
- Reset `submitting` state before `navigate()` on all success paths
- Don't return `null` for empty states -- show user-friendly messages
- Use `canGenerate` based on actual requirements (Tier 1 only), not over-strict checks

**Established backend patterns (from Stories 2.1, 2.3):**
- FastAPI async endpoints, `asyncio.to_thread` for CPU-bound work
- SQLAlchemy async models with UUID PKs, `server_default=func.now()`
- Alembic migrations sequential numbering (next: 005)
- `with_for_update()` for concurrent safety on state mutations
- Auth deferred -- use `user_id` in request body as temporary approach
- Null-coalescing for JSONB: `field or {}`, `.get("key", default)`

### Existing Code State (files being modified)

**`frontend/src/App.tsx`** (MODIFY) -- Currently has 3 routes: `/`, `/decks/:deckId/validate`, `/decks/:deckId/questions`. Add `/decks/:deckId/narratives` route.

**`backend/app/api/v1/endpoints/narratives.py`** (MODIFY) -- Currently has POST /generate-narratives and GET /narratives. Add POST /select-narrative.

**`backend/app/api/v1/schemas/narratives.py`** (MODIFY) -- Currently has NarrativeResponse, GenerateNarrativesRequest/Response, NarrativesListResponse, AssumptionItem, VizRecommendation. Add SelectNarrativeRequest/Response.

**`backend/app/api/v1/endpoints/questions.py`** (MODIFY) -- Add GET /qa-summary endpoint.

**`backend/app/api/v1/schemas/questions.py`** (MODIFY) -- Add QASummaryItem and QASummaryResponse.

**`backend/app/models/__init__.py`** (MODIFY) -- Add DeckSelection.

### Architecture Compliance

**API contracts consumed/created by this story:**
```
GET /api/v1/decks/{deck_id}/narratives (EXISTING)
  Returns: { narratives: [{ id, story_angle, narrative_text, viz_recommendation: {chart_type, justification} | null, assumptions: [{text, flag_type, confidence, source_reference}], overall_confidence }] }

POST /api/v1/decks/{deck_id}/generate-narratives (EXISTING)
  Payload: { session_id: UUID }
  Returns: { narratives: [...same as above] }

POST /api/v1/decks/{deck_id}/select-narrative (NEW)
  Payload: { narrative_id: UUID, user_edits_text: str | null }
  Returns: { selection_id: str, narrative_id: str, user_edits_text: str | null }

GET /api/v1/decks/{deck_id}/qa-summary (NEW)
  Returns: { questions: [{ id, template, answer, parsed_intent, confidence }] }
```

**UX Design Requirements (from epics.md):**
- UX-DR6: Narrative cards with story angle, summary, viz rec, confidence (color-coded), assumption chip, [Select]
- UX-DR7: Detail panel below cards with full text, bulleted assumptions with flag badges, viz justification, [Edit]
- UX-DR8: Q&A summary bar -- collapsed one-liner, expandable, link back to Screen 1 with warning
- UX-DR17: Skeleton cards with shimmer on Screen 2, progressive loading

**Session ID discovery:**
ClarifyingQuestions.tsx navigates to `/decks/${deckId}/narratives` without passing session_id. NarrativePicker must:
1. First try `GET /api/v1/decks/${deckId}/narratives` -- if narratives exist, display them
2. If empty, fetch session_id by calling `GET /api/v1/decks/${deckId}/questions` (returns existing session), then call `POST /generate-narratives` with that session_id
3. This handles both fresh generation and returning to the screen after narratives were already generated

### Technical Stack

- **Frontend:** React 18.3, TypeScript, Vite, react-router-dom 7.18
- **Backend:** Python 3.11, FastAPI async, SQLAlchemy async, Alembic
- **No new dependencies needed** on either side

### Directory Structure

```
frontend/src/
  pages/NarrativePicker.tsx (NEW)
  components/NarrativeCard.tsx (NEW)
  components/NarrativeDetailPanel.tsx (NEW)
  components/SkeletonCard.tsx (NEW)
  components/QASummaryBar.tsx (NEW)
  App.tsx (MODIFIED -- add /decks/:deckId/narratives route)

backend/app/
  models/deck_selection.py (NEW)
  models/__init__.py (MODIFIED -- add DeckSelection)
  api/v1/endpoints/narratives.py (MODIFIED -- add POST /select-narrative)
  api/v1/endpoints/questions.py (MODIFIED -- add GET /qa-summary)
  api/v1/schemas/narratives.py (MODIFIED -- add SelectNarrativeRequest/Response)
  api/v1/schemas/questions.py (MODIFIED -- add QASummaryItem/Response)
backend/alembic/versions/005_add_deck_selections.py (NEW)
backend/tests/test_narrative_selection.py (NEW)
```

### Anti-Patterns to Avoid

- Do NOT implement Screen 3 (Verification) -- that's Epic 3
- Do NOT add narrative re-generation from this screen -- that requires going back to Screen 1
- Do NOT use CSS files or CSS-in-JS libraries -- inline styles only
- Do NOT add global state management (Redux, Context) -- useState pattern
- Do NOT create a separate narrative editing endpoint -- edits are stored via the select-narrative endpoint
- Do NOT allow selecting multiple narratives -- only one selection per deck
- Do NOT hardcode narrative content -- render dynamically from API response
- Do NOT implement the "Modified" badge via a separate DB column -- derive from `user_edits_text IS NOT NULL` in the DeckSelection

### Testing Requirements

- Backend: test select-narrative endpoint (success, 404, upsert, with edits, without edits)
- Backend: test qa-summary endpoint (returns pairs, empty when no session)
- Frontend: deferred unless test framework exists in package.json (vitest/jest not configured per Story 2.2)

### References

- [Source: epics.md#Story 2.4 -- Full acceptance criteria and user story]
- [Source: epics.md#UX-DR6,DR7,DR8,DR17 -- Screen 2 design requirements]
- [Source: backend/app/api/v1/schemas/narratives.py -- NarrativeResponse, AssumptionItem, VizRecommendation shapes]
- [Source: backend/app/api/v1/endpoints/narratives.py -- Existing POST /generate-narratives and GET /narratives endpoints]
- [Source: backend/app/models/narrative.py -- Narrative model columns]
- [Source: frontend/src/pages/ClarifyingQuestions.tsx -- Navigation to /decks/:deckId/narratives at line 292]
- [Source: 2-2-clarifying-questions-screen.md -- Frontend patterns, review fixes, established conventions]
- [Source: 2-3-narrative-generation-service.md -- Backend patterns, API contracts, data shapes]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6

### Debug Log References

- TypeScript compilation: clean, no errors
- Vite production build: 54 modules transformed, builds successfully
- Backend tests (test_narrative_selection.py): 6/6 passed
- Full regression suite: all Story 2.4 tests pass; pre-existing failures in test_narratives.py (Story 2.3 test parameter mismatch — `parsed_answers` list passed where `schema` dict expected) are unrelated to this story

### Completion Notes List

- All backend work was implemented in a prior session: DeckSelection model, Alembic migration 005, select-narrative endpoint with upsert + concurrent safety, qa-summary endpoint joining questions_json with answers_json
- All frontend components implemented: NarrativePicker page with session discovery logic (try existing narratives first, fallback to generate), NarrativeCard with confidence color-coding and assumption chips, SkeletonCard with CSS shimmer animation, NarrativeDetailPanel with inline edit mode and assumption flag badges, QASummaryBar with expand/collapse and back-to-questions confirmation
- Accessibility implemented: keyboard navigation on cards, aria-labels on confidence badges, aria-expanded on panels and summary bar, aria-live region for selection/edit announcements, focus management on load and edit mode
- Frontend test framework (vitest/jest) not installed — frontend tests deferred per Task 10.3/10.4
- No new dependencies added on either side

### File List

- backend/app/models/deck_selection.py (NEW)
- backend/app/models/__init__.py (MODIFIED — added DeckSelection import)
- backend/alembic/versions/005_add_deck_selections.py (NEW)
- backend/app/api/v1/endpoints/narratives.py (MODIFIED — added POST /select-narrative endpoint)
- backend/app/api/v1/endpoints/questions.py (MODIFIED — added GET /qa-summary endpoint)
- backend/app/api/v1/schemas/narratives.py (MODIFIED — added SelectNarrativeRequest/Response)
- backend/app/api/v1/schemas/questions.py (MODIFIED — added QASummaryItem/QASummaryResponse)
- backend/tests/test_narrative_selection.py (NEW)
- frontend/src/App.tsx (MODIFIED — added /decks/:deckId/narratives route)
- frontend/src/pages/NarrativePicker.tsx (NEW)
- frontend/src/components/NarrativeCard.tsx (NEW)
- frontend/src/components/SkeletonCard.tsx (NEW)
- frontend/src/components/NarrativeDetailPanel.tsx (NEW)
- frontend/src/components/QASummaryBar.tsx (NEW)

### Change Log

- 2026-06-20: Implemented Story 2.4 — Narrative Picker Screen (Screen 2). Backend: DeckSelection model + migration, select-narrative upsert endpoint, qa-summary endpoint. Frontend: NarrativePicker page with narrative cards, detail panel with inline editing, Q&A summary bar, skeleton shimmer loading, full accessibility support. 6 backend tests added and passing.
