# Story 2.2: Clarifying Questions Screen (Screen 1)

Status: ready-for-dev

## Story

As an analyst,
I want to see one question at a time with smart suggestions and confidence feedback on my answers,
so that I can quickly tell the system what matters without second-guessing whether it understood me.

## Acceptance Criteria

1. **Given** I have completed data validation sign-off, **When** Screen 1 loads, **Then** I see the progress rail with "Questions" highlighted as active and "Ingest" showing checkmark, **And** I see the data context strip showing filename, row/column counts, and acknowledged issues count, **And** the first question card is displayed with data observation, question text, free-text input, and suggestion chips.

2. **Given** I am viewing an active question card, **When** I click a suggestion chip, **Then** the chip text populates the free-text input field (editable, not submitted).

3. **Given** I submit an answer (Enter or button), **When** the parsed confidence is >= 70%, **Then** the question collapses into the answered stack showing raw answer, parsed intent, and green confidence badge, **And** the next question becomes active.

4. **Given** I submit an answer, **When** the parsed confidence is < 70%, **Then** a clarifying follow-up appears inline below my answer ("I'm not sure I understood -- did you mean X or Y?"), **And** I can provide a clarifying response before the question collapses.

5. **Given** I click "Skip -- use default" on a question, **When** the skip is processed, **Then** the system fills its best guess, marks the answer as `defaulted`, and advances to the next question.

6. **Given** I click [Edit] on a question in the answered stack, **When** the question card re-opens, **Then** my previous answer is pre-filled and I can modify and resubmit.

7. **Given** all questions are answered or skipped, **When** at least Tier 1 questions are resolved, **Then** "Generate Narratives" button enables, **And** clicking it shows a loading state ("Analyzing data and generating narrative options...") and transitions to Screen 2.

## Tasks / Subtasks

