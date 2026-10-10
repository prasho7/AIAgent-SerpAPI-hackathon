# 📡 ScoutAI

## Live Research & Decision Agent

> **Ask. Search. Verify. Decide.**

ScoutAI is a multi-mode AI decision agent that combines **Gemini reasoning** with **SerpApi live search** to answer questions where current, verifiable information matters.

It can:

- 🔎 **Research** current topics and technical questions
- 📍 **Discover** relevant local places
- 🛒 **Compare** products within a budget
- 💬 **Follow up** using the evidence from the current research run

The key idea is simple:

> **LLMs are good at reasoning. Search engines are good at finding live information. ScoutAI builds the reliability layer between them.**

---

# ⚡ Judge Snapshot

| | ScoutAI |
|---|---|
| **What** | Evidence-grounded AI decision agent |
| **AI** | Gemini |
| **Live data** | SerpApi |
| **Modes** | Research · Local · Shopping |
| **UI** | Streamlit |
| **Core strength** | Controlled retrieval + evidence-grounded answers |
| **Trust layer** | Validation · citations · freshness protection · safe failure |

### The 10-second architecture

```text
USER
  ↓
GEMINI → understands intent + creates a structured plan
  ↓
SERPAPI → retrieves live Web / Maps / Shopping evidence
  ↓
PYTHON → validates, normalizes, deduplicates, limits
  ↓
GEMINI → writes from the curated evidence
  ↓
VALIDATOR → checks citation references
  ↓
USER → answer + source cards + limitations
```

---

# 🎯 The Problem

A normal AI assistant can sound convincing even when the underlying information is:

- outdated,
- unsupported,
- incomplete,
- taken from the wrong source type,
- or stale when the user asks a current follow-up.

Traditional search has the opposite problem:

> **Lots of information. Too much manual work.**

ScoutAI targets the gap between the two:

> **Turn live search results into a decision the user can inspect and verify.**

---

# 💡 The Solution

ScoutAI does not simply ask an LLM a question and attach a few links.

It runs a controlled workflow:

```text
Question
   ↓
Understand intent + criteria
   ↓
Create structured plan
   ↓
Validate the plan
   ↓
Call the correct SerpApi engine
   ↓
Curate the returned evidence
   ↓
Generate an answer from that evidence
   ↓
Validate citations
   ↓
Show answer + sources
```

When the evidence is not sufficient, ScoutAI does **not** fill the gap with a confident guess.

```text
Not verified from retrieved sources.
```

That behavior is intentional.

---

# 🧭 Three Decision Modes

| Mode | User need | SerpApi |
|---|---|---|
| 🔎 **Research** | Current research, comparisons, technical questions | Google Web Search |
| 📍 **Local Discovery** | Nearby cafés, restaurants, coworking spaces, services, etc. | Google Maps |
| 🛒 **Smart Shopping** | Product discovery + budget-based comparison | Google Shopping |

## 🔎 Research Mode

**Example**

```text
Compare Streamlit and FastAPI for a beginner building an AI agent.
```

**Flow**

```text
Question
  ↓
Gemini → focused research queries
  ↓
SerpApi → live web results
  ↓
Python → clean + deduplicate + assign [S#]
  ↓
Gemini → evidence-grounded brief
  ↓
Citation validation
```

## 📍 Local Discovery Mode

**Example**

```text
Find good study cafés near Koramangala under ₹500.
```

**Flow**

```text
Question
  ↓
Gemini → local intent + criteria
  ↓
Python → validate location
  ↓
SerpApi → Google Maps results
  ↓
Python → normalize places + assign [P#]
  ↓
Gemini → grounded recommendation
  ↓
Maps / Website links
```

ScoutAI keeps **Maps links** and **business website links** separate.

## 🛒 Smart Shopping Mode

**Example**

```text
Find a laptop under ₹60,000 for coding.
```

**Flow**

