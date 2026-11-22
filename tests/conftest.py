"""Shared pytest fixtures for Phase 7 core-logic tests (no live LLM required)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.config import Settings
from src.filtering import validate_preferences

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def candidate_rows() -> list[dict]:
    return json.loads((FIXTURES / "candidates.json").read_text(encoding="utf-8"))


@pytest.fixture
def candidate_df(candidate_rows) -> pd.DataFrame:
    return pd.DataFrame(candidate_rows)


@pytest.fixture
def candidate_store(candidate_rows) -> pd.DataFrame:
    """Filter/service-ready frame derived from the LLM candidate fixture."""
    frame = pd.DataFrame(candidate_rows)
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


@pytest.fixture
def sample_prefs():
    return validate_preferences(
        {
            "location": "Indiranagar",
            "budget": "medium",
            "cuisine": "Italian",
            "min_rating": 4.0,
            "additional_preferences": "family-friendly, quiet ambience",
            "top_k": 3,
        }
    )


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        candidate_cap=50,
        default_top_k=5,
        llm_mock_mode=True,
        llm_api_key=None,
    )
