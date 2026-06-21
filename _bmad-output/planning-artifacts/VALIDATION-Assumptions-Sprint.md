# Assumptions Validation Sprint: Automated Deck Generation System

**Duration:** 2-4 weeks (parallel with architecture refinement)  
**Goal:** Validate core job-to-be-done, feature prioritization, and technical feasibility before committing to MVP build

---

## Critical Assumptions to Validate

### **Tier 1: Product-Market Fit (Kill-or-Win)**

**Assumption 1.1: Users Will Adopt This Over Existing Workflows**
- **Statement:** CFOs/finance teams will replace Tableau + PowerPoint with a new tool that requires answering 4-5 questions + waiting for verification.
- **Risk if wrong:** Product ships, no adoption. Entire business premise collapses.
- **How to validate:**
  - **User interviews (5-10 users):** Finance directors, controllers, analysts at F500 / mid-market
  - **Question script:**
    - "Today, how do you create board presentation decks?"
    - "How long does it take from data to deck?"
    - "What frustrates you most about the current process?"
    - "Would you use a tool that takes 15 min and verifies every number?"
    - **Critical:** "Would you try this instead of [current tool]? Why or why not?"
  - **Success criteria:** >60% say "yes, I'd try it" (not "yes, I'd buy it" — just try)
  - **Red flag:** >50% say "our Tableau dashboards already do this" or "our analysts handle this"

**Assumption 1.2: The Job is "Speed + Trust," Not Just "Speed"**
- **Statement:** Users care equally about reconciliation/verification as they do about time-to-deck
- **Risk if wrong:** We over-engineer verification; competitors ship faster, simpler products and win market share
- **How to validate:**
  - **Interview question:** "If I gave you a deck in 5 minutes, but without number verification, vs. 15 minutes with verification—which would you choose?"
  - **Probe:** "How often do wrong numbers appear in your current decks? How big a deal is that?"
  - **Success criteria:** >70% choose verified deck even if slower
  - **Red flag:** Users don't care about verification; they just want speed

