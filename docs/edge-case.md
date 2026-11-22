# Edge Cases & Corner Scenarios

## AI-Powered Restaurant Recommendation System (Zomato Use Case)

Catalog of edge cases and corner scenarios derived from `architecture.md` and `implementation-plan.md`. Use this during implementation, testing (Phase 7), and UI/API error design.

**Conventions**

| Severity | Meaning |
|---|---|
| **P0** | Must handle; incorrect behavior breaks core demo trust |
| **P1** | Should handle; poor UX or degraded but recoverable path |
| **P2** | Nice to handle; rare or polish-level |

| Expected stance | Meaning |
|---|---|
| Reject | Validation fails; clear user/API error |
| Normalize | Coerce input and continue |
| Degrade | Continue with fallback (relaxed filters / deterministic rank / no explanations) |
| Empty | Return zero results with transparent `meta` |
| Ignore | Drop invalid model content; keep grounded facts |

---

## 1. Data Ingestion & Store

| ID | Scenario | Severity | Expected behavior |
|---|---|---|---|
| D01 | Hugging Face dataset download fails (network / 401 / rate limit) | P0 | Fail with actionable error; do not write a partial corrupt processed file |
| D02 | Dataset schema differs from expected column names | P0 | Fail fast with missing-column report; do not silently map wrong fields |
| D03 | Rows with null/empty restaurant name | P0 | Drop or quarantine; never surface nameless recommendations |
| D04 | Null, empty, or non-numeric rating (`NEW`, `-`, `nan`, blank) | P0 | Coerce to null and exclude from rating filters, or apply documented default; never crash on compare |
| D05 | Null / missing cost or cost as string with currency symbols (`₹1,200`) | P0 | Parse robustly; rows that cannot be cost-parsed excluded from budget filter or tagged unbudgeted |
| D06 | Cuisine stored as multi-value string (`"Italian, North Indian"`) vs list | P0 | Normalize to searchable tokens; cuisine filter must match any token |
| D07 | Duplicate restaurant rows (same name + location) | P1 | Deduplicate or keep highest-confidence row; avoid identical cards in results |
| D08 | Extreme cost outliers skewing percentile budget buckets | P1 | Use robust thresholds (winsorize / fixed bins); document mapping |
| D09 | Location spelling variants (`Bangalore` vs `Bengaluru`, case/whitespace) | P0 | Normalize case/trim; document whether aliases are supported |
| D10 | Processed artifact missing on first app start | P0 | Clear message to run ingestion; optional auto-ingest if configured |
| D11 | Corrupt / truncated Parquet or CSV in `data/processed/` | P0 | Detect load failure; refuse to serve stale empty recommendations |
| D12 | Re-running ingestion with changed cleaning rules | P1 | Overwrite processed store atomically; version or timestamp if needed |
| D13 | Very large dataset causing slow in-memory load | P1 | Persist efficiently; cache after first load; avoid reloading per request |
| D14 | Unexpected extra columns / unused fields | P2 | Ignore safely; keep only selected schema |

---

## 2. Preference Validation & Normalization

| ID | Scenario | Severity | Expected behavior |
|---|---|---|---|
| P01 | Missing required fields (no location / no cuisine) | P0 | Reject or apply documented defaults; never call LLM with undefined hard filters silently |
| P02 | Empty strings / whitespace-only preferences | P0 | Treat as missing; normalize or reject |
| P03 | Unknown budget value (`"rich"`, `"500"`, typo) | P0 | Reject with allowed values (`low` \| `medium` \| `high`) |
| P04 | Budget sent with wrong type / case (`"Medium"`, `1`) | P1 | Normalize case; reject non-enum types |
| P05 | `min_rating` below 0 or above 5 | P0 | Clamp to valid range or reject |
| P06 | `min_rating` as string (`"4.5"`) or null | P1 | Coerce when safe; else reject |
| P07 | `top_k` = 0, negative, or extremely large (e.g. 10_000) | P0 | Reject 0/negative; clamp to max (e.g. ≤ candidate cap) |
| P08 | Location not present in dataset (e.g. `"Atlantis"`) | P0 | Empty or relaxed path; message that no restaurants matched location |
| P09 | Cuisine not present in dataset (e.g. `"Martian"`) | P0 | Empty or cuisine-relaxation path with `meta` flag |
| P10 | Conflicting prefs (high `min_rating` + very low budget + rare cuisine) | P0 | Likely zero hard matches → run defined relaxation order |
| P11 | Additional preferences empty vs omitted | P2 | Treat equivalently; omit soft block from prompt if blank |
| P12 | Extremely long additional preferences (thousands of chars) | P1 | Truncate with limit; protect prompt size / cost |
| P13 | Additional preferences with prompt-injection text (“ignore previous instructions…”) | P0 | Keep as untrusted user text only; system prompt remains authoritative; never execute as code |
| P14 | Unicode / emoji / non-English free text in preferences | P1 | Accept; do not crash encoding; LLM may soft-interpret |
| P15 | Special characters in location/cuisine (`O'Brien`, `&`, `/`) | P1 | Safe filtering; no injection into SQL/paths if store is SQLite |
| P16 | Multiple cuisines requested (`"Italian, Chinese"`) | P1 | Define semantics: OR vs AND; document and test |
| P17 | Partial cuisine match (`"China"` vs `"Chinese"`) | P1 | Decide contains/fuzzy/canonical map; avoid false positives |

