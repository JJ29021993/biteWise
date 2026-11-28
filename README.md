# AI-Powered Restaurant Recommendation System (Zomato Use Case)

Hybrid **filter-then-LLM** recommender: deterministic restaurant filtering first, then grounded Groq ranking and explanations. Facts (name, rating, cost, cuisine) always come from the local dataset; the LLM only ranks and explains.

## Tech stack

| Layer | Choice |
|---|---|
| API | Python 3.10+ (3.12 recommended), FastAPI, Uvicorn, Pydantic v2 |
| LLM | Groq via the OpenAI-compatible SDK. Default model `openai/gpt-oss-120b` |
| Data | Hugging Face `datasets`, pandas, Parquet (`pyarrow`) |
| Web UI | Next.js 15, React 19, TypeScript, Tailwind CSS |
| Alternate UI | Streamlit |
| Tests | pytest. The suite runs without a live Groq key |
| Deploy | Docker Compose locally. API hosted on Railway |

Project docs (source of truth):

- [`docs/problemStatement.md`](docs/problemStatement.md) — goals and workflow
- [`docs/architecture.md`](docs/architecture.md) — system design
- [`docs/implementation-plan.md`](docs/implementation-plan.md) — phase-wise build plan
- [`docs/edge-case.md`](docs/edge-case.md) — edge cases and failure modes
- [`docs/api.md`](docs/api.md) — REST API contract and curl examples
- [`docs/data-dictionary.md`](docs/data-dictionary.md) — processed columns + budget mapping
- [`docs/example-outputs.md`](docs/example-outputs.md) — sample recommendation outputs
- [`docs/deployment-plan.md`](docs/deployment-plan.md) — host / Docker deploy

---

## Status

**Phase 7 complete** — demo-ready: setup → ingest → UI/API, with a pytest suite that runs without a live LLM key.

---

## Quick start (fresh clone)

```powershell
# 1) Environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[all]"
copy .env.example .env

# 2) Optional: set GROQ_API_KEY in .env for live ranking
#    Leave empty (or LLM_MOCK_MODE=true) for dry-run / fallback demos

# 3) Build the local restaurant store (one-time; caches under data/)
python -m src.ingestion

# 4a) REST API (required by the Next.js UI)
python -m src.api

# 4b) Next.js UI (recommended)
cd web
npm install
npm run dev

# 4c) Or Streamlit UI
streamlit run src/ui/app.py

# 5) Tests (no live LLM required)
pytest
```

