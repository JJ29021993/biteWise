"""Rank filtered candidates via Groq LLM with grounded merge + fallback (Phase 3)."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from src.config import Settings, get_settings
from src.filtering.preferences import UserPreferences
from src.llm.client import LLMClient, LLMError, create_llm_client
from src.llm.models import (
    ParsedLLMResponse,
    ParsedRecommendationItem,
    RankedRecommendation,
    RecommendationEngineResult,
)
from src.llm.parser import ParseError, ResponseParser
from src.llm.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)

FALLBACK_EXPLANATION = "Recommended based on your filters."
DEFAULT_EXPLANATION_EMPTY = FALLBACK_EXPLANATION


def format_estimated_cost(cost_for_two: Any) -> str | None:
    """Human-readable cost string from numeric cost_for_two."""
    if cost_for_two is None or (isinstance(cost_for_two, float) and pd.isna(cost_for_two)):
        return None
    try:
        value = float(cost_for_two)
    except (TypeError, ValueError):
        return None
    if pd.isna(value):
        return None
    # Indian Rupee formatting without requiring locale.
    rounded = int(round(value))
    return f"₹{rounded:,} for two"


def _row_to_recommendation(
    row: pd.Series,
    *,
    rank: int,
    explanation: str,
) -> RankedRecommendation:
    cost = row.get("cost_for_two")
    if cost is not None and isinstance(cost, float) and pd.isna(cost):
        cost = None
    rating = row.get("rating")
    if rating is not None and isinstance(rating, float) and pd.isna(rating):
        rating = None
    votes = row.get("votes", 0)
    try:
        votes_int = int(votes) if votes is not None and not pd.isna(votes) else 0
    except (TypeError, ValueError):
        votes_int = 0

    cuisine = row.get("cuisines")
    if cuisine is not None and not isinstance(cuisine, str):
        cuisine = None if pd.isna(cuisine) else str(cuisine)

    return RankedRecommendation(
        rank=rank,
        restaurant_id=int(row["restaurant_id"]),
        name=str(row["name"]),
        cuisine=cuisine,
        rating=float(rating) if rating is not None else None,
        estimated_cost=format_estimated_cost(cost),
        cost_for_two=float(cost) if cost is not None else None,
        location=None if row.get("location") is None or pd.isna(row.get("location")) else str(row["location"]),
        budget=None if row.get("budget") is None or pd.isna(row.get("budget")) else str(row["budget"]),
        explanation=explanation or DEFAULT_EXPLANATION_EMPTY,
        votes=votes_int,
        rest_type=None
        if row.get("rest_type") is None or pd.isna(row.get("rest_type"))
        else str(row["rest_type"]),
    )


def _normalize_name(name: str | None) -> str:
    if not name:
        return ""
    return " ".join(str(name).casefold().split())


def _index_candidates(candidates: pd.DataFrame) -> tuple[dict[int, pd.Series], dict[str, pd.Series]]:
    by_id: dict[int, pd.Series] = {}
    by_name: dict[str, pd.Series] = {}
    for _, row in candidates.iterrows():
        rid = int(row["restaurant_id"])
        by_id[rid] = row
        key = _normalize_name(str(row["name"]))
        # First occurrence wins for duplicate names (stable).
        by_name.setdefault(key, row)
    return by_id, by_name


def _resolve_candidate(
    item: ParsedRecommendationItem,
    by_id: dict[int, pd.Series],
    by_name: dict[str, pd.Series],
) -> pd.Series | None:
    if item.restaurant_id is not None and item.restaurant_id in by_id:
        return by_id[item.restaurant_id]
    key = _normalize_name(item.name)
    if key and key in by_name:
        return by_name[key]
    return None


def merge_with_candidates(
    parsed: ParsedLLMResponse,
    candidates: pd.DataFrame,
    *,
    top_k: int,
    backfill: bool = True,
) -> tuple[list[RankedRecommendation], str | None]:
    """
    Merge LLM ranks/explanations onto dataset facts.

    Dataset fields always win. Hallucinated names/ids are ignored (R05, R06).
    """
    if candidates.empty or top_k < 1:
        return [], parsed.summary

    by_id, by_name = _index_candidates(candidates)
    used_ids: set[int] = set()
    used_names: set[str] = set()
    merged: list[RankedRecommendation] = []

    # Sort by provided rank when present; preserve relative order otherwise.
    ordered = sorted(
        enumerate(parsed.recommendations),
        key=lambda pair: (
            pair[1].rank is None,
            pair[1].rank if pair[1].rank is not None else 10**9,
            pair[0],
        ),
    )

    for _, item in ordered:
        if len(merged) >= top_k:
            break
        row = _resolve_candidate(item, by_id, by_name)
        if row is None:
            continue
        rid = int(row["restaurant_id"])
        name_key = _normalize_name(str(row["name"]))
        if rid in used_ids or (name_key and name_key in used_names):
            continue
        used_ids.add(rid)
        if name_key:
            used_names.add(name_key)
        merged.append(
            _row_to_recommendation(
                row,
                rank=len(merged) + 1,
                explanation=item.explanation or DEFAULT_EXPLANATION_EMPTY,
            )
        )

    if backfill and len(merged) < top_k:
        for _, row in _deterministic_order(candidates).iterrows():
            if len(merged) >= top_k:
                break
            rid = int(row["restaurant_id"])
            name_key = _normalize_name(str(row["name"]))
            if rid in used_ids or (name_key and name_key in used_names):
                continue
            used_ids.add(rid)
            if name_key:
                used_names.add(name_key)
            merged.append(
                _row_to_recommendation(
                    row,
                    rank=len(merged) + 1,
                    explanation=DEFAULT_EXPLANATION_EMPTY,
                )
            )

    return merged, parsed.summary


def _deterministic_order(candidates: pd.DataFrame) -> pd.DataFrame:
    """Fallback ranking: rating desc, cost asc, votes desc, name/id stable."""
    df = candidates.copy()
    sort_cols = [c for c in ("rating", "cost_for_two", "votes", "name", "restaurant_id") if c in df.columns]
    ascending = []
    for col in sort_cols:
        if col == "rating" or col == "votes":
            ascending.append(False)
        elif col == "cost_for_two":
            ascending.append(True)
        else:
            ascending.append(True)
    return df.sort_values(by=sort_cols, ascending=ascending, na_position="last")


def deterministic_rank(
    candidates: pd.DataFrame,
    *,
    top_k: int,
    summary: str | None = None,
) -> RecommendationEngineResult:
    """Deterministic ranking when the LLM is unavailable or unparseable."""
    k = max(0, min(top_k, len(candidates)))
    ranked_df = _deterministic_order(candidates).head(k)
    recommendations = [
        _row_to_recommendation(row, rank=i + 1, explanation=FALLBACK_EXPLANATION)
        for i, (_, row) in enumerate(ranked_df.iterrows())
    ]
    return RecommendationEngineResult(
        summary=summary,
        recommendations=recommendations,
        llm_fallback=True,
        candidates_considered=len(candidates),
        top_k=top_k,
    )


class RecommendationEngine:
    """
    Phase 3 engine: build prompt → Groq complete → parse → merge-with-store.

    Falls back to deterministic ranking on missing key / API / parse failures.
    """

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        client: LLMClient | None = None,
        prompt_builder: PromptBuilder | None = None,
        parser: ResponseParser | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client = client or create_llm_client(settings=self.settings)
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.parser = parser or ResponseParser()

    def rank(
        self,
        preferences: UserPreferences,
        candidates: pd.DataFrame,
        *,
        top_k: int | None = None,
    ) -> RecommendationEngineResult:
        if candidates is None or candidates.empty:
            return RecommendationEngineResult(
                summary=None,
                recommendations=[],
                llm_fallback=False,
                llm_error="No candidates to rank.",
                candidates_considered=0,
                top_k=preferences.top_k if top_k is None else top_k,
            )

        k = top_k if top_k is not None else preferences.top_k
        k = max(1, min(int(k), len(candidates)))

        try:
            prompt = self.prompt_builder.build(preferences, candidates, top_k=k)
            raw = self.client.complete(prompt)
            parsed = self.parser.parse(raw)
            recommendations, summary = merge_with_candidates(
                parsed, candidates, top_k=k, backfill=True
            )
            if not recommendations:
                # Parsed OK but nothing grounded → degrade.
                result = deterministic_rank(candidates, top_k=k, summary=summary)
                result.llm_error = "No grounded recommendations in LLM output."
                return result
            return RecommendationEngineResult(
                summary=summary,
                recommendations=recommendations,
                llm_fallback=False,
                candidates_considered=len(candidates),
                top_k=k,
            )
        except (LLMError, ParseError, ValueError) as exc:
            logger.warning("LLM ranking degraded to deterministic fallback: %s", type(exc).__name__)
            result = deterministic_rank(candidates, top_k=k)
            result.llm_error = str(exc)
            return result


def rank_candidates(
    preferences: UserPreferences,
    candidates: pd.DataFrame,
    *,
    settings: Settings | None = None,
    client: LLMClient | None = None,
    top_k: int | None = None,
) -> RecommendationEngineResult:
    """Convenience entry point for Phase 3 ranking."""
    engine = RecommendationEngine(settings=settings, client=client)
    return engine.rank(preferences, candidates, top_k=top_k)
