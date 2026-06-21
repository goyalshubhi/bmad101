---
status: draft
updated: 2026-06-18
scope: 3-screen wireframe (clarifying questions, narrative picker, audit/verification)
sources:
  - _bmad-output/planning-artifacts/PRD-Automated-Deck-Generation.md
  - _bmad-output/planning-artifacts/ARCHITECTURE-Technical-Design.md
---

# Experience Spec — Deck Generation MVP (3 Screens)

## Foundation

- **Form factor:** Desktop web (1280px+ viewport). No mobile.
- **UI system:** React. No component library chosen yet — wireframes are system-agnostic.
- **Protagonist:** Riya, FP&A analyst. Messy quarterly export, 25 minutes before a leadership review prep call. Needs speed and visible proof that the numbers are right.

## Information Architecture

Three screens in a linear flow, with one re-entrant path:

```
[Data Ingestion + Validation]        (exists, out of scope)
         │
         ▼
┌─────────────────────────┐
│  1. CLARIFYING QUESTIONS │ ◄── re-answer (from Adapt Service)
└────────────┬────────────┘
             │  all answered / skipped
             ▼
┌─────────────────────────┐
│  2. NARRATIVE PICKER     │
└────────────┬────────────┘
             │  narrative selected
             ▼
┌─────────────────────────┐
│  3. AUDIT / VERIFICATION │ ◄── re-entry (read-only, post-render)
│     (blocking gate mode) │
└────────────┬────────────┘
             │  all checks pass + assumptions signed off
             ▼
[Render PPTX + HTML]                  (exists, out of scope)
```

Every screen shares a persistent **progress rail** (left sidebar or top stepper) showing: Ingest ✓ → Questions → Narratives → Verify → Render. Current step highlighted. Completed steps clickable to revisit (re-answer flow).

---

## Screen 1: Clarifying Questions

### Purpose

Capture 4–5 user intent signals so the system generates relevant narratives instead of generic ones.

### Layout

```
┌──────────────────────────────────────────────────────────────┐
│  Progress Rail (left, narrow)  │  Main Content Area           │
│                                │                              │
│  ● Ingest ✓                   │  ┌──────────────────────────┐│
│  ● Questions  ← active        │  │ DATA CONTEXT STRIP       ││
│  ○ Narratives                  │  │ "quarterly_sales.xlsx"   ││
│  ○ Verify                      │  │ 14 cols · 12,847 rows   ││
│  ○ Render                      │  │ 3 issues acknowledged    ││
│                                │  └──────────────────────────┘│
│                                │                              │
│                                │  Question 1 of 5             │
│                                │  ┌──────────────────────────┐│
│                                │  │ QUESTION CARD            ││
│                                │  │                          ││
│                                │  │ "Your data has 4 numeric ││
│                                │  │  columns (revenue, cost, ││
│                                │  │  headcount, margin).     ││
│                                │  │  Which is the headline   ││
│                                │  │  metric for this deck?"  ││
│                                │  │                          ││
│                                │  │ ┌────────────────────┐   ││
│                                │  │ │ free-text input     │   ││
│                                │  │ └────────────────────┘   ││
│                                │  │ suggestion chips:        ││
│                                │  │ [Revenue] [Margin] [Cost]││
│                                │  │                          ││
│                                │  │ [Skip — use default]     ││
│                                │  └──────────────────────────┘│
│                                │                              │
│                                │  ┌──────────────────────────┐│
│                                │  │ ANSWERED STACK (below)   ││
│                                │  │ Q1: "Focus on margin"    ││
│                                │  │     parsed: PROFIT ✓ 92% ││
│                                │  │     [Edit]               ││
│                                │  └──────────────────────────┘│
│                                │                              │
│                                │  [Generate Narratives →]     │
└──────────────────────────────────────────────────────────────┘
```

### Components

