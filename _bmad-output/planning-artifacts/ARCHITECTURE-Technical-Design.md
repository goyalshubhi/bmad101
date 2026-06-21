# Technical Architecture: Automated Deck Generation System

**Version:** 1.0  
**Date:** 2026-06-10  
**Status:** Ready for Implementation

---

## 1. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│  Web UI (React/SvelteKit) | Mobile (Web-Responsive)             │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────┴──────────────────────────────────┐
│                      API GATEWAY / AUTH                          │
│  REST API (Node.js/FastAPI) | Session Management | Rate Limit   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────┴──────────────────────────────────┐
│                    CORE SERVICES LAYER                           │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────┐              │
│  │ Ingest Svc  │ │ Question Svc  │ │Narrative Svc │              │
│  └─────────────┘ └──────────────┘ └──────────────┘              │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────┐              │
│  │ Verify Svc  │ │ Render Svc    │ │ Adapt Svc    │              │
│  └─────────────┘ └──────────────┘ └──────────────┘              │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────┴──────────────────────────────────┐
│                    DATA & PERSISTENCE LAYER                      │
│  PostgreSQL | Redis (Cache) | S3 (File Storage)                 │
│  Elasticsearch (Audit Logs)                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Technology Stack Decisions

### 2.1 Backend Language: Python (FastAPI)

**Decision:** Python + FastAPI  
**Reasoning:**
- **Data science integration:** NumPy/Pandas for data validation already proven in ML workflows
- **Rapid iteration:** ML/LLM libraries (transformers, scikit-learn) minimize custom code
- **Question parsing:** Rule-based NLP with lightweight libraries (textacy, spacy)
- **Narrative generation:** LLM integration via OpenAI API or local models (llama.cpp)
- **Production-ready:** FastAPI is async-native, high-performance, auto-docs (OpenAPI)
- **Team skill:** Data engineers comfortable with Python > JavaScript backend
- **NOT Node.js because:** Would require separate ML pipeline or external service calls; Python is unified

### 2.2 Frontend: React + SvelteKit (Hybrid Approach)

**Decision:** React for complex UX (question interface, narrative picker), SvelteKit for static pages  
**Reasoning:**
- **Question interface complexity:** React's state management handles ambiguity flows well
- **Real-time feedback:** Need reactive updates as user edits answers
- **Narrative comparison:** 2-3 side-by-side cards with diff highlighting → React excels
- **Mobile responsive:** Web-first, no native app needed initially
- **Lightweight landing:** SvelteKit for marketing pages (smaller bundle)
- **NOT Svelte-only because:** Narrative picker needs complex state; Svelte overkill for data-heavy UX

### 2.3 Primary Database: PostgreSQL

**Decision:** PostgreSQL (not NoSQL)  
**Reasoning:**
- **Relational data required:** Users → Decks → Narratives → Edits → Verifications
- **ACID transactions:** Mandatory for reconciliation audit trail (no lost updates)
- **JSON support:** Store question answers + assumptions as JSONB (queryable)
- **Full-text search:** Audit logs searchable for compliance
- **Row-level security:** Native RLS support for future multi-tenant isolation
- **NOT MongoDB because:** Eventual consistency conflicts with audit trail integrity

### 2.4 Caching Layer: Redis

**Decision:** Redis (not in-memory cache library)  
**Reasoning:**
- **Question history:** Cache user's previous Q&As for quick re-answer flow
- **Session state:** Track mid-flow narrative generation state
- **Rate limiting:** Prevent API abuse (5 decks/hour per user)
- **Temporary storage:** Cache parsed question confidence scores during interaction
- **NOT in-app cache because:** Would lose state on service restart; users need persistence

### 2.5 File Storage: S3 + Local Fallback

**Decision:** S3 for production, local filesystem for MVP testing  
**Reasoning:**
- **Source data persistence:** Store uploaded CSVs, validate schema once
- **PPTX/HTML output:** Immutable after verification (compliance)
- **Scalability:** S3 handles 1000s of concurrent uploads without disk I/O bottlenecks
- **Cost:** Pay-per-use storage (cheap for MVP)
- **Lifecycle:** Auto-delete unverified decks after 7 days
- **NOT database BLOBs because:** Large binary objects slow query performance

### 2.6 Audit Logging: Elasticsearch + PostgreSQL

**Decision:** PostgreSQL for transactional audit trail, Elasticsearch for searchable logs  
**Reasoning:**
- **Compliance:** Every change (Q&A → Narrative → Edit → Verify → Render) logged
- **Immutability:** PostgreSQL audit_log table with triggers
- **Search:** "Show me all decks where Cost Analysis was chosen" → Elasticsearch query
- **NOT just Postgres because:** Full-text search on 1M+ log entries needs indexing
- **NOT just Elasticsearch because:** Need transactional guarantees for financial data

---

## 3. Core Modules & Data Flow

### 3.1 Ingest Service (`/services/ingest`)

