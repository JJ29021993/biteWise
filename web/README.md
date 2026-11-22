# BiteWise Web (Next.js)

Cinematic Epicurean dark UI for BiteWise — Next.js 15 + Tailwind, talking to the FastAPI backend.

## Prerequisites

- Node 20+
- API running with processed data:

```powershell
# from repo root
.\.venv\Scripts\Activate.ps1
python -m src.ingestion   # once
python -m src.api         # http://127.0.0.1:8000
```

## Run

```powershell
cd web
copy .env.local.example .env.local   # if needed
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

`NEXT_PUBLIC_API_BASE_URL` defaults to `http://127.0.0.1:8000`. Dry-run is on by default in the form so demos work without a Groq key.
