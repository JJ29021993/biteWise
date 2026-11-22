"""Dataset-backed filter choices for the Streamlit UI."""

from __future__ import annotations

from functools import lru_cache

import pandas as pd

from src.config import Settings, get_settings
from src.ingestion.preprocess import load_processed_dataframe

CITY_OPTION = "Bangalore"
DEFAULT_LOCATION = "Indiranagar"


@lru_cache(maxsize=1)
def _cached_frame_signature(settings_key: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Load unique locations and cuisine tokens from the processed store."""
    # settings_key keeps cache stable when Settings identity changes but paths match.
    settings = get_settings()
    df = load_processed_dataframe(settings)
    return _extract_options(df)


def _extract_options(df: pd.DataFrame) -> tuple[tuple[str, ...], tuple[str, ...]]:
    locations = sorted(
        {
            str(v).strip()
            for v in df["location"].dropna().tolist()
            if str(v).strip()
        },
        key=str.casefold,
    )
    # City-wide search is a first-class option (matches all neighborhoods).
    if CITY_OPTION not in locations:
        locations = [CITY_OPTION, *locations]
    else:
        locations = [CITY_OPTION, *[loc for loc in locations if loc != CITY_OPTION]]

    cuisine_tokens: set[str] = set()
    if "cuisine_tokens" in df.columns:
        for tokens in df["cuisine_tokens"].dropna().tolist():
            # Parquet often restores list columns as numpy.ndarray, not list/tuple.
            if isinstance(tokens, str):
                iterable = [part.strip() for part in tokens.split(",") if part.strip()]
            elif hasattr(tokens, "__iter__"):
                iterable = tokens
            else:
                continue
            for token in iterable:
                text = str(token).strip()
                if text and text.casefold() not in {"nan", "none", "null"}:
                    cuisine_tokens.add(text)
    elif "cuisines" in df.columns:
        for raw in df["cuisines"].dropna().tolist():
            for part in str(raw).split(","):
                text = part.strip()
                if text:
                    cuisine_tokens.add(text)

    cuisines = tuple(sorted(cuisine_tokens, key=str.casefold))
    return tuple(locations), cuisines


def clear_options_cache() -> None:
    """Drop cached location/cuisine choices (tests / after re-ingestion)."""
    _cached_frame_signature.cache_clear()


def get_location_options(*, settings: Settings | None = None) -> list[str]:
    settings = settings or get_settings()
    key = str(settings.data_processed_dir.resolve())
    return list(_cached_frame_signature(key)[0])


def get_cuisine_options(*, settings: Settings | None = None) -> list[str]:
    settings = settings or get_settings()
    key = str(settings.data_processed_dir.resolve())
    return list(_cached_frame_signature(key)[1])


def default_location_index(locations: list[str]) -> int:
    for preferred in (DEFAULT_LOCATION, CITY_OPTION):
        for i, loc in enumerate(locations):
            if loc.casefold() == preferred.casefold():
                return i
    return 0