- [ ] Task 1: Add route and navigation wiring (AC: #1, #7)
  - [ ] 1.1 Create `frontend/src/pages/ClarifyingQuestions.tsx` with skeleton component that renders inside `AppShell` with correct progress rail steps (Ingest=completed, Questions=active, rest=inactive)
  - [ ] 1.2 Add route in `frontend/src/App.tsx`: `/decks/:deckId/questions` -> `ClarifyingQuestions`
  - [ ] 1.3 In `frontend/src/pages/ValidationReview.tsx`, wire "Proceed to Questions" button with `useNavigate()` to navigate to `/decks/${deckId}/questions` (currently the button does nothing)

- [ ] Task 2: Data context strip component (AC: #1)
  - [ ] 2.1 Create `frontend/src/components/DataContextStrip.tsx` -- persistent banner at top of page showing: filename (from ingest job), row count, column count, acknowledged issues count
  - [ ] 2.2 Props: `{ fileName: string; rowCount: number; columnCount: number; issuesCount: number }`
  - [ ] 2.3 Style: subtle background (#f9fafb), bottom border, horizontal layout with pipe separators, 14px font

- [ ] Task 3: Fetch questions and ingest context on mount (AC: #1)
  - [ ] 3.1 On `ClarifyingQuestions` mount, fetch `GET /api/v1/decks/${deckId}/ingest-status` to get schema (row/column counts, filename) and quality report (issues count) for the DataContextStrip
  - [ ] 3.2 Fetch `GET /api/v1/decks/${deckId}/questions` to get `{ session_id, questions[] }`. Store `session_id` in state for later answer submission
  - [ ] 3.3 Guard: if ingest-status returns no validated job, show error and link back to validation page
  - [ ] 3.4 Show loading skeleton while both fetches complete

- [ ] Task 4: Question card component -- active state (AC: #1, #2, #3)
  - [ ] 4.1 Create `frontend/src/components/QuestionCard.tsx` with props: `{ question: QuestionResponse; onSubmit: (text: string) => void; onSkip: () => void; initialValue?: string }`
  - [ ] 4.2 Display: data observation (`question.context`), question text (`question.template`), auto-growing `<textarea>` for free-text input, suggestion chips row
  - [ ] 4.3 Suggestion chips: render each `question.suggestion_chips` item as a clickable chip button. On click, populate the textarea (don't submit). Style: pill shape, light blue bg (#eff6ff), blue text (#2563eb), hover darken
  - [ ] 4.4 Submit: Enter key (without Shift) or "Submit Answer" button. Disable submit when textarea is empty
  - [ ] 4.5 Skip: "Skip -- use default" button below the textarea. On click, call `onSkip()`
  - [ ] 4.6 Textarea auto-grow: use `onInput` to resize height based on scrollHeight. Min 2 rows, max 6 rows

- [ ] Task 5: Answered stack component (AC: #3, #5, #6)
  - [ ] 5.1 Create `frontend/src/components/AnsweredCard.tsx` with props: `{ question: QuestionResponse; answer: ParsedAnswerLocal; onEdit: () => void }`
  - [ ] 5.2 Collapsed card shows: question template (truncated), raw answer text, parsed intent label, confidence badge, [Edit] link
  - [ ] 5.3 Confidence badge: green (#16a34a) with checkmark for >= 70%, amber (#d97706) with warning icon for < 70%
  - [ ] 5.4 Defaulted answers show "Skipped -- using default" in grey italic instead of raw answer text
  - [ ] 5.5 [Edit] link: on click, calls `onEdit()` which re-opens the question as active card with previous answer pre-filled via `initialValue`

- [ ] Task 6: Answer submission and state machine (AC: #3, #4, #5)
  - [ ] 6.1 In `ClarifyingQuestions.tsx`, manage state: `activeQuestionIndex`, `answeredQuestions: Map<string, ParsedAnswerLocal>`, `sessionId`, `questions[]`, `followUpActive: boolean`, `followUpQuestionId: string | null`
  - [ ] 6.2 On answer submit: call `POST /api/v1/decks/${deckId}/answer-questions` with `{ session_id, answers: [{ question_id, text }] }`. NOTE: the current backend endpoint expects ALL answers at once and prevents resubmission (409 if answers already submitted). Two approaches:
    - **Option A (recommended):** Collect all answers locally, submit in batch when all questions answered. Display confidence feedback from local keyword matching (mirror backend logic) for immediate UX, then validate with backend call at the end.
    - **Option B:** Modify backend to support incremental answer submission (out of scope for this story -- would require backend changes).
    - Use Option A: implement a lightweight client-side confidence estimator that mirrors the backend keyword patterns for instant feedback, then submit all answers in one batch to the backend when complete.
  - [ ] 6.3 Client-side confidence estimator in `frontend/src/utils/confidenceEstimator.ts`:
    - Mirror the 8 keyword patterns from `backend/app/services/questions/parser.py`:
      - `profit|margin|profitability` -> (PROFIT, 0.9)
      - `revenue|sales|growth` -> (GROWTH, 0.85)
      - `cost|spending|efficiency` -> (COST, 0.9)
      - `market|share|position` -> (MARKET, 0.8)
      - `board|directors|governance` -> (BOARD, 0.9)
      - `investors|shareholders` -> (INVESTORS, 0.85)
      - `executive|leadership|c-suite` -> (EXECUTIVE, 0.85)
      - `operations|ops|team` -> (OPERATIONS, 0.8)
    - Empty or "skip" -> (DEFAULT, 0.0, defaulted=true)
    - No match -> (UNKNOWN, 0.5)
    - Return `{ parsed_intent, confidence, defaulted }`
  - [ ] 6.4 On submit: run client-side estimator. If confidence >= 0.7, collapse to answered stack, advance to next question. If confidence < 0.7, set `followUpActive = true` for that question
  - [ ] 6.5 On skip: set answer as `{ text: "skip", parsed_intent: "DEFAULT", confidence: 0.0, defaulted: true }`, collapse and advance

- [ ] Task 7: Low-confidence follow-up flow (AC: #4)
  - [ ] 7.1 When `followUpActive` is true for current question, show a clarifying prompt inline below the original answer: "I'm not sure I understood -- did you mean X or Y?" where X and Y are derived from the question's `suggestion_chips` (first two chips, or "one of the suggested options" if no chips)
  - [ ] 7.2 Show a second textarea for clarifying response, plus "Clarify" submit button
  - [ ] 7.3 On clarify submit: re-run confidence estimator on the new text. Collapse question regardless of new confidence (user gets one follow-up chance). Store the clarified answer as the final answer
  - [ ] 7.4 Show the follow-up section with a subtle yellow/amber left border to visually distinguish it

- [ ] Task 8: Generate Narratives button and transition (AC: #7)
  - [ ] 8.1 Below the question flow, show "Generate Narratives" button. Enabled only when all questions are answered or skipped AND all Tier 1 questions resolved (check `question.tier === 1` and has an answer in `answeredQuestions`)
  - [ ] 8.2 On click: first submit all answers to backend via `POST /api/v1/decks/${deckId}/answer-questions` with `{ session_id, answers: [...all collected answers] }`. On success, verify `ready_to_generate === true` from response
  - [ ] 8.3 Show loading overlay: "Analyzing data and generating narrative options..." with a spinner
  - [ ] 8.4 On success: navigate to `/decks/${deckId}/narratives` (route will be added in Story 2.4 -- for now navigate and let it 404 gracefully)
  - [ ] 8.5 On error: show inline error banner, keep button enabled for retry

- [ ] Task 9: Edit re-open flow (AC: #6)
  - [ ] 9.1 When user clicks [Edit] on answered card: set `activeQuestionIndex` to that question's index, remove it from `answeredQuestions` map
  - [ ] 9.2 Pre-fill the textarea with previous raw answer text via `initialValue` prop
  - [ ] 9.3 Questions below the re-opened one in the answered stack remain visible (don't re-ask them)
  - [ ] 9.4 IMPORTANT: Since backend prevents resubmission (409), editing requires creating a new question session. On edit: call `GET /api/v1/decks/${deckId}/questions` again to get a fresh `session_id`. Repopulate questions (should be same set since same data). Preserve all previously collected local answers. This ensures the final batch submit uses a fresh session.

- [ ] Task 10: Accessibility (AC: all)
  - [ ] 10.1 All interactive elements keyboard-navigable: textarea, chips, buttons, edit links
  - [ ] 10.2 `aria-label` on confidence badges (e.g., "Confidence: 85%, high confidence")
  - [ ] 10.3 Focus management: auto-focus textarea when new question becomes active or when follow-up appears
  - [ ] 10.4 `aria-live="polite"` region for announcing question transitions and follow-up prompts
  - [ ] 10.5 Proper heading hierarchy: h1 for page title, h2 for sections

- [ ] Task 11: Tests (AC: all)
  - [ ] 11.1 Create `frontend/src/__tests__/ClarifyingQuestions.test.tsx` (or co-located test file if project uses that pattern)
  - [ ] 11.2 Test: page renders with progress rail showing Questions active
  - [ ] 11.3 Test: data context strip shows correct metadata
  - [ ] 11.4 Test: suggestion chip click populates textarea
  - [ ] 11.5 Test: submit answer with high confidence -> collapses to answered stack
  - [ ] 11.6 Test: submit answer with low confidence -> shows follow-up
  - [ ] 11.7 Test: skip button sets defaulted answer and advances
  - [ ] 11.8 Test: edit re-opens question with pre-filled answer
  - [ ] 11.9 Test: Generate Narratives button disabled until all questions resolved
  - [ ] 11.10 Test: confidence estimator returns correct intents for known keywords

## Dev Notes

### Previous Story Intelligence (from Story 2.1)

**Established patterns to follow:**
- FastAPI async endpoints with `asyncio.to_thread` for synchronous I/O
- SQLAlchemy async models with UUID primary keys, `server_default=func.now()`
- Pydantic schemas in `backend/app/api/v1/schemas/` with `model_config = {"populate_by_name": True}`
- API router in `backend/app/api/v1/endpoints/`, registered in `router.py`
- Auth deferred -- use `user_id` in request body as temporary approach
- `with_for_update()` for concurrent safety on state transitions

**Review findings from Story 2.1 (and 1.4):**
- Guard against unexpected status values -- add allowlist checks
- Handle null-coalescing for optional JSONB fields
- No 404 catch-all route exists in React Router yet (deferred)
- `Content-Type` header forced to JSON on all requests in `client.ts` -- this is fine for this story (no file uploads)
- Backend `POST /answer-questions` prevents resubmission (returns 409 if `answers_json` is not null). Frontend must handle this by using a fresh session on edit flows.

### Existing Code State (files being modified)

**`frontend/src/App.tsx`** (MODIFY) -- Currently has 2 routes: `/` (Home) and `/decks/:deckId/validate` (ValidationReview). Add `/decks/:deckId/questions` route pointing to new ClarifyingQuestions page.

**`frontend/src/pages/ValidationReview.tsx`** (MODIFY) -- The "Proceed to Questions" button (line 218-230) currently does nothing (no onClick). Wire it with `useNavigate()` from react-router-dom to navigate to `/decks/${deckId}/questions`. Import `useNavigate` at top.

**`frontend/src/api/client.ts`** (READ ONLY) -- `apiFetch<T>(path, init?)` is the HTTP wrapper. Throws `ApiError` on non-2xx. Always sets `Content-Type: application/json`. Use this for all API calls.

**`frontend/src/layouts/AppShell.tsx`** (READ ONLY) -- Wraps content with ProgressRail sidebar. Pass `steps` prop with status per stage. Pattern from ValidationReview: define `pipelineSteps()` function returning step array.

**`frontend/src/components/ProgressRail.tsx`** (READ ONLY) -- Takes `steps: { label, status }[]`. Status: "completed" | "active" | "inactive". Renders vertical nav with icons.

### Architecture Compliance

**API contracts consumed by this story:**
```
GET /api/v1/decks/{deck_id}/questions
  Returns: { session_id: string, questions: [{ id, template, context, suggestion_chips: string[], tier: int }] }

POST /api/v1/decks/{deck_id}/answer-questions
  Payload: { session_id: UUID, answers: [{ question_id: string, text: string }] }
  Returns: { parsed: [{ question_id, raw_answer, parsed_intent, confidence, defaulted }], ready_to_generate: bool }
  IMPORTANT: Returns 409 if answers already submitted for this session

GET /api/v1/decks/{deck_id}/ingest-status
  Returns: { ingest_job_id, schema: { columns, row_count }, quality_report: { status, issues }, status, validated_at }
```

**UX Design Requirements (from epics.md):**
- UX-DR1: Progress rail with "Questions" highlighted, "Ingest" showing checkmark
- UX-DR2: Data context strip -- filename, row/column counts, acknowledged issues count
- UX-DR3: Question card -- one active at a time, data observation, question text, textarea, suggestion chips, skip button
- UX-DR4: Answered stack -- collapsed cards with raw answer, parsed intent, confidence badge, edit link
- UX-DR5: Low-confidence follow-up -- inline clarifying prompt when confidence < 70%

**Frontend patterns (from existing codebase):**
- React 18.3 with react-router-dom 7.18
- Inline styles (no CSS modules or styled-components in use)
- `useState` + `useEffect` for state and data fetching (no global state management)
- `useParams<{ deckId: string }>()` for route params
- `apiFetch<T>()` for API calls with ApiError handling
- Loading/error/data state pattern (see ValidationReview.tsx for reference)
- Desktop-only layout (min-width: 1280px via AppShell)

### Technical Stack

- **Frontend:** React 18.3, TypeScript, Vite, react-router-dom 7.18
- **No new dependencies needed** -- all UI is built with native React and inline styles
- **Testing:** Check if vitest or jest is configured in `frontend/package.json`. If vitest: use `@testing-library/react`. If no test framework: skip tests or add vitest + @testing-library/react as devDependencies

### Directory Structure

```
frontend/src/
  pages/ClarifyingQuestions.tsx (NEW)
  components/DataContextStrip.tsx (NEW)
  components/QuestionCard.tsx (NEW)
  components/AnsweredCard.tsx (NEW)
  utils/confidenceEstimator.ts (NEW)
  App.tsx (MODIFIED -- add /decks/:deckId/questions route)
  pages/ValidationReview.tsx (MODIFIED -- wire Proceed to Questions button)
  __tests__/ClarifyingQuestions.test.tsx (NEW -- if test framework exists)
```

### Anti-Patterns to Avoid

- Do NOT create backend changes -- this is a frontend-only story
- Do NOT implement Screen 2 (Narrative Picker) -- that's Story 2.4
- Do NOT add global state management (Redux, Context) -- follow existing useState pattern
- Do NOT use CSS-in-JS libraries or CSS modules -- use inline styles to match existing codebase
- Do NOT hardcode question text -- render dynamically from API response
- Do NOT call the answer endpoint per-question -- batch all answers in one call at the end (backend prevents resubmission)
- Do NOT implement actual narrative generation -- just navigate to the narratives route
- Do NOT add a 404 catch-all route -- that's deferred per previous review findings
- Do NOT create a separate types file for question/answer types -- define locally in the page component or utils, matching the Pydantic schema shapes

### Testing Requirements

- Check `frontend/package.json` for existing test framework (vitest, jest, @testing-library/react)
- If test framework exists: write component tests for the key flows
- If no test framework: note in completion that tests are deferred pending framework setup
- Test the confidence estimator as a pure function (no DOM needed)

### Project Structure Notes

- All new files go under `frontend/src/` following existing conventions
- Components in `frontend/src/components/`, pages in `frontend/src/pages/`
- New utility in `frontend/src/utils/` (new directory -- create it)
- Route follows pattern: `/decks/:deckId/questions` (matches `/decks/:deckId/validate` pattern)

### References

- [Source: epics.md#Story 2.2 -- Full acceptance criteria and user story]
- [Source: epics.md#UX Design Requirements -- UX-DR1 through UX-DR5]
- [Source: epics.md#Additional Requirements -- React frontend, desktop viewport 1280px+]
- [Source: 2-1-question-generation-answer-parsing-service.md -- Previous story patterns, API contracts, review findings]
- [Source: backend/app/api/v1/schemas/questions.py -- Pydantic response models defining API shapes]
- [Source: backend/app/api/v1/endpoints/questions.py -- 409 resubmission guard on POST /answer-questions]
- [Source: frontend/src/pages/ValidationReview.tsx -- Reference implementation for page pattern, AppShell usage, API fetching]
- [Source: frontend/src/api/client.ts -- apiFetch wrapper and ApiError class]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