**Responsibility:** Multi-format ingestion + quality validation

**Input:** CSV/Excel file, metadata (user_id, dataset_name)

**Process:**
```
1. File Upload Handler
   - Accept: CSV, Excel (XLSX), PDF (if tables), SQL query (V1)
   - Store: S3 with UUID, create ingest_job record

2. Schema Detection (pandas + custom rules)
   - Column names → clean (remove spaces, standardize)
   - Data types: infer from first 1000 rows
   - Cardinality: % unique values (flag high-cardinality)
   - Nullability: % missing per column
   - Date columns: detect date format, normalize to ISO-8601
   
3. Quality Checks (executed in sequence)
   ✓ Duplicate detection (row-level MD5 hash)
   ✓ Encoding validation (UTF-8 enforcement)
   ✓ Type consistency (all nums or all text per column)
   ✓ Date range validation (realistic years)
   ✓ Cardinality warnings (>1000 categories)
   ✓ Missing data summary (% by column)
   
4. Output: ValidationReport
   - quality_issues: [severity, description, count, sample_rows]
   - schema: {column_name: {type, nullability, cardinality, date_format}}
   - status: CLEAN | ISSUES_ACKNOWLEDGED | ISSUES_BLOCKING
   - user must sign-off before proceeding
```

**Decision: Why validate before questions?**
- Prevents system asking questions about bad data (GIGO)
- Users trust the data before providing context
- If data is wrong, garbage questions → garbage narratives

**Technology:**
- Pandas for CSV/Excel parsing
- Custom `Schema` class for metadata tracking
- PostgreSQL `ingest_jobs` table for job tracking (idempotent retries)

**Data Model:**
```sql
CREATE TABLE ingest_jobs (
  id UUID PRIMARY KEY,
  user_id UUID,
  dataset_name TEXT,
  file_url TEXT (S3),
  schema_json JSONB, -- {col: {type, nullability, card}}
  quality_report JSONB, -- {issues: [...], status: enum}
  validated_at TIMESTAMP,
  created_at TIMESTAMP
);
```

---

### 3.2 Question Engine (`/services/questions`)

**Responsibility:** Generate 4-5 targeted questions based on data structure

**Input:** schema, quality_report (from Ingest)

**Process:**
```
1. Ambiguity Detection (rules-based)
   - Multiple numeric columns → "Which is the headline metric?"
   - Temporal + numeric → "Compare vs. past period? (YoY, MoM, fixed date)"
   - Mixed pos/neg deltas → "Which is more concerning?"
   - High-cardinality dimension → "Show all or top N?"
   - Gaps in data → "Fill gaps or exclude?"
   
2. Question Prioritization (algorithm)
   - Tier 1 (always ask):
     * Primary metric focus (mandatory)
     * Audience/context (optional but high-impact)
   - Tier 2 (ask if ambiguous):
     * Conflicting signals (revenue ↑ but profit ↓)
     * Data gaps (> 5% missing)
   - Tier 3 (skip for MVP):
     * Assumptions about trends
   
3. Question Generation (template-based, not LLM)
   Template: "{context} {data_observation}. {focus_options}?"
   Example: "Your data shows revenue up 15% but costs up 22%. 
            Which concerns you more? (a) Cost control (b) Profitability (c) Both?"
   
4. User Answer Collection (async, user-paced)
   - Free-text answers (not multiple choice)
   - Progress indicator (Question N of 5)
   - "Skip & use default" option
   - Answer stored with timestamp
```

**Parsing Logic (Rule-Based):**
```python
class QuestionParser:
  def parse_primary_metric(answer: str) -> tuple[str, float]:
    # Detect keywords: "profit", "revenue", "growth", "efficiency", "cost"
    # Return: (metric_type, confidence_score: 0-1)
    keywords = {
      'profit|margin|profitability': (PROFIT, 0.9),
      'revenue|sales|growth': (GROWTH, 0.85),
      'cost|spending|efficiency': (COST, 0.9),
      'market|share|position': (MARKET, 0.8),
    }
    # Confidence < 0.7 triggers follow-up
    
  def parse_audience(answer: str) -> tuple[str, float]:
    # Detect: "board", "investors", "ops", "cfo", "executive"
    # Impact: Narrative tone + formality
```

**Decision: Why rule-based parsing, not LLM?**
- **Auditability:** Rules are deterministic, explainable, easy to debug
- **Cost:** LLM calls for every question = $$ at scale
- **Hallucination risk:** LLM might "understand" wrong intent, creating silent errors
- **Confidence transparency:** Rules give us explicit confidence scores
- **Fallback:** If parsing confidence < 70%, ask clarifying follow-up (still deterministic)