Next.js UI: [http://localhost:3000](http://localhost:3000) (see [`web/README.md`](web/README.md)).  
Streamlit UI: usually `http://localhost:8501`.  
API docs: `http://127.0.0.1:8000/docs`.

---

## Prerequisites

- Python **3.10+** (3.12 recommended)
- pip / venv
- Optional: [Groq API key](https://console.groq.com/keys) for live explanations

---

## Setup details

```powershell
pip install -e ".[dev]"                  # core + pytest
pip install -e ".[dev,data,llm,ui,api]"   # full local stack
# or: pip install -e ".[all]"
```

Edit `.env` from `.env.example`. Important knobs (defaults in `src/config/settings.py`):

| Variable | Default | Notes |
|---|---|---|
| `GROQ_API_KEY` | _(empty)_ | Required for live LLM; optional for dry-run |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Groq chat model |
| `LLM_MOCK_MODE` | `false` | Skip live calls globally |
| `DEFAULT_TOP_K` | `5` | Default shortlist size |
| `CANDIDATE_CAP` | `50` | Max candidates sent to the LLM |
| `API_RATE_LIMIT_PER_MINUTE` | `60` | Per-IP rolling window |

Verify install:

```powershell
python -c "from src.config import get_settings; print(get_settings().hf_dataset_id)"
pytest
```

---

## Data ingestion

Download the Hugging Face dataset (cached under `data/raw/`), clean it, and write:

- `data/processed/restaurants.parquet`
- `data/processed/budget_thresholds.json`

```powershell
python -m src.ingestion
python -m src.ingestion --force-download   # ignore local raw cache
```

---

## Filtering

Hard filters: location, cuisine (OR if comma-separated), budget, min rating.  
If nothing matches, constraints relax in order: **cuisine → budget → min_rating** (location never relaxes). Soft `additional_preferences` are kept for the LLM only.

```powershell
python -c "from src.filtering import filter_restaurants; r=filter_restaurants(location='Indiranagar', budget='medium', cuisine='Italian', min_rating=4.0); print(len(r.candidates), r.meta.to_dict())"
```

---

## LLM ranking (Groq)

```powershell
python -c "from src.filtering import filter_restaurants; from src.llm import rank_candidates; r=filter_restaurants(location='Indiranagar', budget='medium', cuisine='Italian', min_rating=4.0, top_k=3); out=rank_candidates(r.preferences, r.candidates); print(out.to_dict())"
```

Without a key (or with `LLM_MOCK_MODE=true` / `dry_run=True`), ranking falls back to rating/cost order or mock explanations and sets `llm_fallback` / `dry_run` in meta. Samples: [`docs/llm-samples.md`](docs/llm-samples.md).

### System prompt

Sent as the Groq system message from [`src/llm/prompt_builder.py`](src/llm/prompt_builder.py). The model may only rank and explain restaurants already in the filtered candidate list.

```
You are a restaurant recommendation assistant.
Rank and explain restaurants ONLY from the provided candidate list.
Do NOT invent restaurants, names, ratings, costs, cuisines, or locations.
Do NOT overwrite factual fields from the candidate data.
Hard filters already applied by the system take priority over soft preferences.
If soft preferences conflict with hard filters, note the tension briefly but still recommend from the given candidates.
Return concise, user-facing explanations that reference the user's preferences.
Keep each explanation to 1-2 short sentences.
Respond with a single JSON object only — no markdown fences, no prose outside JSON.
```

### Response schema

The user message sends preferences, the capped candidate JSON, and this contract. The model must return one JSON object and nothing else.

```json
{
  "summary": "optional short overview of the shortlist",
  "recommendations": [
    {
      "restaurant_id": 101,
      "name": "exact name from candidates",
      "rank": 1,
      "explanation": "1-2 short sentences why this fits"
    }
  ]
}
```

Rules sent with that shape:

- Include at most `top_k` recommendations.
- Prefer `restaurant_id` for identity. `name` must match a candidate exactly when used.
- Only recommend restaurants present in `candidates`.
- Rank 1 is the best fit.
- Keep the JSON compact so the response finishes completely.

The HTTP response is wider than this. After parsing, the API copies name, cuisine, rating, cost, and location from the dataset and adds `meta` (filters, candidate counts, `dry_run`, `llm_fallback`). Contract: [`docs/api.md`](docs/api.md). Sample prompt and parsed JSON: [`docs/llm-samples.md`](docs/llm-samples.md).

### Prompt versions

There is one shipped system prompt. It was introduced with the recommender in commit `26aa9f2` (22 Nov 2026) and has not been revised since. Git history of `src/llm/prompt_builder.py` has no earlier or later wording.

That single version was written to lock four constraints in the instruction itself:

| Constraint in the prompt | Why it is there |
|---|---|
| Rank only from the provided candidate list. Do not invent restaurants or facts. | The model was ranking a filtered shortlist, not searching the web or the full corpus. |
| Do not overwrite factual fields. Hard filters beat soft preferences. | Rating, cost, cuisine, and location must stay dataset values. Free-text preferences such as "family-friendly" can influence the explanation, not the filter. |
| Explanations are 1–2 sentences and must reference the user's preferences. | Keeps the card copy short enough for the UI and tied to the request. |
| One JSON object, no markdown fences. | The parser needs a stable payload. Fenced JSON is still recovered, but the prompt asks for raw JSON so the happy path does not depend on that recovery. |

The default Groq model did change around the same time: `llama-3.3-70b-versatile` was retired on the free/dev tier, so settings now default to `openai/gpt-oss-120b`. That was a model swap, not a prompt rewrite.

### How the scope limit is enforced

The prompt tells the model to stay inside the candidate list. The code enforces that bound whether or not the model follows the instruction.

1. **Filter first.** Location, cuisine, budget, and minimum rating run before any LLM call. If the set is empty, constraints relax in order cuisine, then budget, then minimum rating. Location never relaxes.
2. **Candidate cap.** After name dedupe, the filter keeps at most `CANDIDATE_CAP` rows (default **50**) and only those rows are serialized into the prompt (`src/filtering/restaurant_filter.py`).
3. **`top_k` clamp.** Callers ask for a shortlist (default **5**, minimum 1). If `top_k` is larger than `candidate_cap`, validation clamps it (`src/filtering/preferences.py`). The user message then says `Return at most {k} recommendations.`
4. **Merge drops anything outside the list.** `merge_with_candidates` keeps a model row only when `restaurant_id` matches, or the name matches a candidate after case and whitespace normalization. Unknown restaurants are ignored. Name, rating, cost, cuisine, and location are copied from the store. The merged list is cut at `top_k` (`src/llm/engine.py`).
5. **Fallback stays inside the same cap.** If Groq is missing, times out, or returns nothing usable, ranking falls back to rating then cost, still limited to `top_k`, and `meta.llm_fallback` is set.

`meta.candidates_before_cap`, `meta.candidates_considered`, `meta.candidate_cap`, and `meta.top_k` record what the cap did on that request.

---

## Recommend pipeline

```powershell
python -c "from src.services import recommend; r=recommend(location='Indiranagar', budget='medium', cuisine='Italian', min_rating=4.0, top_k=3, dry_run=True); print(r.summary); print(r.to_dict())"
```

Demo script (3 preference sets; default dry-run):

```powershell
python scripts/demo_recommend.py
python scripts/demo_recommend.py --live
```

Example outputs: [`docs/example-outputs.md`](docs/example-outputs.md).

---

## User interface

```powershell
streamlit run src/ui/app.py
```

- Enter location, budget, cuisine, min rating, optional soft preferences, and top-K
- Sidebar **Dry-run** skips live Groq calls for offline demos
- Results show name, cuisine, rating, cost, explanation, plus filter/LLM meta

---

## Docker deploy (API + Next.js)

Requires Docker Desktop (or Engine + Compose). Build the processed store once on the host, then:

```powershell
python -m src.ingestion
docker compose up --build
```

- UI: http://localhost:3000  
- API health: http://localhost:8000/health  

Pass `GROQ_API_KEY` in the environment for live ranking. Full topology, env, and PaaS notes: [`docs/deployment-plan.md`](docs/deployment-plan.md).

---

## REST API

```powershell
python -m src.api
```

```powershell
curl -X POST http://127.0.0.1:8000/api/recommendations `
  -H "Content-Type: application/json" `
  -d "{\"location\":\"Indiranagar\",\"budget\":\"medium\",\"cuisine\":\"Italian\",\"min_rating\":4.0,\"top_k\":3,\"dry_run\":true}"
```

- Health: `GET /health`
- Recommend: `POST /api/recommendations`
- Full contract: [`docs/api.md`](docs/api.md)

---

## Testing

```powershell
pytest
```

Core suite covers ingestion invariants, filter edge cases + relaxation, prompt anti-hallucination instructions, parser fixtures (valid / fenced / malformed), and the recommend service with a mocked LLM. **No live `GROQ_API_KEY` is required.**

Fixtures live under `tests/fixtures/`.

---

## Repository layout

```
Zomato_Project/
├── docs/                  # Problem, architecture, plan, edge cases, API, samples
├── data/
│   ├── raw/               # Cached HF download (gitignored content)
│   └── processed/         # Cleaned store (gitignored content)
├── src/
│   ├── config/            # Settings / env loader
│   ├── ingestion/         # Data load / preprocess
│   ├── filtering/         # Preferences + hard filters
│   ├── llm/               # Groq prompt / client / parser / engine
│   ├── services/          # recommend() orchestration
│   ├── ui/                # Streamlit app
│   └── api/               # FastAPI app
├── scripts/               # Demo / verify helpers
├── tests/
├── web/                   # Next.js UI
├── Dockerfile             # FastAPI image
├── docker-compose.yml     # API + web
├── .env.example
├── pyproject.toml
└── README.md
```

---

## Out of scope

Not part of this project (see also the implementation plan):

- Cart, payments, live delivery, or a Zomato clone
- Training a custom recommender model
- Unbounded LLM search over the full raw corpus
- Production multi-tenant auth, mobile apps, or live menu/availability

---

## Architecture pointer

Filter-then-LLM pipeline: validate preferences → load processed store → hard filters (+ optional relaxation) → grounded Groq rank/explain → merge facts from the store → UI or API response. Details and contracts: [`docs/architecture.md`](docs/architecture.md).
