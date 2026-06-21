---
stepsCompleted: ["step-01-validate-prerequisites", "step-02-design-epics", "step-03-create-stories"]
inputDocuments:
  - _bmad-output/planning-artifacts/PRD-Automated-Deck-Generation.md
  - _bmad-output/planning-artifacts/ARCHITECTURE-Technical-Design.md
  - _bmad-output/planning-artifacts/ux-designs/ux-bmad101-2026-06-18/EXPERIENCE.md
---

# Automated Deck Generation System - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for the Automated Deck Generation System, decomposing the requirements from the PRD, Architecture, and UX Design spec into implementable stories.

**MVP Scope Constraints:**
- Ingestion: CSV, Excel, JSON adapters only (format-agnostic adapter pattern)
- Narrative generation: Template/rule-based only (no live LLM API calls at runtime)
- Verification: Figure reconciliation with tolerance-based match status, assumption sign-off, check dismissal, fix-and-re-verify
- Output: PPTX renderer only (no HTML renderer)
- Frontend: 3 screens (clarifying questions, narrative picker, audit/verification), desktop-only (1280px+)
- Excluded from MVP: HTML output, mobile layouts, live LLM narrative generation, pricing model, what-if cascading, scenario branching, versioning/re-answer

## Requirements Inventory

### Functional Requirements

FR1: System shall accept data uploads in CSV, Excel (XLSX), and JSON formats via a format-agnostic adapter pattern
FR2: System shall auto-detect schema from uploaded data (column names, data types, cardinality, nullability, date formats) using first 1000 rows
FR3: System shall run sequential quality checks on ingested data (duplicate detection, encoding validation, type consistency, date range validation, cardinality warnings, missing data summary)
FR4: System shall produce a ValidationReport with quality_issues, schema, and status (CLEAN | ISSUES_ACKNOWLEDGED | ISSUES_BLOCKING) requiring user sign-off before proceeding
FR5: System shall generate 4-5 targeted questions based on detected data schema and quality report using template-based question generation (not LLM)
FR6: System shall prioritize questions into tiers: Tier 1 (always ask: primary metric, audience), Tier 2 (ask if ambiguous: conflicting signals, data gaps)
FR7: System shall parse user answers using rule-based keyword matching and return parsed intent + confidence score (0-1)
FR8: System shall trigger a clarifying follow-up question when parsed confidence < 70%
FR9: System shall allow users to skip questions with a "use default" option, filling the system's best guess
FR10: System shall detect story angles from data (trend, disruption, composition, anomaly, comparison) using statistical analysis (linear regression, rolling std deviation, composition shifts)
FR11: System shall generate 2-3 narrative options using template-filling logic grounded in detected story angles and parsed user answers
FR12: System shall compute a confidence score per narrative: data_completeness × angle_strength × user_intent_match
FR13: System shall auto-flag every inference with a flag type: EXPLICIT (100%), PATTERN (75%), INFERRED (40%), SPECULATIVE (0%, blocked)
FR14: System shall extract every figure (number) from the selected narrative text via regex parsing and link it to source data rows
FR15: System shall run 5 reconciliation checks: (A) Sum-of-Parts, (B) Data Consistency, (C) Time Series Continuity, (D) Comparison Validity, (E) Statistical Significance
FR16: System shall block rendering if any reconciliation check fails — user must fix, dismiss, or edit narrative before proceeding
FR17: System shall produce per-figure match_status (exact | within_tolerance ≤1% | mismatch >1%) and variance_pct in figure traces
FR18: System shall support fix-and-re-verify flow: apply a suggested fix (e.g., exclude rows), re-run all checks, create a new reconciliation report with parent_report_id
FR19: System shall support check dismissal with required reason text, logged to audit trail
FR20: System shall track per-assumption sign-off actions (acknowledged for PATTERN, signed_off for INFERRED, rejected) with user attribution and timestamp
FR21: System shall support assumption rejection → navigate to narrative edit → re-verify round-trip
FR22: System shall generate PPTX output using python-pptx with slide structure: Title, Executive Summary, Data Visualizations, Assumptions + Flags, Q&A, Appendix
FR23: System shall embed metadata per slide (narrative_confidence, assumptions_count) and add footnotes for data limitations
FR24: System shall log every action to an immutable audit_log table (Q&A, narrative selection, edits, verification, rendering)

