# Product Requirements Document: Automated Deck Generation System

**Version:** 1.0  
**Date:** 2026-06-10  
**Status:** Ready for Design

---

## Executive Summary

A narrative verification engine generating boardroom-ready presentations (PPTX + HTML) from multi-source data in hours instead of weeks. 

**Core Moat:** Figure reconciliation + inference flagging + multi-narrative curation = trust competitors can't match.

**Positioning:** "Intelligence + Speed + Trust for boardroom narratives"

---

## Problem & Opportunity

**Pain:** Creating complex data decks takes weeks (manual, error-prone). Tools like Tableau lack narrative; tools like Beautiful.ai lack rigor.

**Opportunity:** CFOs and board admins need fast, trustworthy deck generation with mandatory figure verification.

---

## Product Vision

**What it's NOT:** Chart generator. Deck template engine.

**What it IS:** Narrative verification engine. Users upload data → answer 4-5 questions → curate from 2-3 AI narratives → system verifies every number → render auditable boardroom deck.

---

## Core Features (MVP)

### 1. Multi-Format Ingestion + Validation
- CSV, Excel, PDF, DB, S3
- Auto schema detection + quality checks (duplicates, encoding, missing data)
- User sign-off before proceeding

### 2. Interactive Question Engine
- 4-5 targeted free-text questions (system asks based on data structure)
- Rule-based parsing with confidence scores (< 70% → clarifying follow-up)
- Pre-filled suggestions for unanswered questions

### 3. Narrative Generation (2-3 Options)
- Each includes: viz recommendation + narrative text + confidence score + assumption flags
- Grounded in data structure + user intent (never hallucinate)
- User picks primary, can edit or override viz

### 4. Mandatory Reconciliation (BLOCKING)
- Every number linked to source rows
- Reconciliation checks: sum-of-parts validation, data consistency
- Halts rendering if any check fails
- Visual proof: "Click 12% → See the 47 rows"

### 5. Dual Output
- **PPTX:** Boardroom format, click-through narrative
- **HTML:** Audit-ready, interactive, all Q&As + assumptions + edits logged

### 6. Full Adaptability
- View question history, re-answer anytime (narratives auto-regenerate)
- Scenario branching (v1, v2, v3 with different assumptions)
- What-if scenarios ("If revenue > $10M, emphasize growth")

---

## Trust Architecture (Priority Order)

1. 🔴 **Figure Reconciliation** → Every number verified, blocking render
2. 🔴 **Inference Flagging** → Confidence scores, assumption sign-off required
3. 🟠 **Parsing Transparency** → Confidence scoring, clarifying follow-ups on ambiguity
4. 🟠 **Data Validation** → Quality checks before questions, user acknowledgment
5. 🟡 **Adaptability** → Question history, versioning, re-answer capability

---

## vs. Tableau

| **Dimension** | **Tableau** | **Us** |
|---|---|---|
| Time-to-insight | Days/weeks | Hours |
| Narrative | None | AI-curated + verified |
| Auditability | Row-level security | Figure reconciliation + inference flags |
| Format | Dashboard | Boardroom deck (PPTX) |
| Adaptability | Rebuild | Re-answer questions |

---

## Workflow (Happy Path: 10 Minutes)

1. Upload data → validate (30 sec)
2. Answer 4-5 questions (5 min)
3. Pick narrative (2 min)
4. System verifies figures (1 min)
5. Render PPTX + HTML (1 min)

---

## Scope

**MVP Must-Have:**
1. Multi-format ingest + validation
2. Question engine (4-5 free-text)
3. Narrative generation (2-3 options)
4. Reconciliation + auditability
5. PPTX + HTML output

**V1 Should-Have:**
6. Inference flagging + assumptions
7. What-if scenarios
8. Narrative versioning
9. Parsing error handling

**V2+ Nice-to-Have:**
10. Reusable question templates
11. Role-based approval workflows
12. Real-time data refresh

---

## Success Metrics

- **Adoption:** 50+ beta customers in 3 months
- **Trust:** 95%+ figures pass reconciliation (zero customer-found errors)
- **Speed:** < 15 min avg deck generation
- **Retention:** 70%+ generate 2nd deck within 30 days
- **NPS:** 50+ (benchmark: 60+)

---

## Open Engineering Questions

1. Question prioritization algorithm
2. Story-angle detection in data
3. Reconciliation check taxonomy (blocking vs. warnings)
4. Confidence scoring methodology
5. What-if cascading mechanics
6. Role-based workflows
7. Mobile UX strategy
8. Pricing model implications

---

## Data Sources (Roadmap)

- **MVP:** CSV, Excel
- **V1:** SQL (PostgreSQL, MySQL)
- **V2:** S3, Salesforce, HubSpot
- **V3+:** Snowflake, BigQuery, real-time

---

## Next: Design → Architecture → Validation