---

## 3. Filtering & Candidate Caps

| ID | Scenario | Severity | Expected behavior |
|---|---|---|---|
| F01 | Zero candidates after all hard filters | P0 | Relax in documented order (e.g. cuisine → budget → rating); set `meta.relaxed`; if still empty → Empty response |
| F02 | Relaxation still yields zero rows | P0 | Return empty recommendations + clear reason; **do not** call LLM with empty candidate list |
| F03 | Exactly 1 candidate | P0 | Still allow LLM explain or deterministic single result; `top_k` capped to 1 |
| F04 | Candidates fewer than `top_k` | P0 | Return all available; do not pad with invented restaurants |
| F05 | Candidates exceed cap (e.g. > 50) | P0 | Pre-rank/truncate (rating then cost or similar) before prompt |
| F06 | Location match is substring-ambiguous (`"North"` matching many areas) | P1 | Prefer normalized exact/alias match; document contains behavior |
| F07 | Cuisine filter case sensitivity | P0 | Case-insensitive match |
| F08 | Budget boundary values (cost exactly on threshold) | P0 | Inclusive bounds documented; unit-test edges |
| F09 | Restaurants with rating equal to `min_rating` | P0 | Include (`≥`) |
| F10 | All candidates identical on ranking keys | P1 | Stable secondary sort (name/id) for deterministic fallback |
| F11 | Filter on unbudgeted rows (cost unknown) | P1 | Exclude from budget-constrained queries unless policy says otherwise |
| F12 | Meta must reflect which filters were applied vs relaxed | P0 | UI/API consumers rely on this for transparency |
| F13 | Concurrent filter requests while store reloads | P2 | Use immutable snapshot / lock; avoid torn reads |

---

## 4. Prompt Building

| ID | Scenario | Severity | Expected behavior |
|---|---|---|---|
| B01 | Candidate payload too large for model context | P0 | Enforce candidate cap; compact JSON; fail loudly if still oversized |
| B02 | Candidate fields contain quotes/newlines breaking JSON in prompt | P0 | Serialize via proper JSON encoding |
| B03 | Missing optional restaurant fields in candidates | P1 | Omit or null; prompt schema still valid |
| B04 | Soft preferences contradict hard filters (“cheap” while budget=`high`) | P1 | Hard filters win; LLM may note tension in explanation |
| B05 | Prompt accidentally omits anti-hallucination instruction | P0 | Treat as implementation bug; tests must assert instruction present |
| B06 | Requesting more ranks than candidates provided | P0 | Instruct model to return ≤ N candidates; enforce in mapper |

---

## 5. LLM Client & Provider Failures

| ID | Scenario | Severity | Expected behavior |
|---|---|---|---|
| L01 | Missing / invalid API key | P0 | Degrade to deterministic ranking; flag explanations unavailable; UI message |
| L02 | Rate limit / 429 from provider | P0 | Retry with backoff; then Degrade |
| L03 | Timeout / network error | P0 | Retry limited times; then Degrade |
| L04 | Provider 5xx / outage | P0 | Degrade; do not hang UI indefinitely |
| L05 | Model returns empty content | P0 | Treat as parse failure → Degrade |
| L06 | Unexpected model refusal / safety block | P1 | Degrade; log reason category without leaking full prompt secrets |
| L07 | Very high latency | P1 | UI loading state; optional client timeout aligned with server |
| L08 | Mock / dry-run mode enabled | P0 | No live API calls; deterministic or fixture explanations |
| L09 | Cost explosion from repeated large prompts | P1 | Cap candidates, max tokens, and request rate |