### NonFunctional Requirements

NFR1: Data validation shall complete in < 5 seconds for 100k rows
NFR2: Question generation shall complete in < 500ms
NFR3: Narrative generation (template-based) shall complete in < 2 seconds
NFR4: Reconciliation shall complete in < 1 second
NFR5: PPTX rendering shall complete in < 1 second
NFR6: All APIs secured with TLS 1.3; data encrypted at rest (AES-256)
NFR7: Audit log entries shall be immutable (PostgreSQL triggers prevent DELETE)
NFR8: All data stored with user attribution and timestamps
NFR9: Desktop viewport 1280px+ minimum; no mobile layouts required
NFR10: All interactive elements keyboard-navigable; status indicators include text labels (not color-only); proper table markup for data displays

### Additional Requirements

- Backend: Python + FastAPI
- Frontend: React (desktop web)
- Database: PostgreSQL with JSONB for flexible data (schema_json, quality_report, questions_json, answers_json, assumptions_json, checks_json, figure_traces)
- Caching: Redis for session state and question history
- File storage: Local filesystem for MVP (S3-ready pattern)
- PPTX generation: python-pptx library
- Async job processing: Celery + RabbitMQ for narrative generation and PPTX rendering
- Docker Compose dev environment: postgres:15, redis:7, python:3.11 FastAPI, node:18 React, minio (S3 mock)
- Adapter pattern for ingestion: base adapter interface with CSV, Excel, JSON concrete adapters (extensible)
- REST API design per architecture Section 5 (including the 3 new verify endpoints from Gap 3 resolution)

### UX Design Requirements

UX-DR1: Progress rail — persistent left sidebar or top stepper showing 5-step pipeline (Ingest ✓ → Questions → Narratives → Verify → Render) across all 3 screens, with current step highlighted and completed steps clickable for navigation
UX-DR2: Data context strip on Screen 1 — persistent banner showing filename, row/column counts, acknowledged quality issues count
UX-DR3: Question card component — shows one active question at a time with: data observation, question text, free-text input (auto-growing textarea), suggestion chips (derived from column names/patterns, populate text input on click), skip button
UX-DR4: Answered stack on Screen 1 — collapsed cards below active question showing: raw answer, parsed intent, confidence badge (green ✓ ≥70%, amber ⚠ <70%), edit link to re-open question
UX-DR5: Low-confidence follow-up — when parsed confidence <70%, inline clarifying follow-up appears below original answer before advancing to next question
UX-DR6: Narrative cards (×2-3) on Screen 2 — fixed-height cards showing: story angle label, 2-3 sentence summary, viz recommendation, confidence score (color-coded: green ≥80%, amber 60-79%, red <60%), assumption count chip, [Select] button
UX-DR7: Detail panel on Screen 2 — appears below card row on click, shows full narrative text, bulleted assumptions with flag type badges, viz justification, inline [Edit] textarea for narrative text modification
UX-DR8: Q&A summary bar on Screen 2 — collapsed one-liner of answered questions, expandable, with link back to Screen 1
UX-DR9: Mode banner on Screen 3 — full-width strip: red with failure count in blocking mode, green when all passed, neutral with timestamp in read-only mode
UX-DR10: Tab bar on Screen 3 — three tabs (Figures, Checks, Assumptions) with badge counts showing pass/fail split
UX-DR11: Figures table on Screen 3 — rows per extracted figure: value, source row range, formula, match status (✓/✗/⚠); mismatched rows expand inline with expected vs actual, variance, action buttons
UX-DR12: Figure drill-down slide-over panel — clicking [View source rows] opens panel showing actual data rows that produce the figure
UX-DR13: Checks list on Screen 3 — one row per check (A-E): name, status, failure details, suggested fix, action buttons ([Apply fix], [Dismiss], [Edit narrative])
UX-DR14: Dismiss confirmation modal — requires typed reason + "I accept responsibility" checkbox before dismissing a failed check
UX-DR15: Assumptions list on Screen 3 — grouped by flag type (EXPLICIT → PATTERN → INFERRED), with appropriate action buttons per type
UX-DR16: Gate status bar on Screen 3 — sticky bottom bar showing remaining blockers (failed checks + unsigned assumptions); "Proceed to Render →" disabled while blockers remain
UX-DR17: Loading/transition states — skeleton cards with shimmer on Screen 2, progress spinner with check-by-check updates on Screen 3, progressive card loading (not all-at-once)
UX-DR18: Accessibility — keyboard navigation for all elements, proper table markup, text labels paired with status icons, aria-labels on confidence scores, focus management on screen transitions, confirmation on destructive actions