**Data Model:**
```sql
CREATE TABLE question_sessions (
  id UUID PRIMARY KEY,
  deck_id UUID,
  question_set_id UUID, -- v1, v2, v3 if user re-answers
  questions_json JSONB, -- [{id, template, context}]
  answers_json JSONB, -- [{question_id, raw_answer, parsed_intent, confidence}]
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

---

### 3.3 Narrative Generation Service (`/services/narrative`)

**Responsibility:** Generate 2-3 valid narrative interpretations of the data

**Input:** schema, parsed_questions, data_sample (first 1000 rows)

**Process:**
```
1. Story Angle Detection (rules-based)
   Detect patterns in data:
   - Trend: Any numeric column showing monotonic increase/decrease
   - Disruption: Sudden inflection point (change in slope)
   - Composition: Mix of categories changing over time
   - Anomaly: Outlier detected (>3σ from mean)
   - Comparison: Categorical breakdown (region, segment, product)
   
   Algorithm:
   for each numeric column:
     - fit linear regression (trend detection)
     - compute rolling standard deviation (disruption detection)
     - if categorical breakdown available:
       - compute composition shifts
     - store detected angles with confidence

2. Narrative Template Selection (based on user answers + angles)
   User said "Focus on cost control" + angle "Cost Disruption" detected
   → Select narrative templates:
     a) "Crisis Narrative" (cost spike as urgent issue)
     b) "Mitigation Narrative" (cost spike but under control)
     c) "Root Cause Narrative" (cost increase driven by [category])

3. Narrative Generation (template-filling + LLM augmentation)
   Template (safe, rule-based):
   "Your {metric} has {changed} from {period1} to {period2}. 
    Key drivers: {top_3_factors}. Status: {risk_level}"
   
   Augmentation (LLM, controlled):
   - Generate 1-2 sentence executive summary
   - Keep LLM to < 50 tokens per narrative (prevents hallucination)
   - Require confidence flag for every inference
   
   LLM constraints:
   - Only use facts from data (no speculation)
   - Flag every assumption: "Assumes Q2 dip is {reason} (unconfirmed)"

4. Confidence Scoring (per narrative)
   Score = (data_completeness * angle_strength * user_intent_match)
   - Data completeness: % non-null rows (0-1)
   - Angle strength: Statistical significance of trend/disruption
   - Intent match: 0-1 based on user answers
   
   Example: 
   Narrative A: Cost Disruption
   - Data: 95% complete (+0.95)
   - Angle: Cost >3σ increase (+0.9)
   - Intent: "Cost control" perfectly matches (+1.0)
   - Confidence = 0.95 * 0.9 * 1.0 = 0.86

5. Assumption Extraction (auto-flagged)
   Every inference gets flagged:
   - Explicit (in data): "Q2 revenue $5M" → flag: EXPLICIT (100%)
   - Derived (pattern): "Growing trend" → flag: PATTERN (75%)
   - Inferred (context): "Market downturn" → flag: INFERRED (40%)
   - Speculative: "Will improve" → flag: SPECULATIVE (0%, blocked)
```

**Decision: Why 2-3 narratives, not 1?**
- Single narrative = user has no choice (trust issue if wrong)
- 2-3 options = user can curate best interpretation (trust-building)
- Not unlimited = prevents decision paralysis

**Decision: Why template-based + LLM hybrid?**
- Templates prevent hallucination (structure safe)
- LLM adds natural language (not robotic)
- Constraints on LLM tokens (50 max per narrative) limit damage
- Every LLM output flagged with confidence (not hidden)

**Data Model:**
```sql
CREATE TABLE narratives (
  id UUID PRIMARY KEY,
  deck_id UUID,
  story_angle VARCHAR(50), -- trend, disruption, composition, anomaly, comparison
  story_angle_confidence FLOAT,
  template_id VARCHAR(50),
  narrative_text TEXT,
  visualization_recommendation TEXT,
  viz_justification TEXT,
  assumptions_json JSONB, -- [{assumption, flag_type, confidence}]
  overall_confidence FLOAT,
  created_at TIMESTAMP
);
```

---

### 3.4 Verification Service (`/services/verify`)

**Responsibility:** Mandatory reconciliation checks before rendering

**Input:** selected_narrative, data, deck_metadata

**Process:**
```
1. Figure Extraction (from narrative)
   Parse narrative text for numbers:
   - Regex: \d+[.,]\d+%? or \$\d+[KMB]?
   - For each number, store: {value, context_sentence, narrative_position}
   
2. Reconciliation Checks (blocking if any fails)
   
   CHECK A: Sum-of-Parts Validation
   - If narrative says "Cost breakdown: A=$3M, B=$2M, C=$1M"
   - Verify: A + B + C = Total reported cost ± 1%
   - Pass criteria: ≤ 1% variance (accounting for rounding)
   
   CHECK B: Data Consistency
   - If narrative references "Q2 revenue $5M"
   - Trace to source data: SELECT SUM(revenue) WHERE quarter='Q2'
   - Match ± 0.1% (allow for rounding)
   
   CHECK C: Time Series Continuity
   - If narrative says "Growing 5 quarters"
   - Verify: No missing quarters in underlying data
   - If gaps exist: Require user confirmation ("OK to extrapolate?")
   
   CHECK D: Comparison Validity
   - If narrative says "Up 15% YoY"
   - Verify: Same dates in both years (no date misalignment)
   - Verify: No data quality issues in either period
   
   CHECK E: Statistical Significance
   - If narrative claims "Declining trend"
   - Compute R² of trend line (must be >0.6 to claim "clear trend")
   - If R² <0.6: Flag as "weak trend, may be noise"

