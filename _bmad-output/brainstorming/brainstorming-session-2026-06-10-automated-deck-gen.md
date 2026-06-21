---
stepsCompleted: [1]
session_topic: "Automated Deck Generation System - Features, Visualization Types, Trust, Adaptability, and Tableau Differentiation"
session_goals: "Expand feature set and visualization possibilities; identify trust/adaptability issues and design moats; articulate defensible differentiation vs Tableau dashboards"
selected_approach: "Custom Structured Brainstorm - Three Parallel Tracks"
context_file: null
techniques_used: ["Interactive Discovery", "Multi-Narrative Generation", "Trust Architecture Design", "Competitive Positioning"]
ideas_generated: 250+
competitive_landscape: "Tableau dashboards (gold standard for trust), PowerPoint + manual, Gamma, Beautiful.ai, internal BI platforms"
session_quality_focus: "Quality depth over quantity - battle-tested, defensible ideas"
session_status: "COMPLETE - Core architecture, positioning, and MVP scope locked"
key_decisions_locked: 7
open_questions_for_implementation: 8
---

# Automated Deck Generation System — Brainstorming Session

**Date:** 2026-06-10  
**Facilitator:** Carson (Elite Brainstorming Specialist)  
**Participant:** panchu  
**Session Type:** Structured Depth Exploration — Three Parallel Tracks

---

## Session Context

### The Core Challenge

Build an **Automated Deck Generation System** that:
- Ingests multi-format data (CSV, Excel, PDF, DB, S3)
- Accepts plain-English briefs
- Generates boardroom-ready presentations (PPTX + HTML)
- Cross-checks every figure against source data before rendering
- **Defensibly beats Tableau dashboards** on narrative + trust + adaptability

### Competitive Context

**Tableau Dashboards** = The Comparison Point
- ✅ Deep trust (enterprise-grade reconciliation, audit trails, data lineage)
- ✅ Rich interactivity (drill-down, filters, real-time updates)
- ✅ Visual sophistication (charts, maps, advanced analytics)
- ❌ Static output, narrative-poor, requires technical skill to author
- ❌ Limited to dashboard UX (no storytelling)

**Other Players:**
- Gamma, Beautiful.ai (design, not data rigor)
- PowerPoint + manual (tedious, error-prone)
- Internal BI tools (siloed, hard to adapt)

### Session Goals (Quality-Depth Framing)

1. **Features + Visualization Types:** What *specific* capabilities make this not just functional but *compelling*?
2. **Trust & Adaptability Moats:** Where are the failure points? How do we make trust and flexibility our defensible advantage?
3. **Tableau Differentiation:** What can *we* do that Tableau *can't* or won't?

---

## Brainstorm Tracks

### TRACK 1: Features & Visualization Types
*What capabilities and visual output options make this system indispensable?*

