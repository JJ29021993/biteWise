# Data Dictionary

Processed restaurant store produced by Phase 1 ingestion.

**Source:** [ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation)  
**Artifacts:**

| File | Path |
|---|---|
| Raw cache | `data/raw/zomato_raw.parquet` |
| Processed store | `data/processed/restaurants.parquet` |
| Budget metadata | `data/processed/budget_thresholds.json` |

Rebuild with:

```powershell
python -m src.ingestion
```

---

## Processed columns

| Column | Type | Description |
|---|---|---|
| `restaurant_id` | int | Stable id within a processed snapshot (1-based) |
| `name` | string | Restaurant name (rows with empty names are dropped) |
| `city` | string | City label for this dataset (`Bangalore`) |
| `location` | string | Neighborhood / area (title-cased) |
| `listed_in_city` | string \| null | Zomato `listed_in(city)` browsing bucket |
| `listed_in_type` | string \| null | Listing type (e.g. Buffet, Cafes, Delivery) |
| `cuisines` | string \| null | Original cuisine string (comma-separated) |
| `cuisine_tokens` | list[string] | Parsed cuisine tokens for filtering |
| `rating` | float \| null | Numeric rating in `[0, 5]`; `NEW` / `-` / blank → null |
| `votes` | int | Review vote count (invalid → 0) |
| `cost_for_two` | float \| null | Approx cost for two people (₹); unparseable → null |
| `budget` | string \| null | `low` \| `medium` \| `high` derived from `cost_for_two` |
| `rest_type` | string \| null | Restaurant type (e.g. Casual Dining, Cafe) |
| `online_order` | string \| null | Whether online ordering is available |
| `book_table` | string \| null | Whether table booking is available |
| `dish_liked` | string \| null | Popular dishes when present |
| `address` | string \| null | Street address |
| `url` | string \| null | Zomato URL |

Dropped from raw (too large / unused for MVP): `reviews_list`, `menu_item`, `phone`.

---

## Budget mapping

Thresholds are computed from the **33rd** and **66th** percentiles of valid `cost_for_two` values in the processed snapshot, then saved to `budget_thresholds.json` for reproducibility.

| Label | Rule |
|---|---|
| `low` | `cost_for_two <= low_max` |
| `medium` | `low_max < cost_for_two <= medium_max` |
| `high` | `cost_for_two > medium_max` |
| `null` | `cost_for_two` missing / unparseable (excluded from hard budget filters in Phase 2) |

Exact `low_max` / `medium_max` values depend on the dataset snapshot; inspect `data/processed/budget_thresholds.json` after ingestion.

---

## Cleaning notes

- Names are required; empty names are dropped
- Locations are trimmed and title-cased (`banashankari` → `Banashankari`)
- Duplicate `(name, location)` rows keep the highest `votes`, then `rating`
- City-level queries should use `city` (`Bangalore`); neighborhood filters use `location`
- `Bangalore` / `Bengaluru` aliases are **not** auto-mapped beyond the fixed `city` label