### FR Coverage Map

FR1: Epic 1 - Multi-format data upload (CSV, Excel, JSON) via adapter pattern
FR2: Epic 1 - Auto schema detection from uploaded data
FR3: Epic 1 - Sequential quality checks on ingested data
FR4: Epic 1 - ValidationReport with user sign-off gate
FR5: Epic 2 - Generate 4-5 targeted questions from data schema
FR6: Epic 2 - Question prioritization into tiers
FR7: Epic 2 - Rule-based answer parsing with confidence scores
FR8: Epic 2 - Clarifying follow-up when confidence < 70%
FR9: Epic 2 - Skip question with system default
FR10: Epic 2 - Story angle detection from data patterns
FR11: Epic 2 - Template-based narrative generation (2-3 options)
FR12: Epic 2 - Per-narrative confidence scoring
FR13: Epic 2 - Auto-flag inferences with flag types
FR14: Epic 3 - Figure extraction from narrative text
FR15: Epic 3 - 5 reconciliation checks (A-E)
FR16: Epic 3 - Block rendering on check failure
FR17: Epic 3 - Per-figure match_status and variance_pct
FR18: Epic 3 - Fix-and-re-verify flow with new report
FR19: Epic 3 - Check dismissal with required reason
FR20: Epic 3 - Per-assumption sign-off tracking
FR21: Epic 3 - Assumption rejection → narrative edit → re-verify round-trip
FR22: Epic 4 - PPTX generation with structured slides
FR23: Epic 4 - Slide metadata and footnotes
FR24: Epic 3 - Immutable audit logging

## Epic List

### Epic 1: Project Foundation & Data Ingestion
User can upload data files (CSV, Excel, JSON), see the auto-detected schema and quality report, acknowledge issues, and sign off to proceed. Includes project scaffolding (Docker, DB, base API) as the first story.
**FRs covered:** FR1, FR2, FR3, FR4
**NFRs:** NFR1, NFR6, NFR7, NFR8
**Additional:** Docker Compose setup, DB schema, adapter pattern base, FastAPI bootstrap

### Epic 2: Question Engine & Narrative Generation
User can answer 4-5 targeted questions with confidence feedback, then receive 2-3 narrative options to compare side-by-side, optionally edit, and select one. Covers Screens 1 and 2 end-to-end.
**FRs covered:** FR5, FR6, FR7, FR8, FR9, FR10, FR11, FR12, FR13
**NFRs:** NFR2, NFR3
**UX-DRs:** UX-DR1, UX-DR2, UX-DR3, UX-DR4, UX-DR5, UX-DR6, UX-DR7, UX-DR8, UX-DR17

### Epic 3: Figure Verification & Trust Gate
User can verify every figure against source data, resolve check failures (apply fix, dismiss with reason, edit narrative), sign off on assumptions, and clear the blocking gate. Covers Screen 3 end-to-end.
**FRs covered:** FR14, FR15, FR16, FR17, FR18, FR19, FR20, FR21, FR24
**NFRs:** NFR4, NFR10
**UX-DRs:** UX-DR9, UX-DR10, UX-DR11, UX-DR12, UX-DR13, UX-DR14, UX-DR15, UX-DR16, UX-DR18