---

## 6. LLM Response Parsing & Grounding

| ID | Scenario | Severity | Expected behavior |
|---|---|---|---|
| R01 | Valid JSON matching schema | P0 | Parse and continue |
| R02 | Markdown-fenced JSON (` ```json ... ``` `) | P0 | Strip fences and parse |
| R03 | JSON embedded in prose | P1 | Extract first valid object/array when possible; else Degrade |
| R04 | Malformed JSON (trailing commas, single quotes) | P1 | Best-effort repair or Degrade |
| R05 | Model invents restaurants not in candidate set | P0 | **Ignore** invents; merge only names/ids present in store |
| R06 | Model overwrites rating/cost/cuisine with wrong facts | P0 | Dataset facts always win in mapper |
| R07 | Duplicate ranks or missing rank numbers | P1 | Reassign stable ranks after merge |
| R08 | Returns more than `top_k` items | P0 | Truncate to `top_k` |
| R09 | Returns fewer than available / requested | P1 | Keep returned grounded items; optionally backfill from deterministic order |
| R10 | Empty `explanation` strings | P1 | Allow; UI shows fallback text (“Recommended based on your filters”) |
| R11 | Missing `summary` | P2 | Optional; omit section in UI |
| R12 | Explanations in wrong language or overly long | P2 | Truncate for UI; do not fail pipeline |
| R13 | Model returns restaurants with fuzzy name mismatch (`"Trattoria X "` vs `"Trattoria X"`) | P0 | Normalize matching (trim/case); unmatched → Ignore |
| R14 | Model includes chain-of-thought / extra keys | P2 | Ignore unknown keys; require required fields only |
| R15 | Partial list where some items grounded and some not | P0 | Keep grounded subset only |

---

## 7. Service Orchestration & Response Mapping

| ID | Scenario | Severity | Expected behavior |
|---|---|---|---|
| S01 | Processed store not loaded / first request cold start | P0 | Lazy-load once; subsequent requests use cache |
| S02 | Filter empty → must short-circuit before LLM | P0 | No LLM spend; Empty response with reason |
| S03 | LLM degrade path still returns restaurant facts | P0 | Ranked list without AI explanations; `meta.llm_fallback=true` (or equivalent) |
| S04 | `top_k` greater than grounded parsed items | P0 | Return available count only |
| S05 | Logging includes API keys or full prompts with sensitive prefs | P0 | Redact secrets; avoid logging full prompts in default config |
| S06 | Exception in mid-pipeline | P0 | Catch at service boundary; return controlled error to UI/API |
| S07 | Parallel identical requests | P2 | Safe; shared read-only store; no cross-request mutation |
| S08 | Config defaults missing (model name, caps) | P1 | Sensible defaults or fail at startup |

---

## 8. User Interface

| ID | Scenario | Severity | Expected behavior |
|---|---|---|---|
| U01 | Submit with empty required fields | P0 | Inline validation; block submit |
| U02 | User clicks submit repeatedly while request in flight | P0 | Disable button / debounce; one in-flight recommendation |
| U03 | Long LLM wait | P0 | Loading indicator; no blank freeze without feedback |
| U04 | Empty recommendation set | P0 | Friendly empty state + suggestion to loosen filters |
| U05 | Relaxed filters used | P1 | Show notice that some criteria were relaxed |
| U06 | LLM fallback (no explanations) | P1 | Show results + note that AI explanations unavailable |
| U07 | Service/API error | P0 | User-readable error; app remains usable for next try |
| U08 | Very long explanation text | P2 | Clamp visually (expand/collapse optional) |
| U09 | Mobile narrow viewport | P1 | Inputs and result list remain usable |
| U10 | Browser refresh mid-request | P2 | No corrupt local state; fresh form OK |
| U11 | Display cost/rating formatting edge values | P1 | Consistent formatting; handle missing display fields gracefully |

---

## 9. API Layer (Optional Phase 6)

