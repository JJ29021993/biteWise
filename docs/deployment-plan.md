# Deployment Plan

How to take BiteWise (Zomato recommender) from a local demo to a hosted environment.

**Stack to deploy**

| Piece | Runtime | Entry | Default local port |
|---|---|---|---|
| REST API | Python 3.10+ / FastAPI + uvicorn | `python -m src.api` | `8000` |
| Web UI | Node 20+ / Next.js 15 | `web/` → `npm run start` | `3000` |
| Restaurant store | Local Parquet | Built by `python -m src.ingestion` | `data/processed/` |
| LLM | Groq (OpenAI-compatible) | Env `GROQ_API_KEY` | External HTTPS |

The Next.js UI talks to the API over HTTP (`NEXT_PUBLIC_API_BASE_URL`). Facts come from the processed store; Groq only ranks and explains. Without a key (or with `LLM_MOCK_MODE=true` / request `dry_run: true`), the API still serves recommendations via fallback ranking.

Out of scope for this project’s current phase: auth, multi-tenant tenancy, payments, and managed databases. Deploy as a small API + Next.js frontend with a baked or build-time Parquet store. Docker images and `docker-compose.yml` ship in-repo for local/single-host deploys.

---

## 1. Recommended topologies

### A. Split hosting (preferred for demos)

```
Browser → Next.js (Vercel / Netlify / any Node host)
              │
              │  HTTPS POST /api/recommendations
              ▼
         FastAPI (Railway / Render / Fly.io / VPS)
              │
              ├── data/processed/restaurants.parquet  (on disk or mounted volume)
              └── Groq API (outbound HTTPS)
```

- Frontend: set `NEXT_PUBLIC_API_BASE_URL` to the public API origin (no trailing slash).
- Backend: set `API_HOST=0.0.0.0`, bind a public port, and set `API_CORS_ORIGINS` to the exact frontend origin(s).

### B. Single VM / VPS (simple, full control)

One Linux box runs both processes behind nginx (or Caddy):

- `api.example.com` → uvicorn on `127.0.0.1:8000`
- `app.example.com` (or `/`) → `next start` on `127.0.0.1:3000`

Use systemd or the shipped `docker compose up --build` stack to keep both alive. CORS can stay same-site or list both origins.

### C. API-only

Useful for Postman, curl, or a custom client. Expose `/docs` only if you want interactive exploration. Still needs the same processed data and optional Groq key.

---

## 2. Prerequisites

**Build machine / CI image**

- Python **3.10+** (3.12 recommended)
- Node.js **20+** and npm (for `web/`)
- Network access to Hugging Face (first ingestion) and Groq (live ranking)
- ~500 MB disk for venv + Node modules; processed Parquet is ~3 MB today

**Secrets (never commit)**

| Secret / env | Where | Required? |
|---|---|---|
| `GROQ_API_KEY` | API host `.env` | For live LLM; optional if demos use dry-run / mock |
| `NEXT_PUBLIC_API_BASE_URL` | Web host env | Yes for production frontend |
| `API_CORS_ORIGINS` | API host | Yes when frontend origin ≠ localhost |

Copy from repo templates:

- Root: `.env.example` → `.env`
- Web: `web/.env.local.example` → `web/.env.local` (local) or platform env vars (hosted)

---

## 3. Pre-deploy checklist

1. **Clone and install Python deps** (API host or build job):

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
   pip install --upgrade pip
   pip install -e ".[data,llm,api]"
   ```

2. **Configure env** on the API host (see §5). At minimum for a public demo:

   - `API_HOST=0.0.0.0`
   - `API_PORT=8000` (or platform-assigned port)
   - `API_CORS_ORIGINS=https://your-frontend.example.com`
   - `GROQ_API_KEY=...` (or `LLM_MOCK_MODE=true` for offline demos)
   - `API_RATE_LIMIT_PER_MINUTE=60` (raise carefully)

3. **Build the restaurant store** (must exist before healthy recommendations):

   ```bash
   python -m src.ingestion
   ```

   Produces:

   - `data/processed/restaurants.parquet`
   - `data/processed/budget_thresholds.json`

   These paths are gitignored. Either:

   - Run ingestion on each deploy / cold start, or
   - Bake the two processed files into the image / release artifact, or
   - Mount a persistent volume at `data/processed/`.

   Without the Parquet file, `GET /health` returns `status: degraded` and `store_ready: false`.

4. **Verify API locally / in staging**:

   ```bash
   python -m src.api
   curl http://127.0.0.1:8000/health
   pytest
   ```

5. **Install and build the web app** (frontend host or same VM):

   ```bash
   cd web
   npm ci
   # set NEXT_PUBLIC_API_BASE_URL before build (it is inlined at build time)
   npm run build
   npm run start
   ```