### Epic 4: PPTX Rendering & Deck Output
User can render the verified narrative into a boardroom-ready PPTX deck with structured slides, embedded metadata, and footnotes.
**FRs covered:** FR22, FR23
**NFRs:** NFR5

---

## Epic 1: Project Foundation & Data Ingestion

User can upload data files (CSV, Excel, JSON), see the auto-detected schema and quality report, acknowledge issues, and sign off to proceed.

### Story 1.1: Project Scaffolding & Dev Environment

As a developer,
I want a working local dev environment with Docker Compose (PostgreSQL, Redis, FastAPI, React, MinIO), base DB schema (users, decks, ingest_jobs, audit_log tables), and a health-check API endpoint,
So that all subsequent stories have a running foundation to build on.

**Acceptance Criteria:**

**Given** a fresh clone of the repository
**When** I run `docker-compose up`
**Then** PostgreSQL, Redis, FastAPI, React dev server, and MinIO containers start successfully
**And** `GET /api/v1/health` returns 200 with service status
**And** the DB contains users, decks, ingest_jobs, and audit_log tables per the architecture schema
**And** the React app renders a shell with the progress rail component (placeholder steps)

### Story 1.2: CSV Data Ingestion with Schema Detection

As an analyst,
I want to upload a CSV file and see the auto-detected schema and quality report,
So that I can verify the system correctly understands my data before proceeding.

**Acceptance Criteria:**

**Given** the base adapter interface is defined with `parse(file) → DataFrame` and `detect_schema(df) → Schema` contracts
**When** I upload a CSV file via `POST /api/v1/decks/{deck_id}/ingest`
**Then** the CSV adapter parses the file using Pandas
**And** schema detection runs on the first 1000 rows (column names cleaned, data types inferred, cardinality computed, nullability calculated, date formats detected)
**And** quality checks run in sequence (duplicate detection via row-level MD5, encoding validation, type consistency, date range validation, cardinality warnings >1000, missing data summary)
**And** the response includes a ValidationReport with `quality_issues`, `schema`, and `status` (CLEAN | ISSUES_ACKNOWLEDGED | ISSUES_BLOCKING)
**And** an ingest_jobs row is created with schema_json and quality_report JSONB
**And** the file is stored in MinIO/S3 with a UUID reference
**And** validation completes in < 5 seconds for a 100k-row file

### Story 1.3: Excel and JSON Ingestion Adapters

As an analyst,
I want to upload Excel (XLSX) or JSON files and get the same schema detection and quality report as CSV,
So that I can use whichever format my data comes in.

**Acceptance Criteria:**

**Given** the adapter interface from Story 1.2 exists
**When** I upload an XLSX file via `POST /api/v1/decks/{deck_id}/ingest`
**Then** the Excel adapter parses the file using Pandas (openpyxl) and returns the same ValidationReport structure as CSV
**And** multi-sheet workbooks use the first sheet by default

**Given** the adapter interface from Story 1.2 exists
**When** I upload a JSON file via `POST /api/v1/decks/{deck_id}/ingest`
**Then** the JSON adapter parses the file (array-of-objects or nested structure flattened to tabular) and returns the same ValidationReport structure
**And** the adapter auto-detects whether the JSON is flat or nested

**Given** an unsupported file format is uploaded
**When** the system receives the file
**Then** it returns a 400 error with a clear message listing supported formats (CSV, XLSX, JSON)

### Story 1.4: Data Validation Review & Sign-Off

As an analyst,
I want to see the quality report on screen, acknowledge any issues, and sign off to proceed to questions,
So that I trust the data is clean enough before the system asks me about it.

**Acceptance Criteria:**

**Given** an ingest job has completed with status CLEAN
**When** I view the ingestion screen
**Then** I see the schema summary (columns, types, row count) and a green status indicating no issues
**And** the "Proceed to Questions →" button is enabled

**Given** an ingest job has completed with status ISSUES_BLOCKING
**When** I view the ingestion screen
**Then** I see each quality issue with severity, description, count, and sample rows
**And** I can acknowledge each issue individually
**And** `POST /api/v1/decks/{deck_id}/validate-acknowledge` updates the status to ISSUES_ACKNOWLEDGED
**And** the "Proceed to Questions →" button enables only after acknowledgment