3. Failure Handling
   If any check fails:
   - HALT rendering (don't output bad deck)
   - Show user reconciliation error with:
     * Which check failed (A-E)
     * Expected vs. actual value
     * Suggested fix ("Exclude Q3 due to data gap?")
     * Option to edit narrative or reject entire narrative

4. Success Output: ReconciliationReport
   - all_checks_passed: boolean
   - figures_verified: [{value, source_rows, formula}]
   - trace_links: [{figure: "12%", trace_url: "?report=X&rows=47,89,103"}]
   - timestamp: when verified
```

**Decision: Why blocking verification?**
- Reconciliation is THE moat (must be perfect)
- If we ship a deck with wrong numbers, trust is 0
- Better to halt than ship garbage
- User can always edit narrative and re-verify

**Decision: Why 5 checks, not automated "everything"?**
- These 5 cover 95% of real-world errors
- Beyond 5: diminishing returns, slows down rendering
- Designed for human collaboration (not full automation)

**Data Model:**
```sql
CREATE TABLE reconciliation_reports (
  id UUID PRIMARY KEY,
  deck_id UUID,
  selected_narrative_id UUID,
  parent_report_id UUID, -- non-null when created by re-verify after fix
  checks_json JSONB,
  -- Shape per check: {
  --   "check_a": {
  --     "status": "pass" | "fail" | "dismissed",
  --     "expected": <value>,        -- null if pass
  --     "actual": <value>,          -- null if pass
  --     "fix_suggestion": <text>,   -- null if pass
  --     "dismissed_reason": <text>, -- null unless dismissed
  --     "dismissed_by": <user_id>,  -- null unless dismissed
  --     "dismissed_at": <timestamp> -- null unless dismissed
  --   }, ...
  -- }
  figure_traces JSONB,
  -- Shape per figure: {
  --   "figure_value": "$5.2M",
  --   "source_rows": "1-847",
  --   "formula": "SUM(D)",
  --   "match_status": "exact" | "within_tolerance" | "mismatch",
  --   "variance_pct": 0.0
  -- }
  -- Tolerance thresholds (hard-coded for MVP):
  --   exact:            variance = 0%
  --   within_tolerance: variance <= 1%  (from Check A's ≤1% rule)
  --   mismatch:         variance > 1%
  assumption_actions_json JSONB,
  -- Shape: [{
  --   "assumption_index": 0,
  --   "action": "acknowledged" | "signed_off" | "rejected",
  --   "user_id": <uuid>,
  --   "created_at": <timestamp>
  -- }]
  -- Only PATTERN and INFERRED assumptions need actions.
  -- EXPLICIT assumptions require no sign-off.
  passed BOOLEAN NOT NULL,
  verified_at TIMESTAMP
);
```

---

### 3.5 Rendering Service (`/services/render`)

**Responsibility:** Generate PPTX + HTML outputs with audit trail

**Input:** selected_narrative, reconciliation_report, user_edits

**Process:**
```
1. PPTX Generation (using python-pptx library)
   Slide structure:
   - Slide 1: Title (Company, Deck Title, Date, Data Source)
   - Slide 2: Executive Summary (1-2 sentence narrative)
   - Slide N: Data visualization (chart + data table)
   - Slide N+1: Assumptions + Inference Flags
   - Slide N+2: Q&A (Questions asked + Answers given)
   - Slide Final: Appendix (Data Quality Notes, Reconciliation Status)
   
   Per slide:
   - Embed metadata: {narrative_confidence, assumptions_count}
   - Add footnotes: "Based on Q1-Q3 data; Q4 forecasted"
   - Clickable numbers: Hyperlink to reconciliation trace (in HTML version)

2. HTML Generation (React component)
   Page structure:
   - Header: Deck metadata, download PPTX button
   - Section: Narrative with highlighted assumptions
   - Section: Visualizations (interactive, Plotly)
   - Section: Figure Traces
     * Table of all numbers in deck
     * Click number → show source rows, formula, confidence
   - Sidebar: Q&A History
   - Sidebar: Edit Log (who changed what when)
   - Footer: Verification timestamp, "Verified by [system]"
   
   Interactive features:
   - Hover over assumption flag → tooltip with explanation
   - Click figure → overlay showing source data
   - Timeline: Show how deck changed (v1 → v2)

3. Audit Log Generation
   Log entry format:
   {
     timestamp,
     user_id,
     action: 'narrative_generated' | 'figure_verified' | 'pdf_rendered',
     narrative_id,
     deck_version,
     details: {...}
   }
   Store in PostgreSQL + Elasticsearch index

4. Output Files
   - PPTX: binary, stored in S3, signed download URL (expires 7 days)
   - HTML: stored in PostgreSQL or S3, served directly
   - Audit log: PostgreSQL (queryable)
```

**Decision: Why both PPTX + HTML?**
- **PPTX:** Executives use this for board meetings (not auditable)
- **HTML:** Data team uses this for verification + compliance (fully auditable)
- Both represent same narrative; HTML is "source of truth" for compliance

**Technology:**
- `python-pptx`: PPTX generation (no external tools)
- `plotly`: Interactive charts → HTML
- React: Front-end HTML rendering

**Data Model:**
```sql
CREATE TABLE deck_outputs (
  id UUID PRIMARY KEY,
  deck_id UUID,
  version INT, -- v1, v2, v3 if re-generated
  pptx_url TEXT (S3),
  html_content TEXT,
  audit_log_id UUID,
  rendered_at TIMESTAMP,
  created_at TIMESTAMP
);
```

---

### 3.6 Adaptation Service (`/services/adapt`)

**Responsibility:** Re-answer questions, regenerate narratives, maintain versioning

**Input:** user_re_answers_question, selected_question_id

**Process:**
```
1. Question Update
   - User goes back, changes answer to Question 2
   - New answer parsed (same rule-based parser)
   - Store: new row in question_sessions OR update existing
   - Mark: "v2 of question session"

2. Cascade Regeneration
   - New questions → new story angles detected
   - Re-run Narrative Generation (with new angles)
   - Show user new 2-3 options vs. old options (diff view)
   
3. Versioning
   Version tree example:
   Deck v1 (Initial)
     └─ Narrative A selected (cost focus)
   
   Deck v2 (User re-answers "primary focus")
     └─ Narrative C selected (growth focus)
   
   Deck v3 (User re-answers "audience")
     └─ Narrative A updated (more formal tone)
   
   Each version is independently verifiable + renderable

4. What-If Scenarios (V1+)
   User creates rule: "IF revenue_growth > 10% THEN emphasize_growth=true"
   System stores: {condition, action}
   On re-render: Re-evaluate rule, swap narrative if condition met

5. Audit Trail
   All re-answers logged: {user, timestamp, old_answer, new_answer}
   Immutable: Can't delete history, only add new version
```

**Decision: Why full re-answer capability?**
- Market changes → user needs to regenerate with new assumptions
- Without this, system feels rigid (users abandon for PowerPoint)
- Versioning ensures compliance (can prove what was decided when)

**Data Model:**
```sql
CREATE TABLE deck_versions (
  id UUID PRIMARY KEY,
  deck_id UUID,
  version INT,
  narrative_id UUID,
  question_session_id UUID,
  parent_version_id UUID, -- for version tree
  created_at TIMESTAMP
);
```

---

## 4. Database Schema (Complete)

```sql
-- Core tables

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  name TEXT,
  organization TEXT,
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE decks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);

CREATE TABLE ingest_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deck_id UUID REFERENCES decks NOT NULL,
  file_url TEXT,
  schema_json JSONB, -- {col_name: {type, nullability, cardinality}}
  quality_report JSONB, -- {issues, status}
  validated_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE question_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deck_id UUID REFERENCES decks NOT NULL,
  version INT DEFAULT 1,
  questions_json JSONB, -- [{id, template, context}]
  answers_json JSONB, -- [{question_id, raw_answer, parsed_intent, confidence}]
  parent_session_id UUID REFERENCES question_sessions,
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE narratives (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deck_id UUID REFERENCES decks NOT NULL,
  question_session_id UUID REFERENCES question_sessions NOT NULL,
  option_number INT, -- 1, 2, 3 (narrative options)
  story_angle VARCHAR(50),
  narrative_text TEXT NOT NULL,
  viz_recommendation TEXT,
  assumptions_json JSONB, -- [{assumption, flag_type, confidence}]
  overall_confidence FLOAT,
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE deck_selections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deck_id UUID REFERENCES decks NOT NULL,
  selected_narrative_id UUID REFERENCES narratives NOT NULL,
  user_edits_text TEXT, -- if user edited narrative
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE reconciliation_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deck_id UUID REFERENCES decks NOT NULL,
  narrative_id UUID REFERENCES narratives NOT NULL,
  parent_report_id UUID REFERENCES reconciliation_reports, -- non-null on re-verify after fix
  checks_json JSONB, -- per check: {status, expected, actual, fix_suggestion, dismissed_*}
  figure_traces JSONB, -- per figure: {figure_value, source_rows, formula, match_status, variance_pct}
  assumption_actions_json JSONB, -- [{assumption_index, action, user_id, created_at}]
  passed BOOLEAN NOT NULL,
  verified_at TIMESTAMP DEFAULT now()
);

CREATE TABLE deck_outputs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deck_id UUID REFERENCES decks NOT NULL,
  version INT,
  pptx_url TEXT,
  html_content TEXT,
  rendered_at TIMESTAMP DEFAULT now()
);

