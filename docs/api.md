# REST API (Phase 6)

FastAPI surface over the same Phase 4 `recommend()` pipeline used by the Streamlit UI.

## Run

```powershell
pip install -e ".[api,data,llm]"
# optional: set API_CORS_ORIGINS / API_RATE_LIMIT_PER_MINUTE in .env
python -m src.api
# or: uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

- Interactive docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- OpenAPI JSON: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness / store readiness (`ok` or `degraded`) |
| `GET` | `/api/options` | Location / cuisine choices for the web UI |
| `POST` | `/api/recommendations` | Ranked recommendations for preferences |

### Health

```powershell
curl http://127.0.0.1:8000/health
```

Returns `status: degraded` and `store_ready: false` when `data/processed/restaurants.parquet` is missing (run `python -m src.ingestion` first).

### Recommendations

Request fields match architecture §3.2. Unknown fields are **rejected** (`extra=forbid` → HTTP 422). Optional `dry_run: true` skips live Groq calls.

```powershell
curl -X POST http://127.0.0.1:8000/api/recommendations `
  -H "Content-Type: application/json" `
  -d "{
    \"location\": \"Indiranagar\",
    \"budget\": \"medium\",
    \"cuisine\": \"Italian\",
    \"min_rating\": 4.0,
    \"additional_preferences\": \"family-friendly, quiet ambience\",
    \"top_k\": 5,
    \"dry_run\": true
  }"
```

Example success shape:

```json
{
  "summary": "…",
  "recommendations": [
    {
      "rank": 1,
      "name": "…",
      "cuisine": "Italian",
      "rating": 4.5,
      "estimated_cost": "₹1,200 for two",
      "location": "Indiranagar",
      "explanation": "…"
    }
  ],
  "meta": {
    "candidates_considered": 24,
    "filters_applied": ["location", "budget", "cuisine", "min_rating"],
    "dry_run": true
  },
  "preferences": { "location": "Indiranagar", "budget": "medium", "…": "…" }
}
```

Invalid payloads (bad budget, missing `cuisine`, extra fields) return **422** with a `detail` message or validation error list.

## Ops notes

- **CORS:** `API_CORS_ORIGINS` (comma-separated). Defaults include local Streamlit origins.
- **Rate limit:** `API_RATE_LIMIT_PER_MINUTE` (default 60) per client IP; `/health` and OpenAPI docs are exempt. Exceeding the limit returns **429**.
- Response DTOs share the Phase 4 contract (`summary`, `recommendations[]`, `meta`) so UI and API stay aligned.