```text
Question
  ↓
Gemini → product + budget + criteria
  ↓
Python → validate required inputs
  ↓
SerpApi → Google Shopping results
  ↓
Python → normalize products + assign [I#]
  ↓
Gemini → evidence-grounded comparison
  ↓
Merchant / listing links
```

---

# 🌐 SerpApi Is the Core Evidence Layer

SerpApi is not a cosmetic integration.

Each major ScoutAI mode depends on it:

| ScoutAI | SerpApi engine | What it provides |
|---|---|---|
| Research | Google Web Search | Current web sources, titles, snippets, URLs |
| Local | Google Maps | Places, addresses, ratings, reviews, Maps links |
| Shopping | Google Shopping | Product listings, prices, merchants, ratings, reviews |

### Role separation

```text
SERPAPI
Finds live external evidence
        ↓
PYTHON
Validates + processes evidence
        ↓
GEMINI
Reasons over that evidence
        ↓
SCOUTAI
Presents a traceable decision
```

Without SerpApi, the live-evidence layer behind ScoutAI's main workflows disappears.

---

# 🧠 What Makes ScoutAI Different?

A search API call is easy.

The difficult part is making an AI agent behave reliably **around** that search.

### Core engineering decisions

| Capability | What ScoutAI does |
|---|---|
| **Multi-tool routing** | Chooses Web, Maps, or Shopping based on the request |
| **Structured planning** | Gemini produces constrained plans instead of free-form tool instructions |
| **Schema validation** | Pydantic validates plans, locations, budgets, limits, and evidence objects |
| **Tool-call gates** | Blocks Maps requests without a usable location and Shopping requests without required product/budget data |
| **Evidence-first generation** | Gemini writes from curated SerpApi evidence rather than freely inventing facts |
| **Hard evidence gate** | No usable evidence → no unsupported factual answer |
| **Typed evidence** | Web, Place, and Product results use separate models |
| **Normalization + deduplication** | Cleans raw results and removes duplicates before synthesis |
| **Citation namespaces** | `[S#]` Research · `[P#]` Local · `[I#]` Shopping |
| **Deterministic citation validation** | Python verifies that cited IDs actually exist in the current evidence set |
| **Freshness protection** | Blocks stale evidence from being presented as “latest”, “open now”, “in stock”, etc. |
| **Bounded follow-ups** | Follow-ups reuse a controlled evidence set instead of silently expanding retrieval |
| **Quota-aware design** | Limits queries, results, retries, and automatic retrieval |
| **Graceful failures** | Shows safe failure states instead of stack traces or made-up answers |
| **Session-state integrity** | Keeps answer, sources, and plan tied to the same run |
| **Mock-first tests** | Tests core behavior without repeatedly consuming live API quota |
| **Separation of concerns** | UI, workflows, services, prompts, schemas, processors, and tests are separated |

---

# ⚖️ Typical AI Search vs ScoutAI

| Typical AI search assistant | ScoutAI |
|---|---|
| One generic search path | 🔀 Three specialised retrieval modes |
| Generic source list | 🧩 Typed Web / Place / Product evidence |
| Uncertainty may be hidden | 🛡️ Explicit evidence boundaries |
| Search added after the answer | 🌐 Live evidence drives the answer |
| Free-form tool use | ✅ Structured plans + validation |
| Old evidence can look current | ⏱️ Freshness-sensitive follow-ups are blocked |
| Source links can be ambiguous | 🔗 Maps, websites, and listings are distinct |
| Failure may become a fluent answer | 🚫 No evidence = no unsupported factual claim |

---

# 🔬 Evidence & Citation Model

ScoutAI gives each evidence item a stable ID.

```text
Research
[S1] [S2] [S3]

Local
[P1] [P2] [P3]

Shopping
[I1] [I2] [I3]
```

The final answer cites these IDs directly next to supported claims.

Python then checks the references.

```text
Claim
  ↓
Citation ID
  ↓
Does this ID exist in current evidence?
  ├── YES → keep
  └── NO  → flag
```

