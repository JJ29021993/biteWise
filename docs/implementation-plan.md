# Implementation Plan

## AI-Powered Restaurant Recommendation System (Zomato Use Case)

Phase-wise plan for building the project described in `problemStatement.md` and `architecture.md`. Each phase has a goal, concrete tasks, deliverables, and exit criteria. Later phases assume earlier ones are complete.

**Approach:** filter-then-LLM hybrid recommender — deterministic retrieval first, grounded LLM ranking and explanations second.

---

## Phase Overview

| Phase | Name | Outcome |
|---|---|---|
| 0 | Project foundation | Repo, env, docs, dependency baseline |
| 1 | Data ingestion & store | Clean local restaurant dataset ready for queries |
| 2 | Preference & filter layer | Hard-constraint candidate retrieval |
| 3 | LLM recommendation engine | Ranked, explainable recommendations from candidates |
| 4 | Service orchestration | End-to-end pipeline behind a stable interface |
| 5 | User interface | Preference form + recommendation display |
| 6 | API hardening (optional) | REST API, validation, operational readiness |
| 7 | Testing, polish & docs | Reliability, README, demo readiness |

---

## Phase 0 — Project Foundation

**Goal:** Establish a runnable project skeleton and shared conventions.

### Tasks

- Initialize repository structure per architecture (`src/`, `data/`, `tests/`, `docs/`)
- Add `pyproject.toml` or `requirements.txt` with baseline deps (later phases pin versions as needed)
- Add `.env.example` (LLM API key placeholders; no secrets committed)
- Add `.gitignore` for `.env`, `data/raw/`, caches, virtualenvs
- Confirm Python 3.10+ and create a virtual environment
- Keep `docs/problemStatement.md` and `docs/architecture.md` as source of truth

### Deliverables

- Empty but coherent package layout
- Local env setup instructions drafted (finalized in Phase 7)
- Config entry points stubbed (settings module or env loader)

### Exit criteria

- Project installs cleanly in a fresh venv
- Docs are present and referenced as the build guide

---

## Phase 1 — Data Ingestion & Store

**Goal:** Load the Hugging Face Zomato dataset once, clean it, and persist a query-friendly local store.

### Tasks

- Integrate Hugging Face `datasets` loader for [ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation)
- Inspect schema; select relevant columns (name, location, cuisine, cost, rating, related fields)
- Implement preprocessing:
  - Handle nulls / bad ratings / missing cost
  - Normalize location and cuisine strings
  - Derive budget buckets (`low` / `medium` / `high`) from cost thresholds or percentiles
- Persist processed data to `data/processed/` (Parquet or CSV; SQLite optional)
- Add a small CLI or script: `python -m src.ingestion.load_dataset` (or equivalent)
- Cache raw download under `data/raw/` when useful; avoid re-downloading on every run

### Deliverables

- `src/ingestion/load_dataset.py`
- `src/ingestion/preprocess.py`
- Processed artifact in `data/processed/`
- Brief data dictionary (column meanings + budget mapping) in docs or module docstring

### Exit criteria

- Processed store loads in under a few seconds locally
- Key columns are non-null for the filtered working set
- Budget labels are reproducible from cost

---

## Phase 2 — Preference Validation & Filter Layer

**Goal:** Turn user preferences into a bounded candidate set without calling an LLM.

### Tasks

- Define a `UserPreferences` model (location, budget, cuisine, min_rating, additional_preferences, top_k)
- Implement validation/normalization (defaults, clamps, canonical strings)
- Map budget label → numeric cost range using Phase 1 thresholds
- Implement deterministic filters:
  - Location
  - Cuisine
  - Min rating
  - Budget/cost range
- Cap candidates (e.g. 20–50) before downstream LLM use
- Implement empty-result fallback / relaxation order (document behavior; e.g. cuisine → budget → rating)
- Return filter metadata (`filters_applied`, `candidates_considered`, whether relaxed)

