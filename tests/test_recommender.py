"""Unit tests for Phase 4 recommendation orchestration."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.config import Settings
from src.filtering import PreferenceValidationError
from src.llm import LLMError, MockLLMClient
from src.services import RecommenderService, recommend

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def candidate_store() -> pd.DataFrame:
    rows = json.loads((FIXTURES / "candidates.json").read_text(encoding="utf-8"))
    frame = pd.DataFrame(rows)
    frame["city"] = "Bangalore"
    frame["cuisine_tokens"] = frame["cuisines"].map(
        lambda s: [p.strip() for p in str(s).split(",")]
    )
    frame["listed_in_city"] = frame["location"]
    return frame


@pytest.fixture
def budget_thresholds() -> dict:
    # Fixture costs are 900–1200 → medium under these thresholds.
    return {"low_max": 500.0, "medium_max": 1500.0}


@pytest.fixture
def sample_llm_text() -> str:
    return (FIXTURES / "sample_llm_response.json").read_text(encoding="utf-8")


def test_recommend_end_to_end_with_mock_llm(
    candidate_store, budget_thresholds, sample_llm_text
):
    client = MockLLMClient(response_text=sample_llm_text)
    service = RecommenderService(
        settings=Settings(candidate_cap=50, default_top_k=3),
        client=client,
        restaurants=candidate_store,
        budget_thresholds=budget_thresholds,
        dry_run=False,
    )
    result = service.recommend(
        {
            "location": "Indiranagar",
            "budget": "medium",
            "cuisine": "Italian",
            "min_rating": 4.0,
            "additional_preferences": "family-friendly",
            "top_k": 3,
        }
    )
    assert not result.is_empty
    assert result.summary is not None
    assert len(result.recommendations) == 3
    assert result.recommendations[0].name == "Trattoria X"
    assert result.recommendations[0].estimated_cost == "₹1,200 for two"
    assert "family" in result.recommendations[0].explanation.lower()
    assert result.meta.candidates_considered >= 1
    assert "location" in result.meta.filters_applied
    assert result.meta.llm_fallback is False
    assert result.meta.dry_run is False
    assert len(client.calls) == 1
    payload = result.to_dict()
    assert "recommendations" in payload and "meta" in payload


def test_recommend_empty_filter_short_circuits_llm(candidate_store, budget_thresholds):
    client = MockLLMClient(response_text='{"recommendations":[]}')
    service = RecommenderService(
        client=client,
        restaurants=candidate_store,
        budget_thresholds=budget_thresholds,
    )
    result = service.recommend(
        location="Atlantis",
        budget="low",
        cuisine="Martian",
        min_rating=5.0,
        top_k=3,
        relax=False,
    )
    assert result.is_empty
    assert result.meta.empty_reason is not None
    assert client.calls == []


def test_recommend_llm_failure_falls_back(candidate_store, budget_thresholds):
    class Boom:
        def complete(self, messages, *, temperature=None, max_tokens=None):
            raise LLMError("down")

    service = RecommenderService(
        client=Boom(),
        restaurants=candidate_store,
        budget_thresholds=budget_thresholds,
    )
    result = service.recommend(
        location="Indiranagar",
        budget="medium",
        cuisine="Italian",
        min_rating=4.0,
        top_k=2,
    )
    assert len(result.recommendations) == 2
    assert result.meta.llm_fallback is True
    assert result.recommendations[0].name
    assert result.recommendations[0].rating is not None


def test_dry_run_sets_flag_and_returns_recs(candidate_store, budget_thresholds):
    service = RecommenderService(
        restaurants=candidate_store,
        budget_thresholds=budget_thresholds,
        dry_run=True,
    )
    result = service.recommend(
        location="Indiranagar",
        budget="medium",
        cuisine="Italian",
        min_rating=4.0,
        top_k=2,
    )
    assert result.meta.dry_run is True
    assert len(result.recommendations) == 2
    assert result.summary is not None
    assert "Italian" in (result.recommendations[0].explanation or "")


def test_recommend_rejects_invalid_preferences(candidate_store):
    service = RecommenderService(restaurants=candidate_store)
    with pytest.raises(PreferenceValidationError):
        service.recommend(location="Indiranagar", budget="rich", cuisine="Italian")


def test_module_recommend_convenience(
    candidate_store, budget_thresholds, sample_llm_text
):
    result = recommend(
        location="Indiranagar",
        budget="medium",
        cuisine="Italian",
        min_rating=4.0,
        top_k=2,
        client=MockLLMClient(response_text=sample_llm_text),
        restaurants=candidate_store,
        budget_thresholds=budget_thresholds,
    )
    assert len(result.recommendations) == 2
    assert result.recommendations[0].name == "Trattoria X"
    assert "meta" in result.to_dict()


def test_recommend_top_k_larger_than_candidates(
    candidate_store, budget_thresholds, sample_llm_text
):
    """E05: sparse matches return available rows only — no padding."""
    # Keep a single Italian/medium row so top_k=5 cannot be filled.
    slim = candidate_store.iloc[:1].copy()
    service = RecommenderService(
        settings=Settings(candidate_cap=50, default_top_k=5),
        client=MockLLMClient(response_text=sample_llm_text),
        restaurants=slim,
        budget_thresholds=budget_thresholds,
    )
    result = service.recommend(
        location="Indiranagar",
        budget="medium",
        cuisine="Italian",
        min_rating=4.0,
        top_k=5,
    )
    assert len(result.recommendations) == 1
    assert result.recommendations[0].name == "Trattoria X"
    assert result.meta.candidates_considered == 1


def test_recommend_soft_pref_does_not_change_hard_filters(
    candidate_store, budget_thresholds, sample_llm_text
):
    """E06: soft 'vegan' text must not empty or invent hard-filter results."""
    client = MockLLMClient(response_text=sample_llm_text)
    service = RecommenderService(
        client=client,
        restaurants=candidate_store,
        budget_thresholds=budget_thresholds,
    )
    without = service.recommend(
        location="Indiranagar",
        budget="medium",
        cuisine="Italian",
        min_rating=4.0,
        top_k=3,
    )
    with_soft = service.recommend(
        location="Indiranagar",
        budget="medium",
        cuisine="Italian",
        min_rating=4.0,
        additional_preferences="vegan only",
        top_k=3,
    )
    assert [r.name for r in without.recommendations] == [
        r.name for r in with_soft.recommendations
    ]
    assert with_soft.preferences["additional_preferences"] == "vegan only"
    # Soft text reaches the LLM prompt
    assert "vegan only" in client.calls[-1][1]["content"]


def test_recommend_dry_run_without_api_key(candidate_store, budget_thresholds):
    """E07: full pipeline works offline with dry_run / mock mode."""
    service = RecommenderService(
        settings=Settings(llm_api_key=None, llm_mock_mode=False),
        restaurants=candidate_store,
        budget_thresholds=budget_thresholds,
        dry_run=True,
    )
    result = service.recommend(
        location="Indiranagar",
        budget="medium",
        cuisine="Italian",
        min_rating=4.0,
        top_k=2,
    )
    assert result.meta.dry_run is True
    assert len(result.recommendations) == 2
    assert all(r.name for r in result.recommendations)
    assert all(r.rating is not None for r in result.recommendations)