| ID | Scenario | Severity | Expected behavior |
|---|---|---|---|
| A01 | Invalid JSON body | P0 | 400 with clear validation error |
| A02 | Extra unknown fields | P1 | Ignore or reject per schema policy (document choice) |
| A03 | Wrong content type | P1 | 415/400 |
| A04 | Missing auth if later added | P2 | Out of current scope; if added, 401 |
| A05 | High request volume / abuse | P1 | Basic rate limit if publicly deployed |
| A06 | CORS from unexpected origins | P1 | Configure allowed origins explicitly |
| A07 | Health check when data store missing | P1 | Health degraded/unready until store loadable |
| A08 | Response contract drift vs UI expectations | P0 | Shared DTO/schema; integration test |

---

## 10. Cross-Cutting: Security, Privacy, Ops

| ID | Scenario | Severity | Expected behavior |
|---|---|---|---|
| X01 | `.env` / API key committed to git | P0 | Prevent via `.gitignore`; rotate key if leaked |
| X02 | Path traversal via crafted location if used in file I/O | P0 | Preferences never become filesystem paths |
| X03 | Free-text prefs used in `eval` / shell / SQL string concat | P0 | Never; parameterized queries / DataFrame filters only |
| X04 | PII-like text typed into additional preferences | P1 | Do not log by default; treat as untrusted content |
| X05 | Disk full while writing processed data | P1 | Fail ingestion cleanly; keep previous good artifact if present |
| X06 | Clock / timezone irrelevant assumptions in ranking | P2 | No time-based restaurant availability in scope |

---

## 11. End-to-End Corner Journeys

These combine multiple layers; prioritize as integration tests.

| ID | Journey | Expected outcome |
|---|---|---|
| E01 | Rare cuisine + high rating + low budget in a real city | Relaxation and/or empty; never hallucinated fillers |
| E02 | Popular city + common cuisine → huge match set | Candidate cap applied; LLM sees bounded list; UI shows `top_k` |
| E03 | Valid filters but LLM down | Deterministic top restaurants, facts intact, fallback flag |
| E04 | Valid filters, LLM returns invented #1 restaurant | Invented row dropped; remaining grounded ranks shown |
| E05 | User asks for `top_k=5` but only 2 candidates exist | Exactly 2 results; no padding |
| E06 | User soft-pref “vegan” with no vegan column in data | Soft preference in prompt only; no false hard filter crash |
| E07 | Mock mode demo without API key | Full UI path works with non-LLM or fixture explanations |
| E08 | Fresh clone, no processed data, user opens UI first | Guided error to run ingestion (or auto-run once) |
| E09 | Prompt-injection in additional preferences + normal filters | Still only ranks provided candidates; facts unchanged |
| E10 | Location alias mismatch (`Bengaluru` vs dataset `Bangalore`) | Empty/poor match unless alias map exists — document limitation |

---

## 12. Explicit Non-Edge Cases (Out of Scope)

Do not invent handling for these within current scope:

- Live table availability / “restaurant closed now”
- Payment, cart, or order failures
- Multi-user accounts / session personalization history (unless later added)
- Training-serving skew of a custom ML model
- Real-time menu price changes beyond dataset snapshot

---

## 13. Recommended Test Mapping

| Area | Minimum edge IDs to cover in automated tests |
|---|---|
| Ingestion | D03–D07, D09, D11 |
| Preferences | P01–P07, P12–P13, P16 |
| Filtering | F01–F05, F07–F09, F12 |
| Prompt | B01–B02, B05–B06 |
| LLM client | L01–L05, L08 |
| Parser / grounding | R02, R05–R08, R13, R15 |
| Service | S02–S04, S06 |
| UI (manual or smoke) | U01–U07 |
| API (if built) | A01, A08 |
| E2E | E01–E05, E07, E09 |

---

## 14. Handling Priority Cheat Sheet

**Never acceptable in a “working” demo**

- Invented restaurants shown as real results (R05, E04)
- Crash on null ratings/costs (D04, D05)
- LLM called with zero candidates (F02, S02)
- Secrets in logs or git (X01, S05)
- Silent failure with blank UI (U03, U07)

**Acceptable degraded modes**

- Relaxed filters with disclosure (F01, U05)
- Deterministic ranking without explanations (L01–L04, S03, U06)
- Fewer than `top_k` results when data is sparse (F04, E05)

---

## 15. Maintenance

When behavior changes (new relaxation order, new budget bins, new parser rules):

1. Update the matching row in this file
2. Add/adjust tests listed in §13
3. Mirror user-visible behavior in UI copy and `architecture.md` if contracts change