---

## 4. Deploy steps by component

### 4.1 FastAPI backend

**Start command**

```bash
python -m src.api
# equivalent:
# uvicorn src.api.main:app --host 0.0.0.0 --port $PORT
```

On PaaS platforms that inject `PORT`, no extra mapping is required: settings accept `PORT` as an alias of `API_PORT` (explicit `API_PORT` wins if both are set).

**Health**

- Liveness: `GET /health` → expect `ok` and `store_ready: true`
- Smoke recommend (dry-run, no Groq required):

  ```bash
  curl -X POST "$API_URL/api/recommendations" \
    -H "Content-Type: application/json" \
    -d '{"location":"Indiranagar","budget":"medium","cuisine":"Italian","min_rating":4.0,"top_k":3,"dry_run":true}'
  ```

**Process supervision**

- Prefer one worker initially (`uvicorn` single process as in `python -m src.api`). The in-memory rate limiter is per-process; multiple workers reset/split limits unless you add shared storage later.
- Restart policy: always; ensure `data/processed/` survives restarts if you do not re-ingest on boot.

**Outbound network**

- Allow HTTPS to `api.groq.com` when live ranking is enabled.
- First-time ingestion also needs Hugging Face dataset download unless processed files are pre-baked.

### 4.2 Next.js frontend (`web/`)

**Env (build-time)**

```bash
NEXT_PUBLIC_API_BASE_URL=https://api.example.com
```

No trailing slash. Wrong or missing value leaves the browser calling localhost and fails in production.

**Commands**

```bash
cd web
npm ci
npm run build
npm run start   # listens on 3000 by default; set PORT if the host requires it
```

**Platform notes**

- **Vercel / Netlify-style hosts:** connect the `web/` subdirectory as the app root; set `NEXT_PUBLIC_API_BASE_URL` in the dashboard; build command `npm run build`, output handled by Next.
- **Same VPS as API:** reverse-proxy to `localhost:3000`; keep CORS origins accurate.

The UI defaults dry-run on in the form for safe demos; live mode still depends on the API having a valid Groq key.

---

## 5. Environment reference (production)

### API (`.env` on the API host)

| Variable | Production guidance |
|---|---|
| `GROQ_API_KEY` | Set for live explanations; store in the host secret manager |
| `GROQ_MODEL` | Keep default unless Groq retires the model |
| `GROQ_BASE_URL` | `https://api.groq.com/openai/v1` |
| `LLM_MOCK_MODE` | `false` for live; `true` for cost-free demos |
| `LLM_TIMEOUT_SECONDS` | Default `45`; raise only if Groq latency warrants |
| `DEFAULT_TOP_K` / `CANDIDATE_CAP` | Defaults `5` / `50`; cap bounds LLM cost |
| `API_HOST` | `0.0.0.0` on containers/VMs (not `127.0.0.1`) |
| `API_PORT` | Match platform `PORT` or reverse-proxy upstream |
| `API_CORS_ORIGINS` | Exact frontend origins, comma-separated; avoid `*` with credentials |
| `API_RATE_LIMIT_PER_MINUTE` | Keep ≥1; `/health` and OpenAPI docs are exempt |
| `API_DISABLE_DOCS` | `true` hides `/docs`, `/redoc`, `/openapi.json` |
| `RUN_INGESTION` | Docker entrypoint only: `true` builds the store if Parquet is missing |

### Web

| Variable | Production guidance |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | Public API origin, e.g. `https://api.example.com` |

---

## 6. Docker (recommended local / single-host path)

Artifacts:

| File | Role |
|---|---|
| `Dockerfile` | FastAPI image (`API_HOST=0.0.0.0`, healthcheck, entrypoint) |
| `web/Dockerfile` | Next.js standalone image |
| `docker-compose.yml` | API + web on ports 8000 / 3000 |
| `scripts/docker-entrypoint.sh` | Warns or runs ingestion when Parquet is missing |

```bash
# From repo root (PowerShell: same commands in Docker Desktop)
python -m venv .venv && source .venv/bin/activate   # or Windows Activate.ps1
pip install -e ".[data,llm,api]"
python -m src.ingestion                              # bake data/processed for the volume

# Optional: export GROQ_API_KEY=... for live ranking
docker compose up --build
```

- UI: http://localhost:3000  
- API: http://localhost:8000/health  
- `NEXT_PUBLIC_API_BASE_URL` defaults to `http://127.0.0.1:8000` so the **browser** reaches the published API port (not the Compose DNS name `api`).
- First cold start without Parquet: set `RUN_INGESTION=true` (needs HF network) or mount/bake `data/processed/`.