**Assumption 1.3: The User is an Analyst, Not a CFO**
- **Statement:** Daily users are finance/data analysts building decks *for* CFOs; CFOs are final reviewers, not daily users
- **Risk if wrong:** We design for analyst speed; CFO adoption fails (they never see the tool)
- **How to validate:**
  - **Interview two cohorts separately:**
    - **Analysts:** "How often do you build decks? How hands-on are you?"
    - **CFOs:** "Do you build decks yourself, or does your team?"
  - **Success criteria:** Analysts say "I'd use this daily"; CFOs say "I'd review the output"
  - **Red flag:** CFOs build their own decks (they won't outsource to your tool) or analysts say "this is too slow; we just use templates"

---

### **Tier 2: Core Feature Validation (Fix-or-Rebuild)**

**Assumption 2.1: Free-Text Question Parsing Works (>90% accuracy)**
- **Statement:** Rule-based parsing can extract user intent from free-text answers with >90% first-pass accuracy
- **Risk if wrong:** Users re-answer questions 3x; system seems broken; adoption fails
- **How to validate:**
  - **Wizard of Oz test (not building real parser yet):**
    1. Manually create 3-5 question templates (primary metric, audience, comparison context, anomaly context, assumptions)
    2. Have 5 users answer in free text (real interface mockup)
    3. Manually parse their answers (rule-based, like you specified)
    4. Ask: "Did the system understand you?" (show back the parsed intent)
    5. Measure: % of first-pass interpretations users agree with
  - **Example:**
    - User answers: "Cost control is the main thing, but we also care about growth"
    - Manual parse: Primary = COST_CONTROL (confidence 0.9), Secondary = GROWTH (0.7)
    - Ask user: "Is that right?" → Yes/No
  - **Success criteria:** >90% first-pass accept rate
  - **Red flag:** <70% accept rate (parsing is unreliable; needs ML or simpler questions)

**Assumption 2.2: 2-3 Auto-Generated Narratives Are Better Than 1**
- **Statement:** Users prefer curating from 2-3 options over a single "recommended" narrative
- **Risk if wrong:** We add complexity (multi-narrative), but users just pick the first one anyway (no benefit)
- **How to validate:**
  - **Prototype test (manually generate, don't use LLM yet):**
    1. Take a real financial dataset (5 users)
    2. Manually write 3 different narratives (e.g., "Risk Focus," "Growth Focus," "Efficiency Focus")
    3. Show all 3 to user + ask: "Which would you use? Do you need the others?"
    4. Measure: % who pick same narrative vs. different ones; % who say "one is enough"
  - **Success criteria:** >60% say "I'd use different narratives for different audiences" OR "The option I didn't pick was close but wrong"
  - **Red flag:** >70% always pick the same narrative (no real choice happening)

**Assumption 2.3: Mandatory Reconciliation Doesn't Create Unacceptable Latency**
- **Statement:** Verification queries run in <30 seconds, keeping 15-min target intact
- **Risk if wrong:** Verification is slow; users wait; they abandon or bypass it
- **How to validate:**
  - **Technical test (build reconciliation locally):**
    1. Create test dataset: 100k rows (realistic financial data)
    2. Implement 5 reconciliation checks (sum-of-parts, consistency, continuity, comparison, statistical significance)
    3. Time execution: How long for all 5 checks?
  - **Success criteria:** <30 seconds for all checks on 100k rows
  - **Red flag:** >1 minute means verification is bottleneck; need optimization strategy

**Assumption 2.4: Dual Output (PPTX + HTML) is Necessary for MVP**
- **Statement:** We need both PPTX (for boardroom) AND HTML (for audit trail) in MVP
- **Risk if wrong:** Building both doubles rendering complexity; we could ship faster with just PPTX
- **How to validate:**
  - **Interview question:** "How do you share board decks? (PPTX? Email? Dashboard?)"
  - **Follow-up:** "If the deck was HTML-only (browser), would you use it?"
  - **Compliance question:** "Do you need an audit trail of what changed in the deck?"
  - **Success criteria:** >50% say "PPTX is mandatory"; >30% say "audit trail matters"
  - **Red flag:** "PPTX is all we need" (HTML is nice-to-have, not MVP)

**Assumption 2.5: Question Re-Answer + Versioning is Important**
- **Statement:** Users will regenerate narratives multiple times (what-if scenarios, assumption changes)
- **Risk if wrong:** We build versioning; users never use it; wasted engineering
- **How to validate:**
  - **Interview question:** "After you create a board deck, how often do you change the assumptions or re-run with different data?"
  - **Follow-up:** "What triggers a regeneration? (New data? Different audience? Board feedback?)"
  - **Success criteria:** >40% say "multiple times per month"
  - **Red flag:** "We generate once and ship it" (re-answer is V2 feature, not MVP)

---

### **Tier 3: Technical Feasibility (Build-or-Redesign)**

**Assumption 3.1: LLM-Based Narrative Generation (50-token limit) Produces Acceptable Quality**
- **Statement:** GPT-3.5 turbo constrained to 50 tokens can produce useful narrative snippets (not hallucinate)
- **Risk if wrong:** Narratives are gibberish or obviously wrong; users don't trust them
- **How to validate:**
  - **Technical spike (Week 1-2):**
    1. Take 3 real financial datasets
    2. Write prompt: "Generate a one-sentence executive summary of [narrative angle]. Do not speculate. Base only on data provided."
    3. Feed data + prompt to GPT-3.5 turbo
    4. Review outputs: Are they factual? Do they match the data?
  - **Success criteria:** >80% of outputs are factually accurate, not speculative
  - **Red flag:** >30% outputs are hallucinated or wrong (need different approach)

**Assumption 3.2: Story Angle Detection Works on Messy Real Data**
- **Statement:** Algorithm can detect trend/disruption/composition/anomaly/comparison on 80% of datasets
- **Risk if wrong:** System generates narratives with low confidence (<60%); users see uncertainty; lose trust
- **How to validate:**
  - **Technical spike (Week 1-2):**
    1. Get 10 real financial datasets (ask beta users for historical data)
    2. Run story angle detection on each
    3. Measure: % where algorithm confidently identifies ≥1 angle
    4. For each angle, measure: Does the narrative make sense?
  - **Success criteria:** >80% of datasets have ≥1 high-confidence angle (>70% confidence)
  - **Red flag:** <60% have high-confidence angles (algorithm isn't robust enough)

**Assumption 3.3: Rule-Based Parsing Can Scale to 50+ Intent Categories**
- **Statement:** Rule-based keyword matching + confidence scoring is maintainable long-term
- **Risk if wrong:** By Month 3, parser is unmaintainable; too many branching rules; need ML
- **How to validate:**
  - **Code spike (Week 1):**
    1. Build the parsing rule engine (as specified in architecture)
    2. Add 15-20 intent categories
    3. Test on 50 real free-text user answers
    4. Measure: Code complexity, maintainability, test coverage
  - **Success criteria:** <200 lines of parsing code; >80% test coverage; easy to add new categories
  - **Red flag:** >400 lines of nested if/else (time to refactor to ML)

---

## Validation Sprint Schedule

### **Week 1: User Research**

**Monday-Wednesday: User Interviews**
- **Target:** 5-10 users (finance directors, controllers, senior analysts at F500 / mid-market / high-growth)
- **Duration:** 30 min each (4-5 interviews/day)
- **Method:** Zoom + screen share (show mockups of question interface, narrative options)
- **Questions:** (See below)
- **Deliverable:** Interview notes + synthesis (common themes, red flags)

**Thursday-Friday: Competitive Deep Dive**
- **Research:** How do users currently solve this? (Tableau, Beautiful.ai, PowerPoint templates, custom tools?)
- **Interview:** Ask 2-3 users: "Have you tried [competitor]? Why did/didn't you use it?"
- **Deliverable:** Competitive positioning notes

**Success Criteria for Week 1:**
- ✅ 5+ interviews completed
- ✅ >60% say "I'd try this tool"
- ✅ Clear picture of current workflow + pain points

---

### **Week 2: Prototype Validation**

**Monday-Tuesday: Wizard of Oz Question Engine**
- **Build:** Question interface mockup (Figma or low-code tool like Bubble)
- **Test:** Have 5 users answer 4-5 questions in free text
- **Manual parse:** You manually parse their answers (rule-based)
- **Feedback:** Ask users: "Did the system understand you?"
- **Deliverable:** Parsing accuracy report (<90% acceptance = problem)

**Wednesday-Thursday: Narrative Prototype**
- **Manual generation:** Write 3 different narratives for 2-3 real financial scenarios
- **User test:** Show 5 users all 3 options + ask which they'd use
- **Deliverable:** User feedback on narrative quality + multi-option preference

**Friday: Technical Spikes**
- **LLM test:** Run GPT-3.5 narrative generation on 3 datasets (check for hallucination)
- **Story angle detection:** Test algorithm on 10 real datasets (measure confidence scores)
- **Deliverable:** Technical risk assessment

**Success Criteria for Week 2:**
- ✅ Question parsing >90% accuracy
- ✅ Users prefer 2-3 narratives over 1
- ✅ LLM outputs are factually accurate
- ✅ Story angle detection works on >80% of datasets

---

### **Week 3-4: Validation Synthesis + Go/No-Go Decision**

**Monday-Tuesday: Consolidate Findings**
- **Analyze:** All user interviews, prototype feedback, technical results
- **Identify:** Biggest risks + biggest opportunities
- **Update:** PRD + architecture based on validated assumptions
- **Deliverable:** Updated assumption list + prioritized feature list

**Wednesday: Go/No-Go Review**
- **Decision gates:**
  - ✅ >60% users would try this? → GO
  - ✅ >70% care about verification? → GO
  - ✅ Question parsing >90% accurate? → GO
  - ✅ Narratives don't hallucinate? → GO
  - ❌ Any major gate fails? → Pivot or extend validation

**Thursday-Friday: Plan Next Phase**
- **If GO:** Create detailed implementation spec for MVP (Weeks 5-10)
- **If PIVOT:** Adjust architecture + restart validation on updated assumptions

---

## Interview Script (Detailed)

### **Part 1: Current State (10 min)**

1. **Role & Workflow:**
   - "What's your role? How often do you build presentations/reports?"
   - "Walk me through the last deck you created. End-to-end, how long did it take?"
   - "What tools do you use? (Tableau, Excel, PowerPoint, BI tool, custom?)"

2. **Pain Points:**
   - "What's the most frustrating part of creating decks?"
   - "How often do numbers in your decks turn out to be wrong? What happens then?"
   - "Who verifies the numbers before you present? How long does that take?"

3. **Audience & Format:**
   - "Who sees these decks? (CFO, board, investors, internal ops?)"
   - "What format do they want? (PowerPoint slides, Excel dashboard, printed PDF?)"
   - "How much do they care about the narrative/story vs. raw data?"

---

### **Part 2: Product Concept (10 min)**

**Show mockup/prototype:**
- Upload CSV
- Answer 4-5 questions ("What's your primary focus?" "Who's the audience?")
- System generates 2-3 narratives (show examples)
- System verifies every number
- Output: PPTX deck + HTML audit trail

4. **Reaction:**
   - "What's your first reaction to this workflow?"
   - "Would you use this instead of [current tool]? Why / why not?"
   - "What would you change?"

5. **Speed vs. Trust Trade-off:**
   - "If I gave you a deck in 5 minutes without verification, vs. 15 minutes with verification, which would you pick?"
   - "How important is the verification/audit trail to your organization?"

6. **Adoption:**
   - "If we built this, would you be willing to pilot it?"
   - "What would have to be true for your organization to switch?"

---

### **Part 3: Alternatives (5 min)**

7. **Why not Tableau / Beautiful.ai / [competitor]?**
   - "Have you used [tool]? Why did/didn't you stick with it?"
   - "What does [tool] do well? What's missing?"

8. **User Role:**
   - "Do you build decks yourself, or does someone build them for you?"
   - "(If themselves) Would your team love a tool to make it faster?"
   - "(If others build) Would your analysts love a tool to make it faster?"

---

## Success / Failure Criteria

### **Go to MVP Build (All Green)**
- ✅ >60% users say "I'd try this"
- ✅ >70% care about verification (not just speed)
- ✅ Question parsing >90% accurate on real answers
- ✅ Narratives don't hallucinate (>80% factually accurate)
- ✅ Story angle detection works on >80% of datasets
- ✅ <30 sec reconciliation latency on 100k-row dataset
- ✅ No major competitive threats identified

### **Pivot or Extend Validation (Red Flags)**
- ❌ <40% would try this → Job-to-be-done unclear; re-interview
- ❌ <50% care about verification → Over-engineering; simplify
- ❌ Question parsing <70% accuracy → Rules too brittle; consider ML or simpler UI
- ❌ LLM narratives hallucinate >20% → Need different approach (templates only, human review)
- ❌ Story angle detection <60% confidence → Algorithm weak; add data scientist or use different method
- ❌ Reconciliation >1 min → Performance bottleneck; optimize or defer to V1

---

## Resource Plan

| **Role** | **Time Commitment** | **Deliverable** |
|---|---|---|
| **Product Manager (you)** | 40 hrs/week (full-time for 2-4 weeks) | Interview synthesis, go/no-go decision |
| **Engineer** | 20 hrs/week | Technical spikes (LLM, story angle, reconciliation latency) |
| **Designer** | 10 hrs/week | Question interface mockup, narrative examples |
| **Optional: Beta users** | 5-10 hrs each | Interviews + prototype testing |

---

## Deliverables

1. **Interview Notes** — Synthesis of 5-10 user conversations (pain points, job-to-be-done clarity)
2. **Parsing Accuracy Report** — % of questions parsed correctly on first attempt
3. **Narrative Quality Assessment** — User preferences: 1 vs. 2-3 options; factual accuracy of narratives
4. **Technical Risk Report** — LLM hallucination rate, story angle detection confidence, reconciliation latency
5. **Updated PRD** — Based on validated assumptions; re-prioritized features
6. **Go/No-Go Recommendation** — Proceed to MVP build, or pivot assumptions

---

## Timeline

**Aggressive:** 2 weeks (parallel execution, dedicated team)  
**Standard:** 3-4 weeks (part-time, coordinated with architecture refinement)  
**Conservative:** 4+ weeks (methodical, interview every potential segment)

**Recommendation:** **Standard (3 weeks).** Run Week 1 (user research) + Week 2 (prototypes) in parallel with architecture review. Use Week 3 to synthesize + make go/no-go decision.

---

## Next Step

**This week:** 
1. Identify 5-10 target users (ask your network, warm intros)
2. Schedule interviews (aim for Monday-Wednesday of Week 1)
3. Create mockup of question interface (Figma / Bubble / PowerPoint slides)
4. Prepare interview script (use above)

**Then:** Run the sprint, collect data, and let the market tell you if this is the right bet.

---

**Ready to start recruiting? Or do you want to refine the validation plan first?**
