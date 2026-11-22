# Architecture

## AI-Powered Restaurant Recommendation System (Zomato Use Case)

This document describes the system architecture for a retrieval-plus-reasoning restaurant recommendation service. Structured filtering narrows candidates from a Zomato dataset; an LLM ranks those candidates and produces explainable recommendations for the user.

---

## 1. High-Level Overview

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Presentation│────▶│  API / Service  │────▶│ Recommendation   │────▶│  LLM Provider   │
│  Layer (UI)  │◀────│  Layer          │◀────│  Engine          │◀────│  (Groq)         │
└──────────────┘     └────────┬────────┘     └────────┬─────────┘     └─────────────────┘
                              │                       │
                              ▼                       ▼
                     ┌─────────────────┐     ┌──────────────────┐
                     │ Preference      │     │ Prompt Builder   │
                     │ Validation      │     │ + Ranker Context │
                     └─────────────────┘     └──────────────────┘
                              │
                              ▼
                     ┌─────────────────┐     ┌──────────────────┐
                     │ Data Access     │────▶│ Preprocessed     │
                     │ / Filter Layer  │     │ Restaurant Store │
                     └─────────────────┘     └────────┬─────────┘
                                                      │
                                                      ▼
                                             ┌──────────────────┐
                                             │ Hugging Face     │
                                             │ Zomato Dataset   │
                                             └──────────────────┘
```

**Core idea:** deterministic retrieval (filters) first, generative reasoning (LLM) second. The LLM never searches the full raw corpus; it only reasons over a bounded candidate set.

---

## 2. Architectural Style

| Concern | Choice | Rationale |
|---|---|---|
| Pattern | Layered + pipeline | Clear separation between ingestion, filtering, prompting, and presentation |
| Recommendation approach | Hybrid (rules + LLM) | Fast, controllable filtering; natural-language ranking and explanations |
| Data access | Local/preprocessed store after first load | Avoid repeated Hugging Face downloads and reduce latency |
| LLM usage | Prompted completion / chat | Rank + explain over structured candidate JSON |
| API shape | Request/response REST (or Streamlit/Gradio callbacks) | Simple preference in → ranked recommendations out |

---

## 3. Component Breakdown

### 3.1 Presentation Layer

**Responsibility:** collect preferences and render ranked results.

**Inputs collected:**

- Location (e.g. Bangalore)
- Budget (`low` | `medium` | `high`)
- Cuisine (e.g. Italian, Chinese)
- Minimum rating
- Free-text additional preferences (e.g. family-friendly, quick service)

**Outputs displayed per restaurant:**

- Name
- Cuisine
- Rating
- Estimated cost
- AI-generated explanation
- Optional overall summary of the recommendation set

**Suggested implementations:** Streamlit / Gradio for a fast demo UI, or a lightweight React/Next.js frontend against a FastAPI backend.

---

### 3.2 API / Service Layer

**Responsibility:** validate input, orchestrate the recommendation pipeline, and return a stable response contract.

**Typical endpoint:**

```http
POST /api/recommendations
```

**Request body (conceptual):**

```json
{
  "location": "Bangalore",
  "budget": "medium",
  "cuisine": "Italian",
  "min_rating": 4.0,
  "additional_preferences": "family-friendly, quiet ambience",
  "top_k": 5
}
```

**Response body (conceptual):**

```json
{
  "summary": "Here are the best mid-budget Italian picks in Bangalore...",
  "recommendations": [
    {
      "rank": 1,
      "name": "Trattoria X",
      "cuisine": "Italian",
      "rating": 4.5,
      "estimated_cost": "₹1,200 for two",
      "location": "Indiranagar",
      "explanation": "Matches your budget and rating bar, with strong reviews for family dining."
    }
  ],
  "meta": {
    "candidates_considered": 24,
    "filters_applied": ["location", "budget", "cuisine", "min_rating"]
  }
}
```

---

### 3.3 Preference Validation

**Responsibility:** normalize and validate user preferences before filtering.

- Canonicalize location and cuisine strings
- Map budget labels to cost ranges derived from the dataset distribution
- Clamp / default `min_rating` and `top_k`
- Keep free-text preferences for the LLM prompt (not for hard SQL-like filters unless explicitly mapped)

---

### 3.4 Data Ingestion & Store

**Responsibility:** load, clean, and persist restaurant records for fast filtering.

**Source:** [ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation)

**Pipeline steps:**

1. Download / load dataset from Hugging Face
2. Select relevant columns (name, location, cuisine, cost, rating, and related fields)
3. Clean nulls, normalize cuisine lists, standardize location names
4. Derive budget buckets (`low` / `medium` / `high`) from cost percentiles or fixed thresholds
5. Persist to a local store (CSV / Parquet / SQLite / in-memory DataFrame cache)

**Storage options:**

| Option | When to use |
|---|---|
| In-memory Pandas/Polars DataFrame | Prototyping and demos |
| Parquet on disk | Reproducible local reload without re-download |
| SQLite | Simple queryable persistence for a service |

---

### 3.5 Data Access / Filter Layer

**Responsibility:** apply hard constraints and produce a bounded candidate set for the LLM.

**Hard filters (deterministic):**

- Location match (exact or fuzzy / contains)
- Cuisine contains requested type
- Rating ≥ `min_rating`
- Cost within mapped budget range

**Soft signals (passed through to LLM, not used as hard rejects unless configured):**

- Additional free-text preferences
- Optional popularity / vote counts if present in the dataset

**Safeguards:**

- Cap candidates (e.g. top 20–50 by rating/cost fit) before prompting
- Fallback: if filters return zero rows, relax constraints in a defined order (cuisine → budget → rating) and surface that relaxation in `meta`

---

### 3.6 Prompt Builder

**Responsibility:** convert structured candidates + user preferences into a reliable LLM prompt.

**Prompt contents:**

- System role: restaurant recommendation assistant; rank only from provided candidates; do not invent restaurants
- User preferences block
- Candidate restaurants as compact structured JSON/table
- Output schema instructions (ranked list + explanation + optional summary)

**Design principles:**

- Ground answers in provided candidates only (anti-hallucination)
- Ask for explicit ranking criteria tied to preferences
- Request concise, user-facing explanations
- Prefer machine-parseable output (JSON) for UI rendering

---

### 3.7 Recommendation Engine (LLM)

**Responsibility:** rank filtered candidates and generate explanations.

**LLM tasks:**

1. Rank restaurants for fit
2. Explain each pick relative to preferences
3. Optionally summarize the overall shortlist

**Provider abstraction:**

```
RecommendationEngine
  ├── PromptBuilder
  ├── LLMClient (Groq via OpenAI-compatible API)
  └── ResponseParser (JSON → Recommendation DTO)