**Given** the user has signed off on data validation
**When** the sign-off is recorded
**Then** an audit_log entry is created with action `data_validated` and the user_id + timestamp
**And** the ingest_job `validated_at` timestamp is set

---

## Epic 2: Question Engine & Narrative Generation

User can answer 4-5 targeted questions with confidence feedback, then receive 2-3 narrative options to compare side-by-side, optionally edit, and select one.

### Story 2.1: Question Generation & Answer Parsing Service

As an analyst,
I want the system to generate targeted questions based on my data structure and parse my answers with confidence scoring,
So that the system understands my intent before generating narratives.

**Acceptance Criteria:**

**Given** a validated ingest job with schema_json and quality_report
**When** I call `GET /api/v1/decks/{deck_id}/questions`
**Then** the system returns 4-5 questions generated from templates based on detected data patterns (multiple numeric columns → headline metric question, temporal + numeric → comparison period question, mixed deltas → priority question, high cardinality → top-N question, data gaps → fill/exclude question)
**And** questions are prioritized: Tier 1 (primary metric, audience) always included, Tier 2 (conflicting signals, data gaps) included only if ambiguous
**And** each question includes `{id, template, context, suggestion_chips}` where chips are derived from column names and detected patterns
**And** a question_sessions row is created with questions_json
**And** generation completes in < 500ms

**Given** the user submits free-text answers via `POST /api/v1/decks/{deck_id}/answer-questions`
**When** the rule-based parser processes each answer
**Then** each answer returns `{question_id, raw_answer, parsed_intent, confidence}` using keyword matching (profit/margin → PROFIT 0.9, revenue/sales → GROWTH 0.85, etc.)
**And** the response includes `ready_to_generate: true` when all Tier 1 questions are answered or skipped
**And** the question_sessions row is updated with answers_json

### Story 2.2: Clarifying Questions Screen (Screen 1)

As an analyst,
I want to see one question at a time with smart suggestions and confidence feedback on my answers,
So that I can quickly tell the system what matters without second-guessing whether it understood me.

**Acceptance Criteria:**

**Given** I have completed data validation sign-off
**When** Screen 1 loads
**Then** I see the progress rail with "Questions" highlighted as active and "Ingest" showing ✓
**And** I see the data context strip showing filename, row/column counts, and acknowledged issues count
**And** the first question card is displayed with data observation, question text, free-text input, and suggestion chips

**Given** I am viewing an active question card
**When** I click a suggestion chip
**Then** the chip text populates the free-text input field (editable, not submitted)

**Given** I submit an answer (Enter or button)
**When** the parsed confidence is ≥ 70%
**Then** the question collapses into the answered stack showing raw answer, parsed intent, and green confidence badge
**And** the next question becomes active

**Given** I submit an answer
**When** the parsed confidence is < 70%
**Then** a clarifying follow-up appears inline below my answer ("I'm not sure I understood — did you mean X or Y?")
**And** I can provide a clarifying response before the question collapses

**Given** I click "Skip — use default" on a question
**When** the skip is processed
**Then** the system fills its best guess, marks the answer as `defaulted`, and advances to the next question

**Given** I click [Edit] on a question in the answered stack
**When** the question card re-opens
**Then** my previous answer is pre-filled and I can modify and resubmit

**Given** all questions are answered or skipped
**When** at least Tier 1 questions are resolved
**Then** "Generate Narratives →" button enables
**And** clicking it shows a loading state ("Analyzing data and generating narrative options...") and transitions to Screen 2

### Story 2.3: Narrative Generation Service

As an analyst,
I want the system to generate 2-3 data-grounded narrative options based on my answers and detected patterns,
So that I can choose the interpretation that best frames my data story.

**Acceptance Criteria:**