### Deliverables

- `src/filtering/preferences.py`
- `src/filtering/restaurant_filter.py`
- Unit tests for common preference combinations and zero-result cases

### Exit criteria

- Given sample preferences, filter returns a relevant, bounded DataFrame/list
- Zero-match path is defined and test-covered
- Free-text additional preferences are carried through but not required for hard filtering

---

## Phase 3 — LLM Recommendation Engine

**Goal:** Rank filtered candidates and generate human-like explanations via a grounded prompt.

### Tasks

- Implement `PromptBuilder`:
  - System instructions: recommend only from provided candidates; do not invent restaurants
  - Include normalized preferences + candidate JSON/table
  - Request structured JSON output (rank, explanation, optional summary)
- Implement `LLMClient` abstraction targeting **Groq** (OpenAI-compatible API) with env-based API key (`GROQ_API_KEY`)
- Implement `ResponseParser` for JSON / fenced-JSON recovery
- Merge LLM ranks/explanations onto dataset facts (facts always win over model text)
- Add deterministic fallback ranking (e.g. by rating, then cost) if LLM fails
- Keep temperature low enough for stable ranking; tune `top_k` handling

### Deliverables

- `src/llm/prompt_builder.py`
- `src/llm/client.py`
- `src/llm/parser.py`
- Sample prompt + sample parsed response checked into docs or tests/fixtures

### Exit criteria

- LLM returns parseable ranked recommendations for a fixed candidate fixture
- Explanations reference user preferences
- Hallucinated restaurant names are rejected or ignored via merge-with-store logic
- Fallback path works with LLM mocked/unavailable

---

## Phase 4 — Service Orchestration

**Goal:** Wire ingestion store + filters + LLM into one recommendation pipeline.

### Tasks

- Implement `RecommenderService` / `src/services/recommender.py`:
  1. Validate preferences
  2. Load processed store (cached in memory after first load)
  3. Filter candidates
  4. Build prompt → call LLM → parse
  5. Map to response DTOs (`summary`, `recommendations[]`, `meta`)
- Define stable internal response schema matching architecture contracts
- Add logging for candidate counts and failures (no secrets in logs)
- Support a `dry_run` / mock-LLM mode for UI development without API spend

### Deliverables

- Working `recommend(preferences) -> RecommendationResponse` function/class
- Manual script or notebook cell that prints top recommendations for 2–3 preference sets

### Exit criteria

- One function call produces ranked restaurants with explanations end-to-end
- Meta includes filters applied and candidate counts
- Mock mode enables offline demos of everything except live LLM prose

---

## Phase 5 — User Interface

**Goal:** Deliver a usable preference form and clear recommendation display.

### Tasks

- Choose UI approach (recommended for speed: Streamlit or Gradio)
- Build input controls:
  - Location
  - Budget (low / medium / high)
  - Cuisine
  - Minimum rating
  - Additional preferences (text)
  - Top-K selector (optional)
- On submit, call Phase 4 service
- Render results:
  - Optional summary
  - Cards/list rows with name, cuisine, rating, estimated cost, explanation
  - Light meta (candidates considered / relaxed filters) for transparency
- Handle empty results and LLM errors with user-friendly messages
- Basic loading state while the LLM runs

### Deliverables

- `src/ui/app.py` (or equivalent)
- Runnable demo command documented (e.g. `streamlit run ...`)

### Exit criteria

- Non-technical user can enter preferences and see top recommendations
- Output matches problem-statement fields (name, cuisine, rating, cost, explanation)
- Errors do not crash the app silently

---

## Phase 6 — API Hardening (Optional)

**Goal:** Expose the same pipeline as a REST API for alternate clients.

### Tasks

- Add FastAPI app with `POST /api/recommendations`
- Reuse preference models and response DTOs from Phase 4
- Request validation via Pydantic
- CORS / basic rate-limiting considerations if deploying publicly
- Health endpoint for uptime checks
- Align OpenAPI schema with architecture request/response examples