| Component | Behavior |
|---|---|
| **Data context strip** | Persistent at top. Shows filename, row/column counts, acknowledged quality issues count. Clicking opens the ingestion validation summary (existing screen, out of scope). |
| **Question card** | Shows one active question at a time. Contains: data observation (what the system noticed), the question itself, free-text input, suggestion chips, skip button. |
| **Suggestion chips** | Pre-filled options derived from column names / detected patterns. Clicking a chip populates the text input — user can edit before submitting. Not radio buttons; they seed the free-text field. |
| **Free-text input** | Single textarea, auto-growing. Submit on Enter or explicit button. |
| **Skip button** | "Skip — use default." Fills the answer with the system's best guess and marks it as `defaulted`. Visible but de-emphasized (text link, not primary button). |
| **Answered stack** | Below the active question. Shows all previously answered questions as collapsed cards: raw answer, parsed intent, confidence badge. Each has an [Edit] link that re-opens the question card for that question. |
| **Confidence badge** | Inline after parsed intent. Green ✓ ≥ 70%, amber ⚠ < 70%. |
| **Generate Narratives button** | Bottom of content area. Disabled until at least the Tier 1 questions (primary metric, audience) are answered or skipped. Enabled state shows "Generate Narratives →". |

### States

| State | Trigger | Behavior |
|---|---|---|
| **Answering** | Screen loads after ingestion | Active question card shown. Answered stack empty. |
| **Low-confidence follow-up** | Parsed confidence < 70% | System appends a clarifying follow-up below the original answer: "I'm not sure I understood — did you mean X or Y?" New input field appears inline. Original answer stays visible. |
| **All answered** | All 4–5 questions answered or skipped | Active question card disappears. Full answered stack visible. "Generate Narratives →" button prominent. |
| **Re-answer (from later screen)** | User clicks "Questions" in progress rail | Returns to this screen with all answers populated. Any answer editable. Editing any answer shows a warning: "Changing this will regenerate narratives." |

### Interaction flow

1. Screen loads with Q1 active.
2. User types or clicks a chip → submits.
3. System parses answer, shows parsed intent + confidence in the answered stack. If confidence < 70%, follow-up appears inline before advancing.
4. Q2 becomes active. Repeat.
5. After last question (or enough skips), "Generate Narratives →" enables.
6. Click → loading state ("Analyzing data and generating narrative options...") → transition to Screen 2.

---

## Screen 2: Narrative Picker

### Purpose

Present 2–3 AI-generated narrative interpretations side-by-side so Riya can pick the one that best frames her data for leadership.

### Layout

```
┌──────────────────────────────────────────────────────────────┐
│  Progress Rail  │  Main Content Area                          │
│                 │                                             │
│  ● Ingest ✓    │  YOUR ANSWERS → THESE NARRATIVES            │
│  ● Questions ✓ │  (collapsed summary of Q&A, expandable)     │
│  ● Narratives  │                                             │
│    ← active    │  ┌─────────┐  ┌─────────┐  ┌─────────┐    │
│  ○ Verify      │  │ CARD A  │  │ CARD B  │  │ CARD C  │    │
│  ○ Render      │  │         │  │         │  │         │    │
│                 │  │ angle   │  │ angle   │  │ angle   │    │
│                 │  │ badge   │  │ badge   │  │ badge   │    │
│                 │  │         │  │         │  │         │    │
│                 │  │ summary │  │ summary │  │ summary │    │
│                 │  │ (2-3    │  │ (2-3    │  │ (2-3    │    │
│                 │  │ lines)  │  │ lines)  │  │ lines)  │    │
│                 │  │         │  │         │  │         │    │
│                 │  │ viz     │  │ viz     │  │ viz     │    │
│                 │  │ recom.  │  │ recom.  │  │ recom.  │    │
│                 │  │         │  │         │  │         │    │
│                 │  │ conf:86%│  │ conf:72%│  │ conf:64%│    │
│                 │  │ 2 flags │  │ 1 flag  │  │ 4 flags │    │
│                 │  │         │  │         │  │         │    │
│                 │  │ [Select]│  │ [Select]│  │ [Select]│    │
│                 │  └─────────┘  └─────────┘  └─────────┘    │
│                 │                                             │
│                 │  ──────── DETAIL PANEL (below cards) ────── │
│                 │  (appears when a card is focused/selected)  │
│                 │  Full narrative text                         │
│                 │  Assumption list with flag types             │
│                 │  Viz justification                           │
│                 │  [Edit narrative text]                       │
│                 │                                             │
│                 │  [← Back to Questions]  [Verify & Proceed →]│
└──────────────────────────────────────────────────────────────┘
```