**Given** a completed question session with parsed answers
**When** the narrative generation service runs
**Then** story angles are detected from data using: linear regression (trend), rolling std deviation (disruption), composition shifts (composition), outlier detection >3σ (anomaly), categorical breakdown (comparison)
**And** 2-3 narrative templates are selected based on the combination of detected angles and parsed user intent
**And** each narrative is generated using template-filling logic (no live LLM API calls): "{metric} has {changed} from {period1} to {period2}. Key drivers: {top_3_factors}. Status: {risk_level}"

**Given** narratives are generated
**When** confidence scores are computed
**Then** each narrative has `overall_confidence = data_completeness × angle_strength × user_intent_match` (all 0-1 floats)

**Given** narratives are generated
**When** assumptions are extracted
**Then** every inference is flagged: EXPLICIT (in data, 100%), PATTERN (statistical pattern, 75%), INFERRED (contextual, 40%)
**And** SPECULATIVE assumptions (0%) are blocked — never included in output
**And** each narrative includes a viz_recommendation with chart type and justification

**Given** narrative generation completes
**When** results are stored
**Then** 2-3 rows are created in the narratives table with story_angle, narrative_text, viz_recommendation, assumptions_json, overall_confidence
**And** `GET /api/v1/decks/{deck_id}/narratives` returns all options
**And** generation completes in < 2 seconds

### Story 2.4: Narrative Picker Screen (Screen 2)

As an analyst,
I want to compare narrative options side-by-side, inspect assumptions, optionally edit, and select my preferred narrative,
So that I can curate the story angle before the system verifies the numbers.

**Acceptance Criteria:**

**Given** I click "Generate Narratives →" from Screen 1
**When** Screen 2 loads
**Then** skeleton cards with shimmer appear while narratives generate
**And** cards populate progressively as each narrative completes (not all-at-once)
**And** the progress rail shows "Narratives" as active with "Questions ✓"

**Given** 2-3 narrative cards are displayed
**When** I view the cards
**Then** each card shows: story angle label, 2-3 sentence summary, viz recommendation (one line), confidence score (green ≥80%, amber 60-79%, red <60%), assumption count chip (amber if INFERRED present), and [Select] button

**Given** I click on a narrative card
**When** the detail panel opens below the card row
**Then** I see: full narrative text, bulleted assumptions with flag type badges (EXPLICIT/PATTERN/INFERRED), viz justification, and an [Edit] button
**And** only one detail panel is open at a time

**Given** I click [Edit] in the detail panel
**When** the inline textarea appears
**Then** I can modify the narrative text and save
**And** the card shows a "Modified" badge
**And** the edit is stored in `deck_selections.user_edits_text`

**Given** I see the Q&A summary bar at the top
**When** I expand it
**Then** I see all question-answer pairs from Screen 1
**And** clicking the link navigates back to Screen 1 (with warning: "Changing answers will regenerate narratives")

**Given** I click [Select] on a card
**When** the selection is recorded via `POST /api/v1/decks/{deck_id}/select-narrative`
**Then** the card shows selected state (checkmark, solid border)
**And** "Verify & Proceed →" button enables
**And** clicking it transitions to Screen 3

---

## Epic 3: Figure Verification & Trust Gate

User can verify every figure against source data, resolve check failures (apply fix, dismiss with reason, edit narrative), sign off on assumptions, and clear the blocking gate.

### Story 3.1: Figure Extraction & Reconciliation Checks Service

As an analyst,
I want every number in my selected narrative automatically verified against the source data,
So that I know whether the deck's figures are accurate before it goes to leadership.

**Acceptance Criteria:**

**Given** a narrative has been selected (with or without user edits)
**When** verification runs
**Then** the system extracts every figure from the narrative text via regex (`\d+[.,]\d+%?`, `\$\d+[KMB]?`) and stores each with `{value, context_sentence, narrative_position}`

**Given** figures are extracted
**When** the 5 reconciliation checks run
**Then** Check A (Sum-of-Parts) verifies component figures sum to reported totals ± 1%
**And** Check B (Data Consistency) traces each figure to source rows and verifies ± 0.1%
**And** Check C (Time Series Continuity) verifies no missing periods when narrative claims continuity
**And** Check D (Comparison Validity) verifies same dates in both periods for YoY/MoM claims
**And** Check E (Statistical Significance) verifies R² > 0.6 for any trend claims