CREATE TABLE audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deck_id UUID REFERENCES decks NOT NULL,
  user_id UUID REFERENCES users NOT NULL,
  action VARCHAR(100),
  details JSONB,
  created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_decks_user ON decks(user_id);
CREATE INDEX idx_audit_log_deck ON audit_log(deck_id);
CREATE INDEX idx_audit_log_user ON audit_log(user_id);
```

---

## 5. API Design (REST)

```
POST /api/v1/decks
  Create new deck project
  
POST /api/v1/decks/{deck_id}/ingest
  Upload + validate data
  Returns: ingest_job_id, schema, quality_report
  
POST /api/v1/decks/{deck_id}/validate-acknowledge
  User acknowledges data quality issues
  Returns: ready to proceed
  
GET /api/v1/decks/{deck_id}/questions
  Get 4-5 questions based on data
  Returns: {questions: [{id, template, context}]}
  
POST /api/v1/decks/{deck_id}/answer-questions
  Submit free-text answers
  Payload: {answers: [{question_id, text}]}
  Returns: {parsed: [{question_id, intent, confidence}], ready_to_generate: bool}
  
GET /api/v1/decks/{deck_id}/narratives
  Get 2-3 narrative options
  Returns: {narratives: [{id, angle, text, viz, confidence, assumptions}]}
  
