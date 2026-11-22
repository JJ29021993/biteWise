# LLM Samples (Phase 3 — Groq)

Sample grounded prompt shape and parsed response used by the recommendation engine.

**Provider:** Groq (`https://api.groq.com/openai/v1`)  
**Default model:** `openai/gpt-oss-120b`  
**Env:** `GROQ_API_KEY` (or `LLM_API_KEY`)

Machine-readable fixtures also live under `tests/fixtures/`.

---

## System instructions (excerpt)

```
You are a restaurant recommendation assistant.
Rank and explain restaurants ONLY from the provided candidate list.
Do NOT invent restaurants, names, ratings, costs, cuisines, or locations.
...
Respond with a single JSON object only — no markdown fences, no prose outside JSON.
```

---

## User message shape

```json
{
  "preferences": {
    "location": "Indiranagar",
    "budget": "medium",
    "cuisine": "Italian",
    "min_rating": 4.0,
    "additional_preferences": "family-friendly, quiet ambience",
    "top_k": 3
  },
  "candidates": [
    {
      "restaurant_id": 101,
      "name": "Trattoria X",
      "location": "Indiranagar",
      "cuisines": "Italian, Pizza",
      "rating": 4.5,
      "cost_for_two": 1200.0,
      "budget": "medium",
      "votes": 850,
      "rest_type": "Casual Dining"
    }
  ]
}
```

The live prompt embeds these blocks as JSON text plus an explicit output schema.

---

## Sample model JSON response

```json
{
  "summary": "Solid mid-budget Italian picks in Indiranagar that clear your rating bar, with a lean toward family-friendly dining.",
  "recommendations": [
    {
      "restaurant_id": 101,
      "name": "Trattoria X",
      "rank": 1,
      "explanation": "Best overall fit: strong 4.5 rating, medium budget cost for two, and Italian cuisines match, with ambience that suits a family outing."
    },
    {
      "restaurant_id": 102,
      "name": "Pasta House",
      "rank": 2,
      "explanation": "Slightly cheaper medium-budget Italian option while staying above your 4.0 rating preference."
    }
  ]
}
```

After parsing, the engine **merges** ranks/explanations onto dataset rows. Name, rating, cost, cuisine, and location always come from the store — hallucinated restaurants are dropped.
