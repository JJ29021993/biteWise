# Example Recommendation Outputs

Captured from the Phase 4 demo script in **dry-run / mock LLM** mode (no live API key required).

```powershell
python scripts/demo_recommend.py
```

These illustrate grounded facts from the processed store plus preference-aware explanations. Live Groq runs (`python scripts/demo_recommend.py --live`) keep the same restaurant facts and swap in model-written prose.

---

## Sample 1 — Indiranagar / medium / Italian

**Preferences:** `min_rating=4.0`, soft: `family-friendly, quiet ambience`, `top_k=3`

| Rank | Name | Cuisine | Rating | Cost | Location |
|---|---|---|---|---|---|
| 1 | Tea Brew | Cafe, Continental, Momos, Italian, North Indian | 4.1 | ₹500 for two | Indiranagar |

**Summary:** Top 1 medium-budget Italian picks near Indiranagar (dry-run / mock explanations).

**Meta:** candidates considered = 1 · filters applied = location, cuisine, budget, min_rating · not relaxed

**Explanation (mock):** Matches your medium budget and Italian preference in Indiranagar rating 4.1 … Also considers: family-friendly, quiet ambience.

---

## Sample 2 — Koramangala / low / South Indian (relaxed)

**Preferences:** `min_rating=4.0`, soft: `quick service`, `top_k=3`

| Rank | Name | Cuisine | Rating | Cost | Location |
|---|---|---|---|---|---|
| 1 | Aligarh House | North Indian, Biryani, Awadhi, Mughlai | 4.4 | ₹400 for two | Koramangala |

**Meta:** candidates = 1 · **relaxed** cuisine → budget (location kept)

Shows the transparency path when hard filters find nothing: constraints drop in order **cuisine → budget → min_rating**, never location.

---

## Sample 3 — Bangalore / high / Japanese, Sushi

**Preferences:** `min_rating=4.2`, soft: `great for a date night`, `top_k=3`

| Rank | Name | Cuisine | Rating | Cost | Location |
|---|---|---|---|---|---|
| 1 | Hammered | North Indian, Thai, Japanese, Continental, Cafe | 4.7 | ₹1,300 for two | Cunningham Road |
| 2 | You Mee | Sushi, Japanese, Chinese, Thai | 4.7 | ₹2,000 for two | Whitefield |
| 3 | The Fatty Bao - Asian Gastro Bar | Japanese, Sushi, Asian | 4.6 | ₹1,200 for two | Indiranagar |

**Meta:** candidates considered = 32 (capped before LLM) · filters applied = location, cuisine, budget, min_rating

City-level `Bangalore` matches all neighborhoods in the store.

---

## Related fixtures

Machine-readable prompt/response samples used by tests:

- [`tests/fixtures/candidates.json`](../tests/fixtures/candidates.json)
- [`tests/fixtures/sample_llm_response.json`](../tests/fixtures/sample_llm_response.json)
- [`docs/llm-samples.md`](llm-samples.md)