```

**Failure handling:**

- Retries with backoff on transient API errors
- Parser fallback if the model returns near-JSON / markdown-fenced JSON
- Deterministic fallback ranking (by rating then cost) if the LLM is unavailable, with a flag that explanations are unavailable

---

### 3.8 Output / Response Mapper

**Responsibility:** map parsed LLM output + original candidate fields into the UI/API contract.

- Merge LLM explanations onto source-of-truth restaurant attributes from the store
- Enforce `top_k`
- Attach filter metadata and candidate counts

---

## 4. End-to-End Data Flow

```
User preferences
        │
        ▼
Validate & normalize preferences
        │
        ▼
Filter restaurant store  ──▶  Candidate set (N items)
        │
        ▼
Build grounded prompt (preferences + candidates)
        │
        ▼
LLM rank + explain
        │
        ▼
Parse / validate model output
        │
        ▼
Map to response DTOs
        │
        ▼
Render in UI / return API JSON
```

**Latency path:** most time is spent in the LLM call. Filtering and local I/O should remain cheap relative to generation.

---

## 5. Suggested Repository Structure

```
Zomato_Project/
├── docs/
│   ├── problemStatement.md
│   └── architecture.md
├── data/
│   ├── raw/                  # optional cached HF download
│   └── processed/            # cleaned Parquet/CSV/SQLite
├── src/
│   ├── ingestion/
│   │   ├── load_dataset.py
│   │   └── preprocess.py
│   ├── filtering/
│   │   ├── preferences.py
│   │   └── restaurant_filter.py
│   ├── llm/
│   │   ├── prompt_builder.py
│   │   ├── client.py          # Groq (OpenAI-compatible)
│   │   ├── parser.py
│   │   ├── models.py
│   │   └── engine.py          # rank + merge + fallback
│   ├── services/
│   │   ├── recommender.py    # orchestration pipeline
│   │   └── models.py         # RecommendationResponse DTOs
│   ├── api/                  # FastAPI app (POST /api/recommendations, /health)
│   │   └── main.py
│   └── ui/                   # Streamlit frontend (BiteWise)
│       ├── app.py
│       └── render.py
├── tests/
├── .env.example
├── requirements.txt / pyproject.toml
└── README.md
```

---

## 6. Technology Stack (Recommended)

| Layer | Technology | Notes |
|---|---|---|
| Language | Python 3.10+ | Strong HF / data / LLM ecosystem |
| Dataset loading | `datasets` (Hugging Face) | Direct load of Zomato dataset |
| Data processing | Pandas or Polars | Cleaning, filtering, budget bucketing |
| Local store | Parquet or SQLite | Fast reload after ingestion |
| Backend API | FastAPI | Optional; clean contracts for UI |
| UI | Streamlit or Gradio | Fastest path to a usable demo |
| LLM | Groq API (OpenAI-compatible) | Ranking + explanations (`openai/gpt-oss-120b` default) |
| Config / secrets | `.env` + pydantic settings | API keys never committed |
| Testing | pytest | Filter logic and prompt/parser unit tests |

Exact provider and UI choices can vary; the layered contracts above should remain stable.

---

## 7. Key Design Decisions

### 7.1 Filter-then-LLM (not LLM-only search)

Hard constraints (location, budget, cuisine, rating) are applied in code. The LLM ranks and explains a small candidate set. This improves cost, latency, controllability, and factual grounding.

### 7.2 Grounded generation

Restaurant facts (name, rating, cost, cuisine, location) always come from the dataset. The LLM may reorder and explain, but must not invent restaurants or overwrite factual fields.

### 7.3 Budget as a derived feature

User-facing budget labels map to numeric cost ranges computed from the dataset (thresholds or percentiles). This keeps UX simple while preserving dataset realism.

### 7.4 Free-text preferences stay soft

Phrases like “family-friendly” or “quick service” are injected into the prompt as soft criteria unless the dataset has reliable matching columns. This avoids brittle hard filters on incomplete metadata.

### 7.5 Parseable LLM outputs

The engine requests structured JSON so the UI can render cards consistently. Narrative text is confined to `explanation` / `summary` fields.

---

## 8. Cross-Cutting Concerns

### Configuration

- Dataset path / HF dataset id
- Budget thresholds
- Candidate cap and `top_k` defaults
- LLM model name, temperature, max tokens
- API keys via environment variables

### Observability

- Log filter counts (input → candidates → returned)
- Log prompt/response sizes (not full PII-heavy prompts in production unless needed)
- Surface `meta` to the UI for transparency when filters are relaxed

### Security & privacy

- Do not commit API keys
- Treat free-text preferences as untrusted input; keep them in the user message, not in executable code paths
- Rate-limit public API deployments

### Testing strategy

| Layer | What to test |
|---|---|
| Ingestion | Column presence, null handling, budget derivation |
| Filtering | Exact preference cases, empty results, relaxation order |
| Prompt builder | Candidate inclusion, schema instructions present |
| Parser | Valid JSON, fenced JSON, malformed fallback |
| Service | End-to-end with mocked LLM client |

---

## 9. Sequence Diagram (Single Recommendation Request)

```
User          UI/API        Validator      Filter        PromptBuilder     LLMClient      Parser
 │               │              │            │                │               │             │
 │ submit prefs  │              │            │                │               │             │
 │──────────────▶│              │            │                │               │             │
 │               │ validate     │            │                │               │             │
 │               │─────────────▶│            │                │               │             │
 │               │ normalized   │            │                │               │             │
 │               │◀─────────────│            │                │               │             │
 │               │ filter candidates         │                │               │             │
 │               │──────────────────────────▶│                │               │             │
 │               │ candidate rows            │                │               │             │
 │               │◀──────────────────────────│                │               │             │
 │               │ build prompt              │                │               │             │
 │               │───────────────────────────────────────────▶│               │             │
 │               │ prompt                    │                │               │             │
 │               │◀───────────────────────────────────────────│               │             │
 │               │ complete(...)             │                │               │             │
 │               │───────────────────────────────────────────────────────────▶│             │
 │               │ raw model text            │                │               │             │
 │               │◀───────────────────────────────────────────────────────────│             │
 │               │ parse                     │                │               │             │
 │               │────────────────────────────────────────────────────────────────────────▶│
 │               │ structured ranks          │                │               │             │
 │               │◀────────────────────────────────────────────────────────────────────────│
 │ recommendations + explanations            │                │               │             │
 │◀──────────────│              │            │                │               │             │