This creates a simple rule:

> **A citation should point to evidence that actually exists in the current research run.**

---

# 🕒 Freshness Safety

One subtle failure mode in AI agents is **stale context pretending to be live information**.

For example:

```text
Original search → product price = ₹59,999

Follow-up:
"What is the latest price?"
```

ScoutAI does not silently reuse the old price and call it current.

Instead, freshness-sensitive follow-ups such as:

```text
What is the latest price?
Is it open right now?
Is it in stock?
Find more options.
```

are treated as requiring fresh retrieval.

That keeps the boundary clear:

> **Old evidence can explain the previous answer. It should not impersonate live evidence.**

---

# 📈 Impact / Use Cases

## 🎓 Students & Developers

```text
Which framework should I learn?
Which API design approach fits my project?
What are current best practices?
```

ScoutAI turns live research into a cited, decision-focused brief.

## 📍 Local Decisions

```text
Where can I study nearby?
Which restaurant fits my criteria?
What coworking spaces are relevant?
```

ScoutAI uses Maps evidence and provides direct navigation links.

## 💰 Budget-Conscious Shopping

```text
Which laptop fits my budget?
Which listing looks most suitable?
Which products are available around my price range?
```

ScoutAI compares current listings and exposes merchant/source links.

## 🔐 Trust-Sensitive Decisions

```text
Why did the AI recommend this?
Which claims are actually supported?
Where did this information come from?
```

ScoutAI exposes the evidence instead of hiding it behind a polished paragraph.

---

# 🏗️ Architecture

```text
┌──────────────────────────────────────────────────────────────────┐
│                           USER / STREAMLIT                       │
│   Question · Result · Follow-up · Sources · Diagnostics         │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                        AGENT CONTROLLER                           │
│        Input validation · Mode routing · Safe result flow        │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                              GEMINI                              │
│     Structured plan · Criteria extraction · Grounded writing     │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                ┌───────────────┼────────────────┐
                ▼               ▼                ▼
       ┌────────────────┐ ┌─────────────┐ ┌──────────────────┐
       │ Research Mode  │ │ Local Mode  │ │ Shopping Mode    │
       │  SerpApi Web   │ │ SerpApi Maps│ │ SerpApi Shopping │
       └───────┬────────┘ └──────┬──────┘ └────────┬─────────┘
               │                 │                  │
               └─────────────────┴──────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                       EVIDENCE PROCESSOR                         │
│       Normalize · Deduplicate · Assign IDs · Curate set         │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                    GROUNDED WRITER + VALIDATOR                   │
│       Gemini writes from evidence · Python checks citations      │
└──────────────────────────────────────────────────────────────────┘
```

---

# 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Language | **Python 3.11+** |
| UI | **Streamlit** |
| AI reasoning | **Google Gemini** via `google-genai` |
| Live Web retrieval | **SerpApi Google Web Search** |
| Local retrieval | **SerpApi Google Maps** |
| Product retrieval | **SerpApi Google Shopping** |
| Validation | **Pydantic** |
| Environment / secrets | **python-dotenv** |
| Testing | **Pytest** |
| Styling | Streamlit + lightweight CSS |

---

# 🧰 Development Tools Used

These tools helped build the project. They are **development aids**, not hidden runtime dependencies.

| Tool | Used for |
|---|---|
| **Perplexity** | Architecture exploration, design thinking, and project structure |
| **Gemma 4 (open source)** | Core knowledge support, understanding query execution, inspecting files, and decoding project behavior step by step |
| **GitHub Copilot** | Coding, file management, UI/design foundation, and project scaffolding |
| **Antigravity** | Coding beyond my existing knowledge, debugging, and error handling |
| **ChatGPT** | Project descriptions, documentation, explanations, and README refinement |

### Runtime stack vs development assistance