### Components

| Component | Behavior |
|---|---|
| **Q&A summary bar** | Collapsed one-liner: "5 questions answered · primary metric: margin · audience: board." Expandable to show full Q&A pairs. Links back to Screen 1 for re-answer. |
| **Narrative card** (×2–3) | Fixed-height card showing: **story angle** label (e.g., "Cost Disruption", "Growth Momentum"), **summary** (2–3 sentence preview from `narrative_text`), **viz recommendation** (chart type + what it shows, one line), **confidence score** (percentage, color-coded: green ≥ 80%, amber 60–79%, red < 60%), **assumption count** (e.g., "2 flagged assumptions"), **[Select]** button. |
| **Confidence indicator** | Circular or bar indicator. Score derived from `overall_confidence` on the narrative. Tooltip on hover: "Data completeness × angle strength × intent match." |
| **Assumption count chip** | Shows count of non-EXPLICIT assumptions. Color: amber if any INFERRED, red if any SPECULATIVE (should not exist per architecture, but defensive). Clicking scrolls to assumption list in detail panel. |
| **Detail panel** | Appears below the card row when any card is clicked or selected. Shows: full `narrative_text`, bulleted `assumptions_json` list (each with flag type badge: EXPLICIT / PATTERN / INFERRED), `viz_justification`, and an [Edit] button for the narrative text. Only one detail panel open at a time. |
| **Edit narrative** | Inline textarea replacing the narrative text in the detail panel. Save → text stored in `deck_selections.user_edits_text`. Visual indicator that narrative was user-modified. |
| **Verify & Proceed** | Primary action. Disabled until a narrative is selected. Click → transitions to Screen 3 in blocking-gate mode. |

### States

| State | Trigger | Behavior |
|---|---|---|
| **Loading** | Entered from Screen 1 | Skeleton cards with shimmer. Progress text: "Analyzing 3 story angles..." Cards appear as each narrative completes (not all-at-once). |
| **Options presented** | All narratives generated | Cards fully rendered, none selected. Detail panel hidden. |
| **Card focused** | Click on any card | Card gets a selection ring. Detail panel opens for that card. Other cards remain visible but visually receded. |
| **Narrative selected** | Click [Select] on a card | Card shows selected state (checkmark, solid border). "Verify & Proceed →" enables. User can switch selection by clicking another card's [Select]. |
| **Narrative edited** | User modifies text in detail panel | "Modified" badge appears on the card. Edited text used for verification instead of original. |
| **Regenerating** | User re-answered questions (returned from Screen 1) | Cards show "Regenerating..." overlay. New options replace old ones. Any previous selection cleared. |

### Interaction flow

1. Screen loads with skeleton cards → cards populate progressively.
2. Riya scans the three angles — looks at confidence scores and assumption counts first (trust signals).
3. Clicks a card to expand the detail panel. Reads full narrative. Checks assumptions.
4. Optionally edits the narrative text.
5. Clicks [Select] → clicks [Verify & Proceed →] → transition to Screen 3.

---

## Screen 3: Audit / Verification View

### Purpose

Show Riya that every number in the selected narrative is traceable to source data, every assumption is flagged, and every reconciliation check passed. In blocking-gate mode, halt progress and surface fix actions on failures. In read-only mode, serve as the permanent audit reference.

### Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  Progress Rail  │  Main Content Area                              │
│                 │                                                  │
│  ● Ingest ✓    │  MODE BANNER                                     │
│  ● Questions ✓ │  ┌──────────────────────────────────────────┐    │
│  ● Narratives ✓│  │ ✓ ALL CHECKS PASSED  (or)               │    │
│  ● Verify      │  │ ✗ 2 OF 5 CHECKS FAILED — FIX REQUIRED  │    │
│    ← active    │  └──────────────────────────────────────────┘    │
│  ○ Render      │                                                  │
│                 │  ┌── TAB BAR ───────────────────────────────┐   │
│                 │  │ [Figures ▾]  [Checks]  [Assumptions]     │   │
│                 │  └──────────────────────────────────────────┘   │
│                 │                                                  │
│                 │  ═══════════════════════════════════════════     │
│                 │  TAB: FIGURES (default)                          │
│                 │  ─────────────────────────────────────────────   │
│                 │                                                  │
│                 │  Figure       Source       Formula    Status     │
│                 │  ─────────────────────────────────────────────   │
│                 │  $5.2M rev    rows 1–847   SUM(D)    ✓ matched  │
│                 │  22% cost ↑   rows 1–847   Δ%        ✓ matched  │
│                 │  $1.1M EBIT   rows 12–340  SUM(G)    ✗ MISMATCH │
│                 │               expected: $1.08M                   │
│                 │               actual:   $1.14M                   │
│                 │               variance: 5.3%                     │
│                 │               [View source rows]                 │
│                 │               [Edit narrative] [Exclude rows]    │
│                 │  ─────────────────────────────────────────────   │
│                 │                                                  │
│                 │  ═══════════════════════════════════════════     │
│                 │  TAB: CHECKS                                     │
│                 │  ─────────────────────────────────────────────   │
│                 │                                                  │
│                 │  Check A: Sum-of-Parts .............. ✓ PASS     │
│                 │  Check B: Data Consistency .......... ✗ FAIL     │
│                 │           $1.1M EBIT ≠ source (5.3%)             │
│                 │           [View affected figure]                  │
│                 │           Suggested fix: "Exclude 12 rows with   │
│                 │           null cost entries"                      │
│                 │           [Apply fix]  [Dismiss]                  │
│                 │  Check C: Time Series Continuity .... ✓ PASS     │
│                 │  Check D: Comparison Validity ....... ✓ PASS     │
│                 │  Check E: Statistical Significance .. ⚠ WEAK     │
│                 │           R²=0.54 for "declining trend" claim    │
│                 │           [Acknowledge weak trend]                │
│                 │  ─────────────────────────────────────────────   │
│                 │                                                  │
│                 │  ═══════════════════════════════════════════     │
│                 │  TAB: ASSUMPTIONS                                 │
│                 │  ─────────────────────────────────────────────   │
│                 │                                                  │
│                 │  ● EXPLICIT (3)    shown as reference, no action │
│                 │    "Q2 revenue $5M" — source: row 201–400        │
│                 │                                                  │
│                 │  ● PATTERN (2)     requires acknowledgment       │
│                 │    "Growing trend in margin" (75% conf)          │
│                 │    [Acknowledge] [Challenge]                      │
│                 │                                                  │
│                 │  ● INFERRED (1)    requires sign-off             │
│                 │    "Cost spike driven by headcount" (40% conf)   │
│                 │    [Sign off] [Reject — edit narrative]           │
│                 │                                                  │
│                 │  ─────────────────────────────────────────────   │
│                 │                                                  │
│                 │  ┌──────────────────────────────────────────┐    │
│                 │  │ GATE STATUS (blocking mode only)         │    │
│                 │  │ ✗ 1 check failure remaining              │    │
│                 │  │ ⚠ 1 assumption awaiting sign-off         │    │
│                 │  │                                          │    │
│                 │  │ [← Back to Narrative]  [Proceed disabled]│    │
│                 │  └──────────────────────────────────────────┘    │
│                 │                                                  │
│                 │  (read-only mode: gate status replaced by        │
│                 │   "Verified 2026-06-18 14:32 · All checks pass"  │
│                 │   + [Download PPTX] [View HTML])                  │
└──────────────────────────────────────────────────────────────────┘
```

### Components

| Component | Behavior |
|---|---|
| **Mode banner** | Full-width strip at top. **Blocking mode:** red if any check failed, green if all passed. Shows count. **Read-only mode:** neutral/green with verification timestamp. |
| **Tab bar** | Three tabs: Figures (default), Checks, Assumptions. Badge counts on each tab show: total figures / pass-fail split, check pass-fail count, unsigned assumption count. |
| **Figures table** | One row per extracted figure from the narrative. Columns: figure value, source row range, formula/derivation, status (✓ matched / ✗ mismatch / ⚠ weak). Mismatched rows expand inline to show expected vs. actual, variance, and action buttons. |
| **Figure drill-down** | Clicking [View source rows] opens a slide-over panel showing the actual data rows that produce the figure. Columns from the source data, filterable. This is the "Click 12% → see the 47 rows" from the PRD. |
| **Checks list** | One row per reconciliation check (A–E per architecture). Shows check name, pass/fail/warn status, failure details inline, suggested fix, and action buttons. |
| **Fix actions** (blocking mode only) | Per failed check: **[Apply fix]** (applies the suggested fix, re-runs verification), **[Dismiss]** (user overrides — requires typed reason, logged to audit trail), **[Edit narrative]** (returns to Screen 2 with the narrative text editable). Per weak-significance warning: **[Acknowledge weak trend]** (user accepts, logged). |
| **Assumptions list** | Grouped by flag type (EXPLICIT → PATTERN → INFERRED). EXPLICIT: display only, no action needed. PATTERN: **[Acknowledge]** or **[Challenge]** (challenge → returns to Screen 2 to edit narrative). INFERRED: **[Sign off]** (requires click, logged) or **[Reject]** (→ edit narrative on Screen 2). |
| **Gate status bar** (blocking mode) | Sticky at bottom. Shows remaining blockers: failed checks count + unsigned assumptions count. "Proceed to Render →" button disabled while any blocker remains. Enables only when: all checks pass (or dismissed with reason) AND all PATTERN/INFERRED assumptions acknowledged/signed off. |
| **Read-only footer** (read-only mode) | Replaces gate status. Shows verification timestamp, overall pass status, download links. No action buttons on figures/checks/assumptions — all fix/sign-off controls hidden. |

### States

| State | Trigger | Behavior |
|---|---|---|
| **Verifying** | Entered from Screen 2 | Spinner with "Running 5 reconciliation checks..." Progress updates as each check completes. |
| **All passed** (blocking) | Every check passes | Green banner. Figures table all green. Gate status: "All checks passed. Proceed to Render →" enabled. Assumptions may still need sign-off (gate tracks both). |
| **Failures found** (blocking) | One or more checks fail | Red banner with count. Figures tab shows failures first (sorted to top). Checks tab badges the failures. Proceed disabled. |
| **Fix applied** | User clicks [Apply fix] on a check | Check re-runs. If passes, status updates inline (animated ✗ → ✓). Gate status count decrements. |
| **Dismissed** | User clicks [Dismiss] on a failure | Modal: "Why are you dismissing this?" + required text input + "I accept responsibility" checkbox. On confirm: check status → ⊘ dismissed. Logged to `audit_log`. Gate status decrements. |
| **All resolved** (blocking) | All checks pass/dismissed + all assumptions signed off | Green banner. "Proceed to Render →" enables. |
| **Read-only** | Entered from post-render (via progress rail or HTML audit link) | Same layout, all action buttons hidden. Banner shows timestamp. Dismissed items show dismissal reason inline. |

### Interaction flow (blocking gate — Riya's path)

1. Screen loads, verification runs (3–5 seconds).
2. Banner shows result. Riya checks the Figures tab first — scans for red rows.
3. One mismatch: $1.1M EBIT. She expands it, sees 5.3% variance, clicks [View source rows] to inspect.
4. Decides the 12 null-cost rows are the problem. Clicks [Apply fix] → system re-runs Check B → passes.
5. Switches to Assumptions tab. Signs off on one INFERRED assumption ("cost spike driven by headcount") — she knows this is true from context the data doesn't capture.
6. Gate status: all clear. Clicks "Proceed to Render →."

---

## Cross-Screen Interaction Patterns

### Progress rail

Persistent across all three screens. Shows the 5-step pipeline: Ingest → Questions → Narratives → Verify → Render. Current step highlighted, completed steps have checkmarks and are clickable (navigation). Clicking a completed step returns to that screen with current state preserved.

### Back navigation

Each screen has a "← Back to [Previous]" link alongside the primary action. Back always preserves state — answers aren't lost, selections aren't cleared. Forward from a revisited screen may trigger regeneration (e.g., editing an answer on Screen 1 → narratives regenerate on Screen 2).

### Data threading

| Data | Created on | Consumed on |
|---|---|---|
| `schema_json`, `quality_report` | Ingest (out of scope) | Screen 1 (data context strip, question generation) |
| `questions_json` | Question Service | Screen 1 (question cards) |
| `answers_json` (incl. `parsed_intent`, `confidence`) | Screen 1 | Screen 2 (Q&A summary bar), Screen 3 (audit log) |
| `narratives` (text, angle, confidence, assumptions, viz) | Narrative Service | Screen 2 (cards + detail panel) |
| `deck_selections` (narrative_id, user_edits_text) | Screen 2 | Screen 3 (figures extracted from selected narrative) |
| `reconciliation_reports` (checks, figure_traces, passed) | Verify Service | Screen 3 (all tabs) |
| `audit_log` entries | Screens 1–3 (every action) | Screen 3 read-only mode |

---

## Data Gaps — Not Specified in Architecture

The following are needed by these screens but not present in the current architecture doc. Flagged for resolution before implementation.

### Gap 1: Assumption sign-off tracking

**Need:** Screen 3 requires per-assumption sign-off state (unsigned → acknowledged/signed-off → rejected) with user attribution and timestamp.

**Current state:** `narratives.assumptions_json` stores `[{assumption, flag_type, confidence}]` but has no sign-off fields.

**Suggested fix:** Either extend `assumptions_json` entries with `{signed_off_by, signed_off_at, action: 'acknowledged'|'signed_off'|'rejected'}`, or create a separate `assumption_signoffs` table:
```sql
CREATE TABLE assumption_signoffs (
  id UUID PRIMARY KEY,
  narrative_id UUID REFERENCES narratives,
  assumption_index INT,
  action VARCHAR(20), -- 'acknowledged', 'signed_off', 'rejected'
  user_id UUID REFERENCES users,
  created_at TIMESTAMP DEFAULT now()
);
```

### Gap 2: Check dismissal tracking

**Need:** Screen 3 allows users to dismiss a failed check with a reason. This must be persisted and auditable.

**Current state:** `reconciliation_reports.checks_json` stores pass/fail booleans. No dismissal state or reason field.

**Suggested fix:** Extend `checks_json` entries to include `{status: 'pass'|'fail'|'dismissed', dismissed_by, dismissed_reason, dismissed_at}`, or create a `check_dismissals` table.

### Gap 3: Fix-application API endpoint

**Need:** Screen 3's [Apply fix] button needs an endpoint that applies a suggested fix (e.g., exclude rows) and re-runs verification.

**Current state:** No endpoint for this. The architecture has `POST /select-narrative` returning a verification report, but no endpoint for "re-verify after applying a fix."

**Suggested fix:** Add `POST /api/v1/decks/{deck_id}/apply-fix` with payload `{check_name, fix_type, parameters}` returning an updated `reconciliation_report`.

### Gap 4: Per-figure confidence (minor)

**Need:** The Figures tab would benefit from showing per-figure match confidence (exact match vs. within-tolerance vs. mismatch).

**Current state:** `figure_traces` stores `{figure_value, source_rows, formula}` but no tolerance/match-quality indicator.

**Suggested fix:** Add `match_status: 'exact'|'within_tolerance'|'mismatch'` and `variance_pct` to each figure trace entry.

### Gap 5: Assumption challenge → narrative edit round-trip

**Need:** When a user rejects/challenges an assumption on Screen 3, the system should return to Screen 2 with the relevant assumption highlighted and the narrative text editable at the relevant passage.

**Current state:** The architecture's Adaptation Service handles re-answering questions but doesn't model assumption-driven narrative edits.

**Suggested fix:** This may be handleable in the UI layer alone (deep-link back to Screen 2 with a query param like `?highlight=assumption-3`), but confirm whether assumption rejection should trigger narrative regeneration or just allow manual text editing.

---

## Accessibility Floor

- All interactive elements keyboard-navigable (tab order: progress rail → main content top-to-bottom).
- Figures table and checks list are proper `<table>` elements with headers, not div grids.
- Status indicators (✓/✗/⚠) paired with text labels — never color-only.
- Confidence percentages include aria-label with semantic meaning (e.g., `aria-label="confidence 86 percent, high"`).
- Focus management: transitioning between screens places focus on the first meaningful element (mode banner on Screen 3, first question on Screen 1).
- [Apply fix] and [Dismiss] actions require confirmation (no single-click destructive actions).
