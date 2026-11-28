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

## System prompt

Live ranking sends this system prompt to Groq. The UI never calls the model directly. Hard filters run first, and restaurant facts (name, rating, cost, cuisine, location) always come from the processed dataset. Source: [`src/llm/prompt_builder.py`](../src/llm/prompt_builder.py).

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

The user message then includes preferences, the capped candidate list, and this output contract:

```
Required JSON shape:
{
  "summary": "optional short overview of the shortlist",
  "recommendations": [
    {
      "restaurant_id": <int from candidates>,
      "name": "<exact name from candidates>",
      "rank": <1-based integer>,
      "explanation": "<1-2 short sentences why this fits>"
    }
  ]
}
Rules:
- Include at most top_k recommendations.
- Prefer restaurant_id for identity; name must match a candidate exactly when used.
- Only recommend restaurants present in candidates.
- Rank 1 = best fit.
- Keep the JSON compact so it finishes completely.
```

Sample prompt and parsed response: [`docs/llm-samples.md`](../docs/llm-samples.md).