```

---

## 10. Extensibility Hooks

Future enhancements that fit this architecture without redesign:

- **Embeddings retrieval:** add a vector index for semantic cuisine/ambiance search before (or instead of) keyword cuisine filters
- **User profiles / history:** inject past likes into the prompt as additional soft context
- **Streaming UI:** stream LLM tokens for summary/explanations while keeping final JSON parse at the end
- **Multi-city support:** partition or index the store by city/location for faster filters
- **Evaluation harness:** offline test set of preference → expected restaurants for regression on filter + prompt changes

---

## 11. Non-Goals (Current Scope)

- Full Zomato product clone (orders, payments, live delivery tracking)
- Training a custom recommender model from scratch
- Unbounded LLM browsing of the entire raw dataset without filtering
- Real-time restaurant availability / table booking integrations

---

## 12. Architecture Summary

The system is a **layered hybrid recommender**:

1. **Ingest & store** Zomato data once in a clean local form  
2. **Validate** user preferences  
3. **Filter** to a small, relevant candidate set  
4. **Prompt** an LLM with grounded candidate context  
5. **Parse & merge** ranked explanations onto dataset facts  
6. **Present** top recommendations with clear cost, rating, cuisine, and rationale  

This keeps recommendations personalized and explainable while remaining cost-efficient, testable, and resistant to hallucination.