POST /api/v1/decks/{deck_id}/select-narrative
  User picks primary narrative
  Payload: {narrative_id, edits: optional_text}
  Returns: verification_report

POST /api/v1/decks/{deck_id}/verify/apply-fix
  Apply a suggested fix and re-run verification
  Payload: {report_id, check_name, fix_type: "exclude_rows"|"recalculate", parameters: {row_ids: [...]}}
  Returns: new reconciliation_report (with parent_report_id set to original)
  Flow: apply data filter → re-extract figures → re-run all checks → return updated report
  
POST /api/v1/decks/{deck_id}/verify/dismiss-check
  Dismiss a failed check with reason (audit-logged)
  Payload: {report_id, check_name, reason: "text"}
  Returns: updated reconciliation_report (check status → "dismissed")

POST /api/v1/decks/{deck_id}/verify/assumption-action
  Sign off, acknowledge, or reject an assumption
  Payload: {report_id, assumption_index, action: "acknowledged"|"signed_off"|"rejected"}
  Returns: updated reconciliation_report

POST /api/v1/decks/{deck_id}/render
  Generate PPTX + HTML
  Returns: {pptx_url, html_url, status}
  
POST /api/v1/decks/{deck_id}/re-answer
  User re-answers question (versioning)
  Payload: {question_id, new_answer}
  Returns: updated_narratives (v2 options)
  
GET /api/v1/decks/{deck_id}/versions
  Get version tree + history
  Returns: {versions: [{version, narrative, timestamp, diff}]}
  
GET /api/v1/audit-log
  Query audit trail
  Query params: deck_id, action, date_range
  Returns: {logs: [...]}
```

---

## 6. Security & Compliance

### 6.1 Data Security

| **Layer** | **Decision** | **Reasoning** |
|---|---|---|
| **Encryption in transit** | TLS 1.3 for all APIs | Financial data must be encrypted |
| **Encryption at rest** | S3 + RDS encryption (AES-256) | Compliance: HIPAA, SOC 2 |
| **Source data retention** | Delete after 30 days (S3 lifecycle) | Minimize data liability |
| **Audit immutability** | PostgreSQL triggers prevent DELETE | Can't cover tracks |
| **API authentication** | OAuth 2.0 (Google/Microsoft) + JWT | Enterprise SSO support |

### 6.2 Audit & Compliance

| **Requirement** | **Implementation** |
|---|---|
| **Figure traceability** | Every number links to source rows (URL-based trace) |
| **Decision logging** | Immutable audit_log table (all Q&As, narrative picks, edits) |
| **User attribution** | Every action tagged with user_id + timestamp |
| **Compliance queries** | Elasticsearch index for fast "show all decks where X happened" |
| **Data residency** | S3 + RDS in user's selected region (AWS multi-region support) |

---

## 7. Scalability & Performance

### 7.1 Performance Targets

| **Operation** | **Target** | **Achieved By** |
|---|---|---|
| Data validation | < 5 sec for 100k rows | Pandas native C code + streaming read |
| Question generation | < 500 ms | Pre-computed templates (no ML inference) |
| Narrative generation | < 2 sec (w/ LLM) | LLM call batched, 50-token limit |
| Reconciliation | < 1 sec | Query on indexed numeric columns |
| PPTX rendering | < 1 sec | python-pptx (no external tool calls) |
| **Total user wait time** | < 15 min | Async job processing (user doesn't wait) |

### 7.2 Scalability Strategy

**MVP (Month 1-3): 1000 decks/month**
- Single Python FastAPI instance (vertically scaled)
- PostgreSQL (standard tier)
- Redis single-node cache
- S3 regional bucket

**V1 (Month 3-6): 10k decks/month**
- FastAPI auto-scaling (2-5 workers)
- PostgreSQL replica for read scaling
- Redis cluster (for sessions)
- S3 multi-region replication

**V2 (Month 6+): 100k+ decks/month**
- Kubernetes (FastAPI microservices)
- PostgreSQL sharding (by deck_id)
- ElasticSearch cluster (for audit logs)
- S3 cross-region redundancy

**Async Job Queue (for heavy lifting):**
- Celery + RabbitMQ (for narrative generation, PPTX rendering)
- User sees progress: "Generating narrative... (2/3 complete)"
- Job results cached in Redis

---

## 8. Deployment & Infrastructure

### 8.1 Development Environment

```
docker-compose:
  - postgres:15 (local DB)
  - redis:7 (cache)
  - python:3.11 FastAPI (backend)
  - node:18 React (frontend, dev server)
  - minio (S3 mock for testing)
