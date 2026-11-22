"""Deterministic restaurant filtering with relaxation and metadata (Phase 2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

import pandas as pd

from src.config import Settings, get_settings
from src.filtering.preferences import UserPreferences, validate_preferences
from src.ingestion.preprocess import load_budget_metadata, load_processed_dataframe

# Relaxation order from architecture / implementation plan:
# drop cuisine → drop budget → drop min_rating. Location is never relaxed.
RELAXATION_ORDER: tuple[str, ...] = ("cuisine", "budget", "min_rating")


@dataclass(frozen=True)
class BudgetRange:
    """Inclusive numeric cost bounds for a budget label."""

    label: str
    min_cost: float | None
    max_cost: float | None

    def contains(self, cost: float) -> bool:
        if self.min_cost is not None and cost < self.min_cost:
            return False
        if self.max_cost is not None and cost > self.max_cost:
            return False
        return True


@dataclass
class FilterMeta:
    filters_requested: list[str] = field(default_factory=list)
    filters_applied: list[str] = field(default_factory=list)
    filters_relaxed: list[str] = field(default_factory=list)
    relaxed: bool = False
    candidates_before_cap: int = 0
    candidates_considered: int = 0
    candidate_cap: int = 0
    top_k: int = 0
    budget_range: dict[str, float | None] | None = None
    empty_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "filters_requested": list(self.filters_requested),
            "filters_applied": list(self.filters_applied),
            "filters_relaxed": list(self.filters_relaxed),
            "relaxed": self.relaxed,
            "candidates_before_cap": self.candidates_before_cap,
            "candidates_considered": self.candidates_considered,
            "candidate_cap": self.candidate_cap,
            "top_k": self.top_k,
            "budget_range": self.budget_range,
            "empty_reason": self.empty_reason,
        }


@dataclass
class FilterResult:
    """Bounded candidate set plus transparency metadata."""

    candidates: pd.DataFrame
    preferences: UserPreferences
    meta: FilterMeta

    @property
    def is_empty(self) -> bool:
        return self.candidates.empty


def budget_label_to_range(
    label: str,
    thresholds: dict[str, Any] | None = None,
    *,
    settings: Settings | None = None,
) -> BudgetRange:
    """
    Map budget label → inclusive cost range using Phase 1 thresholds.

    Threshold schema (from budget_thresholds.json):
      low_max, medium_max
    Mapping:
      low:    cost <= low_max
      medium: low_max < cost <= medium_max
      high:   cost > medium_max
    """
    settings = settings or get_settings()
    if thresholds is None:
        meta = load_budget_metadata(settings)
        thresholds = meta["budget_thresholds"]

    low_max = float(thresholds["low_max"])
    medium_max = float(thresholds["medium_max"])
    label_key = label.casefold()

    if label_key == "low":
        return BudgetRange(label="low", min_cost=None, max_cost=low_max)
    if label_key == "medium":
        # Exclusive of low_max on the lower side in assign_budget; for filtering
        # use a tiny epsilon via strict > low_max implemented in mask logic.
        return BudgetRange(label="medium", min_cost=low_max, max_cost=medium_max)
    if label_key == "high":
        return BudgetRange(label="high", min_cost=medium_max, max_cost=None)
    raise ValueError(f"Unknown budget label: {label}")


def _mask_location(df: pd.DataFrame, prefs: UserPreferences) -> pd.Series:
    """
    Location matching policy:
    - City-level query (Bangalore / Bengaluru / BLR): match `city`
    - Otherwise: case-insensitive exact match on `location` OR `listed_in_city`
      (no substring match — avoids ambiguous hits like 'North')
    """
    if prefs.is_city_level_location:
        city_key = prefs.location_normalized
        return df["city"].fillna("").map(lambda v: str(v).casefold() == city_key)

    needle = prefs.location.casefold()
    loc = df["location"].fillna("").map(lambda v: str(v).casefold() == needle)
    listed = df["listed_in_city"].fillna("").map(lambda v: str(v).casefold() == needle)
    return loc | listed


def _shared_prefix_len(left: str, right: str) -> int:
    n = 0
    for a, b in zip(left, right):
        if a != b:
            break
        n += 1
    return n


def _cuisine_token_matches(tokens: Any, requested: Iterable[str]) -> bool:
    """
    Case-insensitive match with OR semantics across requested cuisines (P16).

    Matching rules (P17):
    - Exact token match
    - Substring either way when query length >= 3 ('ital' → 'Italian')
    - Shared prefix length >= 4 ('china' → 'Chinese')
    """
    if tokens is None:
        return False
    try:
        token_list = list(tokens)
    except TypeError:
        return False
    if not token_list:
        return False

    normalized_tokens = [str(t).casefold() for t in token_list if t is not None]
    for req in requested:
        req_key = req.casefold()
        for token in normalized_tokens:
            if req_key == token:
                return True
            if len(req_key) >= 3 and (req_key in token or token in req_key):
                return True
            if _shared_prefix_len(req_key, token) >= 4:
                return True
    return False


def _mask_cuisine(df: pd.DataFrame, prefs: UserPreferences) -> pd.Series:
    return df["cuisine_tokens"].map(
        lambda tokens: _cuisine_token_matches(tokens, prefs.cuisine_list)
    )


def _mask_rating(df: pd.DataFrame, prefs: UserPreferences) -> pd.Series:
    # Rating >= min_rating; null ratings excluded when a positive threshold is set
    ratings = pd.to_numeric(df["rating"], errors="coerce")
    if prefs.min_rating <= 0:
        return pd.Series(True, index=df.index)
    return ratings >= prefs.min_rating


def _mask_budget(df: pd.DataFrame, budget_range: BudgetRange) -> pd.Series:
    """
    Apply cost bounds. Rows with unknown cost are excluded (F11).

    Medium uses exclusive lower bound (cost > low_max) to mirror Phase 1
    assign_budget. High uses exclusive lower bound (cost > medium_max).
    Low / medium upper bounds are inclusive.
    """
    costs = pd.to_numeric(df["cost_for_two"], errors="coerce")
    known = costs.notna()

    if budget_range.label == "low":
        return known & (costs <= budget_range.max_cost)
    if budget_range.label == "medium":
        return known & (costs > budget_range.min_cost) & (costs <= budget_range.max_cost)
    if budget_range.label == "high":
        return known & (costs > budget_range.min_cost)
    return pd.Series(False, index=df.index)


def _sort_candidates(df: pd.DataFrame) -> pd.DataFrame:
    """Deterministic pre-rank before candidate cap (F05, F10)."""
    return df.sort_values(
        by=["rating", "votes", "name", "restaurant_id"],
        ascending=[False, False, True, True],
        na_position="last",
    )


def _dedupe_by_name(df: pd.DataFrame) -> pd.DataFrame:
    """
    Keep one row per restaurant name (case-insensitive).

    Chains appear many times across Bangalore neighborhoods; for recommendations
    we keep the strongest rating/votes instance so listings don't repeat.
    """
    if df.empty or "name" not in df.columns:
        return df
    ranked = _sort_candidates(df)
    keys = ranked["name"].fillna("").map(lambda v: " ".join(str(v).casefold().split()))
    return ranked.loc[~keys.duplicated(keep="first")].copy()


def _apply_filters(
    df: pd.DataFrame,
    prefs: UserPreferences,
    *,
    budget_range: BudgetRange,
    active: set[str],
) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)

    if "location" in active:
        mask &= _mask_location(df, prefs)
    if "cuisine" in active:
        mask &= _mask_cuisine(df, prefs)
    if "budget" in active:
        mask &= _mask_budget(df, budget_range)
    if "min_rating" in active:
        mask &= _mask_rating(df, prefs)

    return df.loc[mask].copy()


def filter_restaurants(
    preferences: UserPreferences | dict[str, Any] | None = None,
    *,
    restaurants: pd.DataFrame | None = None,
    settings: Settings | None = None,
    budget_thresholds: dict[str, Any] | None = None,
    relax: bool = True,
    **kwargs: Any,
) -> FilterResult:
    """
    Apply hard constraints and return a bounded candidate set.

    When `relax=True` and the full filter set is empty, constraints are dropped
    in order: cuisine → budget → min_rating. Location is never relaxed.
    """
    settings = settings or get_settings()
    prefs = (
        preferences
        if isinstance(preferences, UserPreferences) and not kwargs
        else validate_preferences(preferences, settings=settings, **kwargs)
    )

    store = restaurants if restaurants is not None else load_processed_dataframe(settings)
    if store.empty:
        meta = FilterMeta(
            filters_requested=[],
            empty_reason="Processed restaurant store is empty.",
            candidate_cap=settings.candidate_cap,
            top_k=prefs.top_k,
        )
        return FilterResult(candidates=store.copy(), preferences=prefs, meta=meta)

    if budget_thresholds is None:
        budget_thresholds = load_budget_metadata(settings)["budget_thresholds"]
    budget_range = budget_label_to_range(
        prefs.budget, budget_thresholds, settings=settings
    )

    requested = ["location"]
    if prefs.cuisine_list:
        requested.append("cuisine")
    requested.append("budget")
    if prefs.min_rating > 0:
        requested.append("min_rating")

    active = set(requested)
    applied = list(requested)
    relaxed: list[str] = []

    matched = _apply_filters(store, prefs, budget_range=budget_range, active=active)

    if matched.empty and relax:
        for key in RELAXATION_ORDER:
            if key not in active:
                continue
            active.remove(key)
            relaxed.append(key)
            applied = [f for f in requested if f in active]
            matched = _apply_filters(
                store, prefs, budget_range=budget_range, active=active
            )
            if not matched.empty:
                break

    before_cap = len(matched)
    ranked = _dedupe_by_name(matched)
    capped = ranked.head(settings.candidate_cap).reset_index(drop=True)

    empty_reason = None
    if capped.empty:
        if "location" in active and len(active) == 1 and relaxed:
            empty_reason = (
                "No restaurants matched the location "
                "after relaxing cuisine, budget, and rating filters."
            )
        elif not relaxed:
            empty_reason = "No restaurants matched the given preferences."
        else:
            empty_reason = "No restaurants matched the given preferences."

    meta = FilterMeta(
        filters_requested=requested,
        filters_applied=applied if not capped.empty else list(active),
        filters_relaxed=relaxed,
        relaxed=bool(relaxed) and not capped.empty,
        candidates_before_cap=before_cap,
        candidates_considered=len(capped),
        candidate_cap=settings.candidate_cap,
        top_k=prefs.top_k,
        budget_range={
            "label": budget_range.label,
            "min_cost": budget_range.min_cost,
            "max_cost": budget_range.max_cost,
        },
        empty_reason=empty_reason,
    )
    # When empty after full relaxation, filters_applied should reflect what was
    # still active (location only).
    if capped.empty:
        meta.filters_applied = [f for f in requested if f in active]
        meta.relaxed = bool(relaxed)

    return FilterResult(candidates=capped, preferences=prefs, meta=meta)