**Given** checks complete
**When** the reconciliation report is created
**Then** each check stores `{status: "pass"|"fail", expected, actual, fix_suggestion}` in checks_json
**And** each figure trace stores `{figure_value, source_rows, formula, match_status, variance_pct}` where match_status is `exact` (0%), `within_tolerance` (≤1%), or `mismatch` (>1%)
**And** the report `passed` boolean is false if any check has status `fail`
**And** reconciliation completes in < 1 second

### Story 3.2: Verification Screen — Figures & Checks Tabs (Screen 3)

As an analyst,
I want to see which figures match, which checks failed, and what the system suggests to fix them,
So that I can quickly identify and resolve any data integrity issues.

**Acceptance Criteria:**

**Given** I click "Verify & Proceed →" from Screen 2
**When** Screen 3 loads
**Then** a spinner shows "Running 5 reconciliation checks..." with progress updates as each check completes
**And** the progress rail shows "Verify" as active

**Given** verification completes
**When** all checks pass
**Then** a green mode banner shows "✓ ALL CHECKS PASSED"
**And** the Figures tab is active by default

**Given** verification completes
**When** one or more checks fail
**Then** a red mode banner shows "✗ N OF 5 CHECKS FAILED — FIX REQUIRED"

**Given** I view the Figures tab
**When** the figures table renders
**Then** each row shows: figure value, source row range, formula/derivation, and status icon (✓ matched green, ✗ mismatch red, ⚠ within_tolerance green)
**And** mismatched rows expand inline showing expected vs. actual, variance percentage, and action buttons ([View source rows], [Edit narrative], [Exclude rows])
**And** the table uses proper `<table>` markup with column headers

**Given** I click [View source rows] on a figure
**When** the slide-over panel opens
**Then** I see the actual data rows that produce the figure with filterable source columns

**Given** I view the Checks tab
**When** the checks list renders
**Then** each of the 5 checks shows: name, pass/fail/warn status, and for failures: expected vs. actual, suggested fix text, and action buttons ([Apply fix], [Dismiss], [Edit narrative])
**And** Check E (Statistical Significance) with R² < 0.6 shows ⚠ WEAK with [Acknowledge weak trend] button

**Given** the tab bar renders
**When** I see badge counts
**Then** Figures tab shows total count and pass/fail split, Checks tab shows pass/fail count, Assumptions tab shows unsigned count

### Story 3.3: Fix, Dismiss & Re-Verify Flow

As an analyst,
I want to apply a suggested fix, dismiss a check with a reason, or edit the narrative and re-verify,
So that I can resolve every failure and move forward with confidence.

**Acceptance Criteria:**

**Given** a check has failed
**When** I click [Apply fix] (e.g., "Exclude 12 rows with null cost entries")
**Then** `POST /api/v1/decks/{deck_id}/verify/apply-fix` applies the data filter, re-extracts figures from filtered data, re-runs all 5 checks, and returns a new reconciliation_report with `parent_report_id` pointing to the original
**And** the check status updates inline (animated ✗ → ✓ on success)
**And** the gate status blocker count decrements

**Given** a check has failed
**When** I click [Dismiss]
**Then** a modal appears requiring: typed reason text and "I accept responsibility" checkbox
**And** on confirm, `POST /api/v1/decks/{deck_id}/verify/dismiss-check` updates the check status to `dismissed` with `dismissed_reason`, `dismissed_by`, `dismissed_at`
**And** the check shows ⊘ dismissed status with the reason inline
**And** an audit_log entry is created
**And** the gate status blocker count decrements

**Given** a check has failed
**When** I click [Edit narrative]
**Then** the UI navigates to Screen 2 with the detail panel open and narrative text editable
**And** after saving edits and clicking "Verify & Proceed →", a new reconciliation report is created from the edited narrative

**Given** a fix or dismissal resolves the last remaining failure
**When** the gate status updates
**Then** the check failure count shows 0 remaining

### Story 3.4: Assumption Sign-Off & Gate Resolution