```

### 8.2 Production Environment (AWS)

```
Container Orchestration:
  - ECR: Docker images (backend + workers)
  - ECS: Task scheduling (FastAPI, Celery workers)
  - ALB: Load balancer (health checks, sticky sessions)

Data:
  - RDS PostgreSQL: Multi-AZ (automated failover)
  - ElastiCache Redis: Multi-AZ cluster
  - S3: Versioned buckets with lifecycle policies

Observability:
  - CloudWatch: Logs, metrics (request latency, error rates)
  - X-Ray: Distributed tracing (per-request debug)
  - Sentry: Error tracking (catches exceptions)

Networking:
  - VPC: Isolated environment
  - NAT Gateway: Outbound internet access (S3, LLM API)
  - Security Groups: Whitelist only necessary ports
```

---

## 9. Major Architectural Decisions Table

| **Decision** | **Alternative** | **Why We Chose This** |
|---|---|---|
| **Python + FastAPI** | Node.js | Data science libraries + LLM integration native |
| **PostgreSQL** | MongoDB | ACID guarantees for audit trail |
| **Rule-based parsing** | LLM | Deterministic, auditable, cheap, no hallucination |
| **2-3 narratives** | 1 or 10+ | Balances choice vs. decision paralysis |
| **Blocking verification** | Warning-only | Trust is the moat (can't ship wrong numbers) |
| **Template + LLM hybrid** | Full LLM | Constraints prevent hallucination |
| **Dual output (PPTX + HTML)** | PPTX only | Executives use PPTX; compliance uses HTML |
| **Redis cache** | None | Speeds up re-answer flow, reduces DB load |
| **S3 storage** | Database BLOBs | Scalable, cheap, lifecycle management |
| **Async jobs** | Sync processing | Long-running tasks (LLM calls) don't block UI |

---

## 10. Implementation Roadmap

### **Phase 1 (MVP): Weeks 1-4**
- ✅ Ingest Service (CSV/Excel only)
- ✅ Question Engine (template-based, no ML)
- ✅ Narrative Generation (templates + rule-based)
- ✅ Verification Service (4 core checks)
- ✅ PPTX Rendering (basic slides)
- ✅ React UI (question interface + narrative picker)

### **Phase 2 (V1): Weeks 5-8**
- HTML rendering (audit trail + interactive traces)
- Parsing error handling (clarifying follow-ups)
- Question versioning + re-answer capability
- Elasticsearch indexing for audit logs
- LLM integration (GPT-3.5 for narrative polish, 50-token limit)
- Role-based UI (editor vs. viewer modes)

### **Phase 3 (V2): Weeks 9-12**
- SQL database support (PostgreSQL, MySQL ingest)
- S3/Salesforce connectors
- What-if scenarios (simple rules)
- Approval workflows (CFO sign-off)
- Multi-language support (i18n)
- Mobile optimization

---

## 11. Risks & Mitigations

| **Risk** | **Mitigation** |
|---|---|
| **LLM hallucination** | 50-token limit, template structure, confidence flags, user review |
| **Data quality issues** | Pre-validation mandatory, user sign-off before proceeding |
| **Wrong figure** | Reconciliation is blocking; can't render if check fails |
| **Performance at scale** | Async jobs, caching, database indexing, horizontal scaling |
| **Vendor lock-in (AWS)** | Terraform IaC (portable to GCP/Azure); S3 → object storage generic |
| **Regulatory compliance** | Built audit trail from day 1; encryption at rest/transit |

---

## 12. Resolved Data-Model Gaps (UX Spec Alignment)

*Added 2026-06-18. Resolves Gaps 1–5 identified in the Screen 3 (Audit/Verification) UX spec.*

### Gap 1: Assumption Sign-Off Tracking — RESOLVED

**Approach:** New `assumption_actions_json` JSONB column on `reconciliation_reports`.

Each entry records `{assumption_index, action, user_id, created_at}` where action is `acknowledged` (PATTERN flags), `signed_off` (INFERRED flags), or `rejected`.

**Why not a separate table?** For MVP, assumptions are a small list (typically 1–5 per narrative). JSONB on the existing report row avoids a join and keeps all verification state in one place. The `narratives.assumptions_json` array stays immutable — sign-off state lives on the report, not the narrative.

**Breaking changes:** None. New column on `reconciliation_reports`, additive only.

### Gap 2: Check Dismissal Tracking — RESOLVED

**Approach:** Restructured `checks_json` from `{check_a: bool}` to `{check_a: {status, dismissed_reason, dismissed_by, dismissed_at, ...}}`.

Removed the redundant `failures_json` column from the service-level data model — failure details (expected, actual, fix_suggestion) are now inlined per-check in `checks_json`.

**Why inline, not a separate table?** There are exactly 5 checks (A–E). A dismissal is a one-time action per check per report. The data fits naturally as fields on the check object. A separate `check_dismissals` table would add a join for 5 rows.

**Breaking changes:** Shape of `checks_json` changed from `{key: bool}` to `{key: object}`. Since no code exists yet, this is safe. The `failures_json` column in the service-level model was merged into `checks_json`; the complete schema in Section 4 never had `failures_json`, so no conflict.

### Gap 3: Fix-Application Endpoint — RESOLVED

**Approach:** Three new endpoints under `/api/v1/decks/{deck_id}/verify/`:

| Endpoint | Purpose |
|---|---|
| `POST .../apply-fix` | Apply a suggested data fix (e.g., exclude rows), re-run all checks, return a **new** `reconciliation_reports` row with `parent_report_id` pointing to the original. |
| `POST .../dismiss-check` | Record a check dismissal with required reason text. Updates the existing report's `checks_json` in place. |
| `POST .../assumption-action` | Record a sign-off/acknowledge/reject action. Appends to `assumption_actions_json`. |

**Re-verify flow:** `apply-fix` creates a new report row (preserving the original for audit). The new row re-runs figure extraction on the filtered data, then runs all 5 checks against the new figures. The gate status on Screen 3 reads from the latest report for the narrative.

**Breaking changes:** New `parent_report_id` column on `reconciliation_reports` (nullable FK to self). Additive only.

### Gap 4: Per-Figure Match Status — RESOLVED

**Approach:** Each entry in `figure_traces` JSONB now includes `match_status` and `variance_pct`.

**Tolerance thresholds (hard-coded for MVP):**

| match_status | Condition | UI treatment |
|---|---|---|
| `exact` | variance = 0% | ✓ green |
| `within_tolerance` | 0% < variance ≤ 1% | ✓ green (matches Check A's ≤1% rule) |
| `mismatch` | variance > 1% | ✗ red, requires fix or dismissal |

The 1% threshold comes directly from the existing Check A definition ("≤ 1% variance accounting for rounding"). No new configuration surface — the threshold is a constant in the Verify Service.

**Breaking changes:** Shape of `figure_traces` entries extended. Additive — new fields alongside existing ones.

### Gap 5: Assumption Challenge → Narrative Edit Round-Trip — RESOLVED

**Approach:** UI-layer navigation only. No new data model.

**Flow when user rejects/challenges an assumption on Screen 3:**
1. User clicks [Reject] or [Challenge] on an assumption.
2. Action recorded in `assumption_actions_json` (action: `rejected`).
3. UI navigates to Screen 2 with query param `?highlight=assumption-{index}`.
4. Screen 2 opens the detail panel with the narrative text editable, cursor near the relevant passage.
5. User edits the text manually. Edit saved to `deck_selections.user_edits_text` (existing field).
6. User clicks [Verify & Proceed →] to return to Screen 3.
7. Verify Service re-runs on the edited narrative text — creates a new `reconciliation_reports` row.

**Why manual edit, not regeneration?** For MVP, assumption challenges are rare (most assumptions are acknowledged). Full regeneration would require the Narrative Service to accept "regenerate but without assumption X" as input, which adds complexity for a low-frequency path. Manual editing is sufficient — the user knows what they want to say. Regeneration can be added in V1 if usage data shows frequent challenges.

**Breaking changes:** None. Uses existing `deck_selections.user_edits_text` and existing re-verify flow.

---

## Conclusion

This architecture is:
- **Trust-first:** Reconciliation blocking, not optional
- **Auditability-first:** Every action logged, immutable trail
- **User-centric:** 4-5 questions → 2-3 narratives → user curates
- **Scalable:** Async jobs, caching, database indexing
- **MVP-focused:** Core 6 features only; nice-to-haves in V1+

**Ready for:** Backend development, database design, frontend UX sprint.