**Key Decisions Locked:**
- ✅ Smart Viz (A) + Narrative Intelligence (B) are the core moat (not Adaptability)
- ✅ Inference is acceptable **if flagged** (not refusing outright)
- ✅ Negotiation layer required between Viz + Narrative (one doesn't trump the other)
- ✅ **Multiple Narrative Strategy:** System generates 2-3 valid interpretations; user curates
- ✅ **Interactive Discovery:** System asks 4-5 targeted questions based on data structure (after data quality validation)
- ✅ **Question Format:** Free text (user answers in their own words, system parses intent)
- ✅ **Question Iteration:** Users can go back to re-answer questions at any point; narratives regenerate
- ⚠️ **Highest Risk:** Narrative hallucination—prevented by user-system collaboration
- 🤔 **Open Design Questions:**
  - Question prioritization: How to pick the top 4-5 questions from ambiguities?
  - Follow-up depth: When to ask deeper follow-ups vs. letting user see generated narratives?
- ✅ **Parsing & Error Handling (Decided):**
  - Ambiguous answers → Ask clarifying follow-up (not guess)
  - Missing answers → Offer pre-filled suggestions (user accepts/rejects)
  - Parsing approach: Pattern-matched intent extraction (rule-based + lightweight NLP, not LLM)
  - Sensitivity: System tracks confidence in parsing (flags uncertain inferences)

---

### TRACK 2: Trust & Adaptability Issues
*What breaks? Where does trust erode? How do we architect adaptability?*

**Architecture Foundation (from TRACK 1):**
The interactive question engine IS the trust mechanism. Every user answer → audit trail → narrative grounding.

**Core Trust Threats (Ranked by Severity):**

1. 🔴 **CRITICAL: Figure Reconciliation** (2) — If numbers don't match source, deck is worthless
2. 🔴 **CRITICAL: Inference Without Context** (3) — Wrong conclusions sound confident
3. 🟠 **HIGH: Parsing Errors** (4) — System misunderstands user intent → wrong narratives
4. 🟠 **HIGH: Data Quality** (1) — Garbage source data → garbage narratives
5. 🟡 **MEDIUM: Adaptability Lock-In** (5) — System feels rigid but can be worked around

---

**Threat 1: Data Quality Disasters**
- Bad source data (duplicates, encoding errors, missing values)
- User uploads "clean" data that's actually corrupted
- System generates narratives from garbage
- Narrative sounds plausible; board believes it; decision made on false premise

**Threat 2: Figure Reconciliation Failures**
- A number in the deck doesn't match the source
- User clicks "Where does this come from?" → dead link or wrong data
- System claims verification happened; verification is broken
- Trust implodes

**Threat 3: Inference Without Context**
- System generates: "Cost spike is temporary disruption"
- But it's actually structural; user didn't catch it
- Deck goes to board; board makes wrong decision
- System gets blamed (or worse, user gets blamed for not catching system error)

**Threat 4: Parsing Errors -> Wrong Narratives**
- User says: "We're cautious about cost growth"
- System parses: "Cost growth is the opportunity"
- System generates growth-focused narrative
- User is horrified; loses trust in system

**Threat 5: Adaptability Lock-In**
- User generates Deck v1 with Question Answer Set A
- Market changes; user needs different narrative
- System won't re-answer questions; forces regeneration from scratch
- User feels system is rigid, not adaptive

---

### TRACK 3: Tableau Differentiation
*Where do we win? What's our unique competitive position?*

**Direct Comparison: Tableau vs. Our System**

| **Dimension** | **Tableau** | **Our System** | **Winner** |
|---|---|---|---|
| **Data Input** | Manual schema design; requires technical setup | Multi-format auto-ingest (CSV, Excel, PDF, DB, S3) | **Ours** (velocity) |
| **Visualization** | Chart library (100+ types, highly interactive) | Intelligent auto-recommend + user override | **Tableau** (richness, but **Ours** for speed) |
| **Narrative** | Dashboard UX; user interprets | AI-generated + multi-option + user-curated | **Ours** (storytelling) |
| **Output** | Interactive dashboards (web-native) | Boardroom decks (PPTX) + audit-ready HTML | **Ours** (presentation format) |
| **Trust/Auditability** | Row-level security, data lineage, audit logs | Figure reconciliation, inference flagging, assumption tracking | **Ours** (narrative audit trail) |
| **Adaptability** | Filters/drill-down (reactive) | Question-based re-generation (proactive), what-if scenarios | **Ours** (narrative flexibility) |
| **Time to Insight** | Days (design, build, publish dashboard) | Hours/Minutes (upload, brief, verify narratives, render) | **Ours** (10-100x faster) |
| **Collaboration** | Viewer/Editor permissions | Narrative versioning, branching, comment threads | **Ours** (for deck-based collaboration) |

**Defensible Moat: The Narrative + Trust Combination**

- Tableau = "Show the data, user interprets" (CEO has to be the analyst)
- Beautiful.ai = "AI generates deck, pray it's right" (trust issues)
- **Our System = "AI suggests narrative, user verifies, system reconciles"** (trust built-in)

**Positioning:** "Deck generation for orgs that can't compromise on trust. Faster than PowerPoint. Smarter than dashboards. Auditable."

---

## Final Architectural Decisions

### **System Workflow (End-to-End)**

1. **Intake Phase**
   - User uploads data (multi-format)
   - System validates schema + quality
   - Flags data issues; user resolves or accepts with caveats
   - ✅ DECISION: Validation happens before questions (user sees clean data)

2. **Discovery Phase**
   - System analyzes data structure, detects ambiguities
   - Asks 4-5 targeted questions (Tier 1 + 1 Tier 2)
   - User answers in free text; system parses with confidence scoring
   - If parsing confidence < 70%, system asks clarifying follow-up
   - If user skips question, system offers pre-filled suggestion
   - ✅ DECISION: Free-text answers, rule-based parsing, max 5 questions upfront

3. **Narrative Generation Phase**
   - System generates 2-3 valid narratives (based on data structure + user answers)
   - Each narrative includes:
     - Recommended viz + justification
     - Generated narrative text with inference flags
     - Confidence score (50-100%)
     - Assumption callouts
   - ✅ DECISION: 2-3 narratives max (not 9); narratives grounded in data structure + user intent

4. **Negotiation Phase**
   - User reviews narratives
   - Picks primary narrative
   - System asks follow-ups if needed (refines assumptions)
   - User can edit narrative text, override viz recommendation
   - All changes logged
   - ✅ DECISION: Questions can come before or after narrative selection; user decides

5. **Verification Phase** (CRITICAL)
   - System runs reconciliation checks:
     - Sum of parts = whole?
     - Data consistency checks
     - Inference assumptions validated
   - Every number linked to source rows
   - If any check fails: halt and show user (don't render bad deck)
   - ✅ DECISION: Verification is blocking (not optional); halts rendering on failure

6. **Rendering Phase**
   - PPTX generated (boardroom format)
   - HTML generated (audit trail + interactive review)
   - Audit log included: Q&As, assumptions, edits, verification results
   - ✅ DECISION: Dual output (PPTX + HTML); audit trail embedded in both

7. **Adaptation Phase**
   - User can view question history
   - Can re-answer questions; narratives regenerate
   - Can create branches (v1, v2, v3 based on different assumptions)
   - What-if scenarios: "If [variable] changes, emphasize [different story]"
   - ✅ DECISION: Full re-answer capability; question history saved; versioning built-in

---

### **Core Feature Stack (Prioritized)**

**Must-Have (MVP):**
1. Multi-format data ingestion + quality validation
2. Interactive question engine (4-5 questions)
3. 2-3 narrative generation + user curation
4. Figure reconciliation + auditability
5. PPTX + HTML output with embedded audit trail

**Should-Have (V1):**
6. Inference flagging + assumption surfacing
7. What-if scenarios (simple)
8. Narrative branching + versioning
9. Parsing error handling (clarifying follow-ups)

**Nice-to-Have (V2+):**
10. Reusable question templates (across similar decks)
11. Role-based approval workflows (CFO approves narratives before board sees them)
12. Real-time data refresh + deck auto-update

---

### **Trust Architecture (Locked)**

**Defense Priority (aligned with threat ranking):**

1. 🔴 **Reconciliation First**
   - Every number traceable to source
   - Reconciliation checks blocking (not warnings)
   - Visual proof in the deck ("Click 12% → See the 47 rows that made it")

2. 🔴 **Inference Flagging**
   - Every inference scored 0-100% confidence
   - Assumptions explicit ("This assumes [X]")
   - User sign-off required before rendering

3. 🟠 **Parsing Transparency**
   - Parsing confidence scored
   - Ambiguous answers trigger follow-ups
   - Audit trail shows what user said vs. what system understood

4. 🟠 **Data Validation**
   - Quality checks before questions
   - User acknowledges issues upfront
   - Validation results in audit trail

5. 🟡 **Adaptability**
   - Question history saved
   - Full re-answer + regeneration capability
   - Scenario branching optional (nice-to-have)

---

## Tableau Competitive Positioning (Final)

**What Tableau Excels At (Concede):**
- ✅ Interactive exploration (drill-down, filters, real-time)
- ✅ Chart variety and statistical sophistication
- ✅ Large datasets (performance optimized)

**Where We Win (Defend):**
- ✅ **Time-to-insight:** Upload + brief + verify = 30 min, vs. Tableau's weeks
- ✅ **Narrative quality:** Curated stories, not dashboard noise
- ✅ **Trust & auditability:** Full inference + reconciliation trail
- ✅ **Format:** Boardroom decks (PPTX) resonate with C-suite; dashboards don't
- ✅ **Adaptability:** Re-answer questions, narratives change; Tableau requires redesign

**Positioning Statement:**
*"For organizations that need boardroom-ready narratives from complex data, verified for accuracy, and generated in hours—not weeks. If you're choosing between PowerPoint (slow, manual, error-prone) and Tableau (interactive but lacks narrative), we're the third option: Intelligence + Speed + Trust."*

---

## Deep Dive: Multi-Narrative Architecture

**The Core Concept:**
Instead of generating *one* narrative + viz combo, the system generates 2-3 defensible interpretations of the data, each with:
- A recommended viz (with justification)
- A narrative framing (with inference flags)
- A confidence score (based on data completeness, assumption validity)
- User choice and annotation path

**Example:** Sales data with seasonal patterns + Q2 dip

**Narrative Option 1: "Risk & Mitigation"**
- Viz: Year-over-year comparison (bars) + anomaly highlighted
- Story: Q2 underperformance vs. historical trend; mitigation underway
- Inferences flagged: Root cause (FLAGGED: not in data, requires user context)
- Confidence: High (data clear, narrative grounded in viz)

**Narrative Option 2: "Seasonal Context"**
- Viz: Full year + seasonal decomposition (time series + bands)
- Story: Q2 dip is within seasonal norm; full-year trajectory on track
- Inferences flagged: Seasonality pattern (FLAGGED: derived from historical data, not current brief)
- Confidence: Medium (pattern exists, but context-dependent)

**Narrative Option 3: "Drilling Into the Dip"**
- Viz: Stacked bar (by product line / region / segment)
- Story: Q2 decline driven by [specific segment]; others stable
- Inferences flagged: Attribution (FLAGGED: correlation, not causation)
- Confidence: High if data has breakdown; Low if not

**User then:**
- Picks one narrative as "primary"
- Can edit/combine them
- Can reject all three and start fresh
- All choices are logged (auditability)

---

## Final Architectural Decisions

### **System Workflow (End-to-End)**

1. **Intake Phase**
   - User uploads data (multi-format)
   - System validates schema + quality
   - Flags data issues; user resolves or accepts with caveats
   - ✅ DECISION: Validation happens before questions (user sees clean data)

2. **Discovery Phase**
   - System analyzes data structure, detects ambiguities
   - Asks 4-5 targeted questions (Tier 1 + 1 Tier 2)
   - User answers in free text; system parses with confidence scoring
   - If parsing confidence < 70%, system asks clarifying follow-up
   - If user skips question, system offers pre-filled suggestion
   - ✅ DECISION: Free-text answers, rule-based parsing, max 5 questions upfront

3. **Narrative Generation Phase**
   - System generates 2-3 valid narratives (based on data structure + user answers)
   - Each narrative includes:
     - Recommended viz + justification
     - Generated narrative text with inference flags
     - Confidence score (50-100%)
     - Assumption callouts
   - ✅ DECISION: 2-3 narratives max (not 9); narratives grounded in data structure + user intent

4. **Negotiation Phase**
   - User reviews narratives
   - Picks primary narrative
   - System asks follow-ups if needed (refines assumptions)
   - User can edit narrative text, override viz recommendation
   - All changes logged
   - ✅ DECISION: Questions can come before or after narrative selection; user decides

5. **Verification Phase** (CRITICAL)
   - System runs reconciliation checks:
     - Sum of parts = whole?
     - Data consistency checks
     - Inference assumptions validated
   - Every number linked to source rows
   - If any check fails: halt and show user (don't render bad deck)
   - ✅ DECISION: Verification is blocking (not optional); halts rendering on failure

6. **Rendering Phase**
   - PPTX generated (boardroom format)
   - HTML generated (audit trail + interactive review)
   - Audit log included: Q&As, assumptions, edits, verification results
   - ✅ DECISION: Dual output (PPTX + HTML); audit trail embedded in both

7. **Adaptation Phase**
   - User can view question history
   - Can re-answer questions; narratives regenerate
   - Can create branches (v1, v2, v3 based on different assumptions)
   - What-if scenarios: "If [variable] changes, emphasize [different story]"
   - ✅ DECISION: Full re-answer capability; question history saved; versioning built-in

---

### **Core Feature Stack (Prioritized)**

**Must-Have (MVP):**
1. Multi-format data ingestion + quality validation
2. Interactive question engine (4-5 questions)
3. 2-3 narrative generation + user curation
4. Figure reconciliation + auditability
5. PPTX + HTML output with embedded audit trail

**Should-Have (V1):**
6. Inference flagging + assumption surfacing
7. What-if scenarios (simple)
8. Narrative branching + versioning
9. Parsing error handling (clarifying follow-ups)

**Nice-to-Have (V2+):**
10. Reusable question templates (across similar decks)
11. Role-based approval workflows (CFO approves narratives before board sees them)
12. Real-time data refresh + deck auto-update

---

## 🎯 Session Synthesis: The Breakthrough

**The Core Insight:** You're not building a *chart generator*. You're building a *narrative verification engine* that happens to output decks.

**The Moat:** Figure reconciliation + inference flagging + multi-narrative curation = trust that competitors can't match.

**The Positioning:** "Intelligence + Speed + Trust for boardroom narratives"

---

## Key Decisions Recap

✅ **Architecture:** Ingest → Validate → Question → Narrative Gen → Negotiate → Verify → Render  
✅ **Questions:** Free-text, rule-based parsing, max 5 upfront, clarifying follow-ups for ambiguity  
✅ **Narratives:** 2-3 options max, grounded in data structure + user intent, never hallucinate  
✅ **Verification:** Blocking (halts rendering if reconciliation fails), figure-level traceability  
✅ **Trust Priority:** Figure reconciliation > Inference > Parsing > Data quality > Adaptability  
✅ **Output:** PPTX for boardroom, HTML for audit trail  
✅ **vs. Tableau:** We're narrative + speed; they're exploration + interactivity  

---

## Open Questions for Implementation Phase

1. Question prioritization algorithm (detecting top 4-5 from ambiguities)
2. Narrative generation engine (identifying story angles in data)
3. Reconciliation logic (which checks block vs. warn)
4. Inference confidence scoring methodology
5. What-if cascading mechanics
6. Collaboration/approval workflows
7. Mobile UX + accessibility
8. Pricing model implications

---

## Next Steps (Beyond Brainstorm)

**Immediate:**
- Validate positioning with early customers
- Design UX flows (question interface, narrative picker)
- Build reconciliation logic (highest risk component)
- Plan MVP scope

**Short-term:**
- Technical architecture
- Security/compliance framework
- Integration strategy

**Product Decisions:**
- Launch data sources (CSV first? DB?)
- Template library scope (generic vs. industry-specific)
- Go-to-market motion

---

**Session Complete.** You moved from "automate deck generation" to "build a narrative verification engine with defensible trust moats." That's a product. 🎯



