"""Canonical column contracts for raw HF data and the processed store."""

from __future__ import annotations

# Required columns from ManikaSaini/zomato-restaurant-recommendation
REQUIRED_RAW_COLUMNS: tuple[str, ...] = (
    "name",
    "location",
    "cuisines",
    "rate",
    "approx_cost(for two people)",
)

OPTIONAL_RAW_COLUMNS: tuple[str, ...] = (
    "address",
    "url",
    "online_order",
    "book_table",
    "votes",
    "rest_type",
    "dish_liked",
    "listed_in(type)",
    "listed_in(city)",
)

# Final processed schema (source of truth for Phase 2+)
PROCESSED_COLUMNS: tuple[str, ...] = (
    "restaurant_id",
    "name",
    "city",
    "location",
    "listed_in_city",
    "listed_in_type",
    "cuisines",
    "cuisine_tokens",
    "rating",
    "votes",
    "cost_for_two",
    "budget",
    "rest_type",
    "online_order",
    "book_table",
    "dish_liked",
    "address",
    "url",
)

RAW_CACHE_FILENAME = "zomato_raw.parquet"
PROCESSED_FILENAME = "restaurants.parquet"
BUDGET_META_FILENAME = "budget_thresholds.json"