```text
DEVELOPMENT
Perplexity + Gemma 4 + Copilot + Antigravity + ChatGPT
                              ↓
                         ScoutAI codebase
                              ↓
RUNTIME
Python + Streamlit + Gemini + SerpApi + Pydantic
```

---

# 🔐 Reliability Rules

ScoutAI follows a compact set of non-negotiable rules:

```text
No usable evidence
        ↓
No unsupported factual answer

Bad / incomplete plan
        ↓
Block the tool call

Missing requested fact
        ↓
State the limitation

Old evidence + current-time question
        ↓
Require fresh retrieval

Invalid citation
        ↓
Flag it

API failure
        ↓
Fail safely
```

---

# ⚠️ Limitations & API Constraints

ScoutAI is intentionally a **bounded MVP**.

### Retrieval limits

| Mode | Current behavior |
|---|---|
| Research | Up to three focused web queries + bounded source selection |
| Local | One validated Maps query + limited place results |
| Shopping | One validated Shopping query + limited product results |
| Follow-ups | Reuse current evidence; no silent live re-search |

Because retrieval is bounded, a result may not contain every detail requested by the user.

When it cannot be verified:

```text
Not verified from retrieved sources.
```

### API limitations

ScoutAI depends on:
- SerpApi quota and successful retrieval,
- Gemini model availability and quota,
- network availability.

The system deliberately limits calls and retries so it can remain predictable and cost-aware.

---

# 🔮 Future Scope

These are planned features, **not currently implemented**.

## 1. Evidence Gap Recovery

```text
Initial retrieval
      ↓
Material evidence gap detected
      ↓
One targeted verification search
      ↓
Curated additional evidence
      ↓
Answer revision + citation validation
```

With strict limits to prevent recursive search loops.

## 2. Cross-Mode Decision Chains

Example:

```text
Find a gaming laptop under ₹100,000
and nearby stores in Bengaluru.
```

Future ScoutAI could combine Shopping + Local evidence while keeping the two evidence types separate.

> Nearby retailer ≠ verified exact in-store inventory.

## 3. Better Commerce Coverage

- Amazon / Flipkart connectors
- Regional retailer adapters
- Better product matching
- Merchant-level comparison

## 4. Freshness-Aware Retrieval

- User-controlled refresh
- Explicit freshness windows
- “Refresh evidence” action

## 5. Advanced Trust Layer

- Semantic claim-to-evidence validation
- Source-quality indicators
- Query reranking
- Evidence diversity selection
- Controlled caching and freshness rules

## 6. Product & Deployment

- Market selector
- Accessibility improvements
- More responsive UI
- Secure cloud deployment
- Saved decision history
- Shared decision workspaces

---

# ⚙️ Installation

## Requirements

```text
Python 3.11+
Gemini API key
SerpApi API key
```

## 1. Clone

```bash
git clone https://github.com/YOUR_USERNAME/scoutai-live-decision-agent.git
cd scoutai-live-decision-agent
```

## 2. Create environment

### Windows

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 4. Add local secrets

Create `.env`:

```env
GEMINI_API_KEY=your_gemini_api_key
SERPAPI_API_KEY=your_serpapi_api_key
GEMINI_MODEL=your_available_gemini_model

APP_ENV=development

SHOPPING_GL=in
SHOPPING_HL=en
SHOPPING_MARKET_LABEL=India
```

## 5. Run

```bash
streamlit run app.py
```

## 6. Test

```bash
pytest
```

> **Never commit `.env`, API keys, or logs containing secrets.**

---

# 🏁 Final Word

ScoutAI is not trying to make an AI that merely **sounds right**.

It is built to make AI decisions more **inspectable, bounded, and grounded in live evidence**.

```text
SEARCH
  ↓
UNDERSTAND
  ↓
VERIFY
  ↓
SYNTHESIZE
  ↓
CITE
  ↓
DECIDE
```

> **ScoutAI: from “the AI says so” to “here is the evidence.”**