Build images alone:

```bash
docker build -t bitewise-api .
docker build -t bitewise-web \
  --build-arg NEXT_PUBLIC_API_BASE_URL=https://api.example.com \
  ./web
```

---

## 7. Suggested platform mappings

| Role | Fit | Notes |
|---|---|---|
| API | Railway, Render, Fly.io, any Linux VPS, or `Dockerfile` | Persist or bake `data/processed/`; start `python -m src.api` |
| Web | Vercel, Netlify, Cloudflare Pages (Next), `web/Dockerfile`, or same VPS | Set `NEXT_PUBLIC_API_BASE_URL` **before** `next build` |
| Secrets | Platform env / Vault / Doppler | Never commit `.env` or `web/.env.local` |
| TLS | Platform default or Caddy/nginx | Terminate TLS at the edge; proxy to uvicorn/Next |

**Minimal demo path:** `docker compose up --build` locally, or deploy API on one PaaS with pre-baked Parquet + optional Groq key and `web/` to Vercel with the API URL.

---

## 8. Data & release strategy

1. **Bake processed data into the release** when the dataset is stable (simplest ops). Run ingestion in CI, then publish an artifact that includes `data/processed/*`.
2. **Re-ingest on deploy** when you want fresher HF data: add a release step `python -m src.ingestion` (or `--force-download`) before starting uvicorn. Cold starts will be slower and need HF access.
3. **Volume mount** if the host is long-lived: persist `data/processed/` so restarts skip download.

Do not rely on `data/raw/` at runtime for recommendations; only the processed store is required after ingestion.

---

## 9. Security & ops

- **Secrets:** `GROQ_API_KEY` only on the API host. The browser never needs it.
- **CORS:** list exact production frontend origins. Localhost defaults are for development only.
- **Rate limiting:** in-process sliding window per client IP (`API_RATE_LIMIT_PER_MINUTE`). Fine for demos; not a substitute for an edge WAF under abuse.
- **OpenAPI `/docs`:** set `API_DISABLE_DOCS=true` in public deploys to remove `/docs`, `/redoc`, and `/openapi.json`.
- **Logging:** prefer status codes, latency, `meta` flags (`dry_run`, `llm_fallback`); avoid logging full preference free-text or prompts with PII.
- **LLM cost / failure:** dry-run and mock mode keep demos working when Groq is down or keys are missing; live mode should tolerate `llm_fallback` in response meta.
- **Scaling:** prefer horizontal scale of the Next.js tier first. API scaling needs either sticky single-instance rate limits or a shared limiter; Parquet is read-only and can be copied per instance.

---

## 10. Post-deploy verification

| Check | Expect |
|---|---|
| `GET {API}/health` | `ok`, `store_ready: true` |
| `GET {API}/api/options` | Non-empty locations / cuisines |
| `POST {API}/api/recommendations` with `dry_run: true` | 200 + ranked list + meta |
| Same request without dry-run (key present) | 200; explanations present unless fallback |
| Open frontend URL | Form loads; submit returns cards |
| Browser network tab | Calls go to production API origin, not localhost |
| CORS error in console | Fix `API_CORS_ORIGINS` to match the exact UI origin |
| `pytest` in CI | Green without a live Groq key |

---

## 11. Rollback

1. Keep the previous API release (and its matching `data/processed/` snapshot) ready to redeploy.
2. Frontend: revert the Vercel/host deployment or redeploy the prior git SHA; confirm `NEXT_PUBLIC_API_BASE_URL` still points at a healthy API.
3. If Groq model deprecations break live ranking, set `LLM_MOCK_MODE=true` or instruct clients to use `dry_run` while updating `GROQ_MODEL`.

---

## 12. Cutover order (first production demo)

1. Ingest (or bake) processed data.
2. Deploy API (`docker compose` or PaaS) with `API_HOST=0.0.0.0`, CORS, and secrets.
3. Confirm `/health` and dry-run `POST /api/recommendations`.
4. Build/deploy Next.js with `NEXT_PUBLIC_API_BASE_URL` set to the live API.
5. Smoke-test the UI end-to-end (dry-run, then live if keyed).
6. Set `API_DISABLE_DOCS=true` and tune `API_RATE_LIMIT_PER_MINUTE` if public.

---

## Related docs

- [`architecture.md`](architecture.md) — system design
- [`api.md`](api.md) — REST contract and curl examples
- [`edge-case.md`](edge-case.md) — failure modes (incl. public rate limits)
- [`implementation-plan.md`](implementation-plan.md) — build phases
- Root [`README.md`](../README.md) — local quick start
- [`web/README.md`](../web/README.md) — Next.js local run
