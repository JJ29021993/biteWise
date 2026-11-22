"""End-to-end recommendation orchestration (Phase 4).

Pipeline: validate → load store (cached) → filter → LLM rank/explain → map DTOs.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import pandas as pd

from src.config import Settings, get_settings
from src.filtering.preferences import (
    PreferenceValidationError,
    UserPreferences,
    validate_preferences,
)
from src.filtering.restaurant_filter import FilterResult, filter_restaurants
from src.ingestion.preprocess import load_budget_metadata, load_processed_dataframe
from src.llm.client import LLMClient, MockLLMClient, create_llm_client
from src.llm.engine import RecommendationEngine
from src.llm.models import RankedRecommendation
from src.services.models import (
    RecommendationItem,
    RecommendationMeta,
    RecommendationResponse,
)

logger = logging.getLogger(__name__)


def _preferences_public_dict(prefs: UserPreferences) -> dict[str, Any]:
    return {
        "location": prefs.location,
        "budget": prefs.budget,
        "cuisine": prefs.cuisine,
        "min_rating": prefs.min_rating,
        "additional_preferences": prefs.additional_preferences,
        "top_k": prefs.top_k,
    }


def _map_recommendation(item: RankedRecommendation) -> RecommendationItem:
    return RecommendationItem(
        rank=item.rank,
        name=item.name,
        cuisine=item.cuisine,
        rating=item.rating,
        estimated_cost=item.estimated_cost,
        location=item.location,
        explanation=item.explanation,
        restaurant_id=item.restaurant_id,
        budget=item.budget,
        cost_for_two=item.cost_for_two,
    )


def _build_mock_response_text(
    preferences: UserPreferences,
    candidates: pd.DataFrame,
    *,
    top_k: int,
) -> str:
    """Fixture-style JSON so dry_run still yields preference-aware explanations."""
    rows = candidates.head(top_k)
    recs: list[dict[str, Any]] = []
    soft = preferences.additional_preferences
    soft_bit = f" Also considers: {soft}." if soft else ""
    for i, (_, row) in enumerate(rows.iterrows(), start=1):
        name = str(row["name"])
        cuisine = row.get("cuisines") or preferences.cuisine
        rating = row.get("rating")
        rating_bit = f" rating {rating}" if rating is not None and not pd.isna(rating) else ""
        recs.append(
            {
                "restaurant_id": int(row["restaurant_id"]),
                "name": name,
                "rank": i,
                "explanation": (
                    f"Matches your {preferences.budget} budget and "
                    f"{preferences.cuisine} preference in {preferences.location}"
                    f"{rating_bit} ({cuisine}).{soft_bit}"
                ),
            }
        )
    payload = {
        "summary": (
            f"Top {len(recs)} {preferences.budget}-budget "
            f"{preferences.cuisine} picks near {preferences.location} "
            f"(dry-run / mock explanations)."
        ),
        "recommendations": recs,
    }
    return json.dumps(payload, ensure_ascii=False)


class RecommenderService:
    """
    Stateful orchestrator with an in-memory restaurant store cache.

    Use `dry_run=True` (or `LLM_MOCK_MODE=true`) to avoid live Groq spend.
    """

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        client: LLMClient | None = None,
        restaurants: pd.DataFrame | None = None,
        budget_thresholds: dict[str, Any] | None = None,
        dry_run: bool | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._client_override = client
        self._store = restaurants
        self._budget_thresholds = budget_thresholds
        self._dry_run = (
            bool(self.settings.llm_mock_mode) if dry_run is None else bool(dry_run)
        )
        self._engine: RecommendationEngine | None = None

    @property
    def dry_run(self) -> bool:
        return self._dry_run

    def clear_cache(self) -> None:
        """Drop cached store / budget metadata (tests or after re-ingestion)."""
        self._store = None
        self._budget_thresholds = None

    def _get_store(self) -> pd.DataFrame:
        if self._store is None:
            logger.info("Loading processed restaurant store into memory cache.")
            self._store = load_processed_dataframe(self.settings)
            logger.info("Cached restaurant store (%s rows).", f"{len(self._store):,}")
        return self._store

    def _get_budget_thresholds(self) -> dict[str, Any]:
        if self._budget_thresholds is None:
            meta = load_budget_metadata(self.settings)
            self._budget_thresholds = meta["budget_thresholds"]
        return self._budget_thresholds

    def _resolve_client(
        self,
        preferences: UserPreferences,
        candidates: pd.DataFrame,
        *,
        top_k: int,
    ) -> LLMClient:
        if self._client_override is not None:
            return self._client_override
        if self._dry_run:
            return MockLLMClient(
                response_text=_build_mock_response_text(
                    preferences, candidates, top_k=top_k
                )
            )
        return create_llm_client(settings=self.settings)

    def _get_engine(
        self,
        preferences: UserPreferences,
        candidates: pd.DataFrame,
        *,
        top_k: int,
    ) -> RecommendationEngine:
        client = self._resolve_client(preferences, candidates, top_k=top_k)
        # Rebuild when dry_run needs a candidate-specific mock payload.
        if self._dry_run or self._client_override is not None or self._engine is None:
            self._engine = RecommendationEngine(settings=self.settings, client=client)
        return self._engine

    def recommend(
        self,
        preferences: UserPreferences | dict[str, Any] | None = None,
        *,
        dry_run: bool | None = None,
        relax: bool = True,
        **kwargs: Any,
    ) -> RecommendationResponse:
        """
        Run validate → filter → LLM → map.

        Raises PreferenceValidationError for invalid inputs.
        Unexpected pipeline failures are caught and returned in `meta.error`.
        """
        effective_dry_run = self._dry_run if dry_run is None else bool(dry_run)

        try:
            prefs = (
                preferences
                if isinstance(preferences, UserPreferences) and not kwargs
                else validate_preferences(
                    preferences, settings=self.settings, **kwargs
                )
            )
        except PreferenceValidationError:
            raise

        prefs_public = _preferences_public_dict(prefs)

        try:
            store = self._get_store()
            filter_result = filter_restaurants(
                prefs,
                restaurants=store,
                settings=self.settings,
                budget_thresholds=self._get_budget_thresholds(),
                relax=relax,
            )
            return self._rank_filtered(
                filter_result,
                dry_run=effective_dry_run,
                preferences_public=prefs_public,
            )
        except PreferenceValidationError:
            raise
        except Exception as exc:  # noqa: BLE001 - service boundary (S06)
            logger.exception("Recommendation pipeline failed: %s", type(exc).__name__)
            return RecommendationResponse(
                summary=None,
                recommendations=[],
                preferences=prefs_public,
                meta=RecommendationMeta(
                    top_k=prefs.top_k,
                    dry_run=effective_dry_run,
                    error=f"{type(exc).__name__}: pipeline failed",
                    empty_reason="Recommendation pipeline failed.",
                ),
            )

    def _rank_filtered(
        self,
        filter_result: FilterResult,
        *,
        dry_run: bool,
        preferences_public: dict[str, Any],
    ) -> RecommendationResponse:
        prefs = filter_result.preferences
        fmeta = filter_result.meta

        base_meta = RecommendationMeta(
            candidates_considered=fmeta.candidates_considered,
            candidates_before_cap=fmeta.candidates_before_cap,
            filters_requested=list(fmeta.filters_requested),
            filters_applied=list(fmeta.filters_applied),
            filters_relaxed=list(fmeta.filters_relaxed),
            relaxed=fmeta.relaxed,
            top_k=prefs.top_k,
            candidate_cap=fmeta.candidate_cap,
            budget_range=fmeta.budget_range,
            empty_reason=fmeta.empty_reason,
            dry_run=dry_run,
        )

        logger.info(
            "Filter complete: considered=%s before_cap=%s applied=%s relaxed=%s empty=%s",
            fmeta.candidates_considered,
            fmeta.candidates_before_cap,
            fmeta.filters_applied,
            fmeta.filters_relaxed,
            filter_result.is_empty,
        )

        # S02: never call the LLM with an empty candidate set.
        if filter_result.is_empty:
            return RecommendationResponse(
                summary=None,
                recommendations=[],
                preferences=preferences_public,
                meta=base_meta,
            )

        # Temporarily honor per-call dry_run without mutating service default forever
        # when recommend(dry_run=...) differs from self._dry_run.
        previous_dry = self._dry_run
        self._dry_run = dry_run
        try:
            engine = self._get_engine(
                prefs,
                filter_result.candidates,
                top_k=prefs.top_k,
            )
            ranked = engine.rank(prefs, filter_result.candidates, top_k=prefs.top_k)
        finally:
            self._dry_run = previous_dry

        logger.info(
            "LLM rank complete: returned=%s fallback=%s dry_run=%s",
            len(ranked.recommendations),
            ranked.llm_fallback,
            dry_run,
        )
        if ranked.llm_error:
            logger.warning("LLM path note: %s", ranked.llm_error)

        base_meta.llm_fallback = ranked.llm_fallback
        base_meta.llm_error = ranked.llm_error
        # Dry-run is intentional mock usage, not an API failure.
        if dry_run and not ranked.llm_fallback:
            base_meta.llm_error = base_meta.llm_error or None

        return RecommendationResponse(
            summary=ranked.summary,
            recommendations=[_map_recommendation(r) for r in ranked.recommendations],
            preferences=preferences_public,
            meta=base_meta,
        )


# Module-level singleton for simple scripts / UI (lazy store load).
_default_service: RecommenderService | None = None


def get_recommender_service(
    *,
    settings: Settings | None = None,
    refresh: bool = False,
    dry_run: bool | None = None,
) -> RecommenderService:
    """Return a process-wide RecommenderService (cached store)."""
    global _default_service
    if refresh or _default_service is None:
        _default_service = RecommenderService(settings=settings, dry_run=dry_run)
    elif dry_run is not None:
        _default_service._dry_run = bool(dry_run)
    return _default_service


def recommend(
    preferences: UserPreferences | dict[str, Any] | None = None,
    *,
    settings: Settings | None = None,
    client: LLMClient | None = None,
    restaurants: pd.DataFrame | None = None,
    budget_thresholds: dict[str, Any] | None = None,
    dry_run: bool | None = None,
    relax: bool = True,
    **kwargs: Any,
) -> RecommendationResponse:
    """
    Convenience entry: validate → filter → Groq LLM → response DTOs.

    Pass dry_run=True for offline / no-API demos.
    """
    if (
        client is not None
        or restaurants is not None
        or budget_thresholds is not None
        or settings is not None
    ):
        service = RecommenderService(
            settings=settings,
            client=client,
            restaurants=restaurants,
            budget_thresholds=budget_thresholds,
            dry_run=dry_run,
        )
        return service.recommend(preferences, dry_run=dry_run, relax=relax, **kwargs)

    service = get_recommender_service(settings=settings, dry_run=dry_run)
    return service.recommend(preferences, dry_run=dry_run, relax=relax, **kwargs)