### Deliverables

- `src/api/main.py`
- Example `curl` / HTTP request in docs

### Exit criteria

- UI (or HTTP client) can obtain identical recommendation payloads via API
- Invalid payloads return clear 4xx errors

*Skip this phase if Streamlit/Gradio-only delivery is sufficient for the current scope.*

---

## Phase 7 — Testing, Polish & Documentation

**Goal:** Make the project demo-ready, reproducible, and maintainable.

### Tasks

- Expand pytest coverage:
  - Ingestion/preprocessing invariants
  - Filter edge cases + relaxation
  - Prompt contains candidates and anti-hallucination instructions
  - Parser fixtures (valid, fenced, malformed)
  - Service tests with mocked LLM
- Add README:
  - What the project does
  - Setup (venv, deps, `.env`, data build step)
  - How to run UI / API
  - Architecture pointer to `docs/`
- Add sample screenshots or example recommendation outputs (optional)
- Final pass on config defaults (`top_k`, candidate cap, model name)
- Confirm non-goals remain out of scope (orders, payments, custom model training)

### Deliverables

- Passing test suite for core logic
- Complete `README.md`
- Demo-ready application

### Exit criteria

- Fresh clone → setup → ingest → run UI works using README alone
- Core tests pass without a live LLM key (mocks)
- Live demo with a real key produces explainable top-N recommendations

---

## Suggested Build Order (Dependency Graph)

```
Phase 0 Foundation
    │
    ▼
Phase 1 Data ingestion & store
    │
    ▼
Phase 2 Preferences & filters
    │
    ▼
Phase 3 LLM engine
    │
    ▼
Phase 4 Orchestration service
    │
    ├──────────────┐
    ▼              ▼
Phase 5 UI    Phase 6 API (optional)
    │              │
    └──────┬───────┘
           ▼
    Phase 7 Test, polish, docs
```

Phases 5 and 6 can proceed in parallel after Phase 4. Phase 7 runs continuously in light form (tests per phase) and as a final hardening pass.

---

## Milestone Checklist

Use this as a progress tracker:

- [x] **M0** Repo + env + layout ready
- [x] **M1** Processed Zomato store available locally
- [x] **M2** Filters return bounded candidates for sample prefs
- [x] **M3** LLM returns grounded ranked JSON with explanations
- [x] **M4** Single `recommend()` pipeline works end-to-end
- [x] **M5** UI demo runnable
- [x] **M6** (Optional) REST API live
- [x] **M7** README + tests + reproducible demo

---

## Effort Guidance (Rough)

| Phase | Relative effort | Notes |
|---|---|---|
| 0 | XS | Setup only |
| 1 | M | Schema discovery and cleaning dominate |
| 2 | M | Most important correctness layer |
| 3 | M–L | Prompt design + parsing robustness |
| 4 | S–M | Mostly wiring |
| 5 | M | UX polish and error states |
| 6 | S–M | Optional; fast if models already exist |
| 7 | M | Worth doing early tests incrementally |

---

## Implementation Principles (All Phases)

1. **Facts from data, prose from the LLM** — never let the model invent restaurants or overwrite rating/cost/name.
2. **Filter before generate** — keep prompts small and cheap.
3. **Mockable LLM boundary** — UI and tests must run without paid API calls.
4. **Ship vertical slices** — after Phase 4, prefer improving the full path over building unused abstractions.
5. **Docs stay in sync** — if architecture decisions change during build, update `architecture.md` in the same change.

---

## Out of Scope for This Plan

- Zomato clone features (cart, payments, live delivery)
- Training a custom recommender model
- Unbounded LLM search over the full raw corpus
- Production multi-tenant deployment, auth systems, or mobile apps

These can be future extensions after M7; they are not required to satisfy the problem statement.