As an analyst,
I want to review every assumption the system made, sign off or reject each one, and only proceed to rendering when everything is resolved,
So that the deck has full human accountability for every inference.

**Acceptance Criteria:**

**Given** I view the Assumptions tab
**When** assumptions are displayed
**Then** they are grouped by flag type: EXPLICIT (display only, no action), PATTERN (requires acknowledgment), INFERRED (requires sign-off)
**And** each shows the assumption text, confidence percentage, and source reference

**Given** I see a PATTERN assumption
**When** I click [Acknowledge]
**Then** `POST /api/v1/decks/{deck_id}/verify/assumption-action` records `{assumption_index, action: "acknowledged", user_id, created_at}` in assumption_actions_json
**And** the assumption shows ✓ acknowledged state

**Given** I see a PATTERN assumption
**When** I click [Challenge]
**Then** the UI navigates to Screen 2 with `?highlight=assumption-{index}`, the detail panel opens with narrative text editable near the relevant passage
**And** after editing and returning to Screen 3, re-verification runs on the edited text

**Given** I see an INFERRED assumption
**When** I click [Sign off]
**Then** the action is recorded as `signed_off` with user attribution and timestamp

**Given** I see an INFERRED assumption
**When** I click [Reject — edit narrative]
**Then** the rejection is recorded, the UI navigates to Screen 2 for narrative editing, and returning triggers re-verification

**Given** the gate status bar at the bottom of Screen 3
**When** I view it
**Then** it shows remaining blockers: failed/undismissed check count + unresolved PATTERN/INFERRED assumption count
**And** "Proceed to Render →" is disabled while any blocker remains
**And** it enables only when all checks pass (or dismissed) AND all PATTERN assumptions acknowledged AND all INFERRED assumptions signed off

**Given** all blockers are resolved
**When** I click "Proceed to Render →"
**Then** an audit_log entry records `verification_completed` and the system transitions to rendering

**Given** I return to Screen 3 post-render (via progress rail)
**When** the screen loads in read-only mode
**Then** all action buttons are hidden, the banner shows "Verified [timestamp] · All checks pass", dismissed items show their dismissal reason, and [Download PPTX] is visible

---

## Epic 4: PPTX Rendering & Deck Output

User can render the verified narrative into a boardroom-ready PPTX deck with structured slides, embedded metadata, and footnotes.

### Story 4.1: PPTX Rendering Service & Deck Download

As an analyst,
I want my verified narrative rendered into a structured PPTX deck that I can download and present,
So that I have a boardroom-ready deliverable within minutes of uploading my data.

**Acceptance Criteria:**

**Given** all verification checks are resolved and "Proceed to Render →" was clicked
**When** the render service runs via `POST /api/v1/decks/{deck_id}/render`
**Then** python-pptx generates a PPTX file with this slide structure:
- Slide 1: Title (deck name, date, data source filename)
- Slide 2: Executive Summary (1-2 sentence narrative from selected narrative_text)
- Slides 3-N: Data visualizations (chart placeholder + data table per viz_recommendation)
- Slide N+1: Assumptions & Inference Flags (bulleted list from assumptions_json with flag type labels)
- Slide N+2: Q&A (questions asked + answers given from question_sessions)
- Final Slide: Appendix (data quality notes from quality_report, reconciliation status summary, verification timestamp)

**Given** the PPTX is generated
**When** metadata is embedded
**Then** each slide includes narrative_confidence and assumptions_count in slide notes
**And** footnotes appear on data slides for any data limitations (e.g., "Based on Q1-Q3 data; Q4 not available")

**Given** rendering completes
**When** the output is stored
**Then** a deck_outputs row is created with version number and pptx_url (MinIO/S3 signed URL)
**And** an audit_log entry records `deck_rendered` with deck_id, version, user_id, timestamp
**And** rendering completes in < 1 second

**Given** the user is on Screen 3 (read-only mode post-render)
**When** they click [Download PPTX]
**Then** the browser downloads the generated PPTX file
**And** the progress rail shows "Render ✓" as the final completed step
