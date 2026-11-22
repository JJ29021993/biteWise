"""Clean raw Zomato rows and persist the processed restaurant store.

Usage:
    python -m src.ingestion.preprocess
    python -m src.ingestion
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.config import Settings, get_settings
from src.ingestion.columns import (
    BUDGET_META_FILENAME,
    PROCESSED_COLUMNS,
    PROCESSED_FILENAME,
)
from src.ingestion.load_dataset import load_raw_dataframe, validate_raw_schema

logger = logging.getLogger(__name__)

# Dataset is Bangalore-centric Zomato listings.
DEFAULT_CITY = "Bangalore"

_NON_NUMERIC_RATING = re.compile(r"^(new|-|nan|none|null)?$", re.IGNORECASE)
_COST_CLEAN = re.compile(r"[^\d.]")


def processed_path(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    return settings.data_processed_dir / PROCESSED_FILENAME


def budget_meta_path(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    return settings.data_processed_dir / BUDGET_META_FILENAME


def _normalize_text(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    return re.sub(r"\s+", " ", text)


def _normalize_location(value: Any) -> str | None:
    """Trim/collapse whitespace and title-case without turning '5th' into '5Th'."""
    text = _normalize_text(value)
    if not text:
        return None
    parts: list[str] = []
    for word in text.casefold().split(" "):
        if not word:
            continue
        parts.append(word[:1].upper() + word[1:])
    return " ".join(parts)


def parse_rating(value: Any) -> float | None:
    """Parse values like '4.1/5', 'NEW', '-', blank → float or None (D04)."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        rating = float(value)
        return rating if 0.0 <= rating <= 5.0 else None

    text = str(value).strip()
    if not text or _NON_NUMERIC_RATING.match(text):
        return None

    if "/" in text:
        text = text.split("/", 1)[0].strip()

    try:
        rating = float(text)
    except ValueError:
        return None
    return rating if 0.0 <= rating <= 5.0 else None


def parse_cost(value: Any) -> float | None:
    """Parse cost strings such as '800', '1,200', '₹1,200' (D05)."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        cost = float(value)
        return cost if cost >= 0 else None

    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None

    cleaned = _COST_CLEAN.sub("", text.replace(",", ""))
    if not cleaned:
        return None
    try:
        cost = float(cleaned)
    except ValueError:
        return None
    return cost if cost >= 0 else None


def tokenize_cuisines(value: Any) -> list[str]:
    """Split multi-cuisine strings into normalized tokens (D06)."""
    text = _normalize_text(value)
    if not text:
        return []
    tokens: list[str] = []
    seen: set[str] = set()
    for part in text.split(","):
        token = part.strip()
        if not token:
            continue
        key = token.casefold()
        if key in seen:
            continue
        seen.add(key)
        tokens.append(token)
    return tokens


def compute_budget_thresholds(
    costs: pd.Series,
    *,
    low_percentile: float = 33.0,
    high_percentile: float = 66.0,
) -> dict[str, float]:
    """
    Derive low/medium/high cut-points from valid costs.

    - budget == low     if cost <= low_max
    - budget == medium  if low_max < cost <= medium_max
    - budget == high    if cost > medium_max
    """
    valid = costs.dropna()
    if valid.empty:
        raise ValueError("Cannot compute budget thresholds: no valid cost values.")

    low_max = float(np.percentile(valid, low_percentile))
    medium_max = float(np.percentile(valid, high_percentile))
    if medium_max < low_max:
        low_max, medium_max = medium_max, low_max
    return {
        "low_max": low_max,
        "medium_max": medium_max,
        "low_percentile": low_percentile,
        "high_percentile": high_percentile,
    }


def assign_budget(cost: float | None, thresholds: dict[str, float]) -> str | None:
    """Map numeric cost to low/medium/high; None if cost unknown."""
    if cost is None or (isinstance(cost, float) and np.isnan(cost)):
        return None
    if cost <= thresholds["low_max"]:
        return "low"
    if cost <= thresholds["medium_max"]:
        return "medium"
    return "high"


def preprocess_dataframe(
    raw: pd.DataFrame,
    *,
    city: str = DEFAULT_CITY,
    thresholds: dict[str, float] | None = None,
    low_percentile: float = 33.0,
    high_percentile: float = 66.0,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Clean and normalize raw HF rows into the processed schema.

    Returns (processed_frame, budget_metadata).
    """
    validate_raw_schema(raw.columns)
    df = raw.copy()

    df["name"] = df["name"].map(_normalize_text)
    df["location"] = df["location"].map(_normalize_location)
    df["cuisines"] = df["cuisines"].map(_normalize_text)
    df["cuisine_tokens"] = df["cuisines"].map(tokenize_cuisines)
    df["rating"] = df["rate"].map(parse_rating)
    df["cost_for_two"] = df["approx_cost(for two people)"].map(parse_cost)

    if "votes" in df.columns:
        df["votes"] = pd.to_numeric(df["votes"], errors="coerce").fillna(0).astype(int)
    else:
        df["votes"] = 0

    for src, dest in (
        ("listed_in(city)", "listed_in_city"),
        ("listed_in(type)", "listed_in_type"),
        ("rest_type", "rest_type"),
        ("online_order", "online_order"),
        ("book_table", "book_table"),
        ("dish_liked", "dish_liked"),
        ("address", "address"),
        ("url", "url"),
    ):
        if src in df.columns:
            df[dest] = df[src].map(_normalize_text)
        else:
            df[dest] = None

    df["city"] = city

    before = len(df)
    df = df[df["name"].notna()].copy()
    dropped_names = before - len(df)
    if dropped_names:
        logger.info("Dropped %s rows with empty restaurant names", dropped_names)

    df = df.sort_values(
        by=["votes", "rating"],
        ascending=[False, False],
        na_position="last",
    )
    df = df.drop_duplicates(subset=["name", "location"], keep="first")

    budget_thresholds = thresholds or compute_budget_thresholds(
        df["cost_for_two"],
        low_percentile=low_percentile,
        high_percentile=high_percentile,
    )
    df["budget"] = df["cost_for_two"].map(
        lambda c: assign_budget(None if pd.isna(c) else float(c), budget_thresholds)
    )

    df = df.reset_index(drop=True)
    df.insert(0, "restaurant_id", df.index.astype(int) + 1)

    processed = df.loc[:, list(PROCESSED_COLUMNS)].copy()

    meta: dict[str, Any] = {
        "city_default": city,
        "row_count": int(len(processed)),
        "budget_thresholds": {
            "low_max": budget_thresholds["low_max"],
            "medium_max": budget_thresholds["medium_max"],
            "low_percentile": budget_thresholds.get("low_percentile", 33.0),
            "high_percentile": budget_thresholds.get("high_percentile", 66.0),
            "mapping": {
                "low": f"cost_for_two <= {budget_thresholds['low_max']}",
                "medium": (
                    f"{budget_thresholds['low_max']} < cost_for_two "
                    f"<= {budget_thresholds['medium_max']}"
                ),
                "high": f"cost_for_two > {budget_thresholds['medium_max']}",
            },
        },
        "null_counts": {
            "rating": int(processed["rating"].isna().sum()),
            "cost_for_two": int(processed["cost_for_two"].isna().sum()),
            "budget": int(processed["budget"].isna().sum()),
            "location": int(processed["location"].isna().sum()),
            "cuisines": int(processed["cuisines"].isna().sum()),
        },
    }
    return processed, meta


def _atomic_write_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        frame.to_parquet(tmp_path, index=False)
        tmp_path.replace(path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise


def _atomic_write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp_path.replace(path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise


def save_processed(
    frame: pd.DataFrame,
    meta: dict[str, Any],
    settings: Settings | None = None,
) -> tuple[Path, Path]:
    """Persist processed Parquet + budget metadata atomically (D12)."""
    settings = settings or get_settings()
    out_path = processed_path(settings)
    meta_path = budget_meta_path(settings)
    _atomic_write_parquet(frame, out_path)
    _atomic_write_json(meta, meta_path)
    logger.info("Wrote processed store (%s rows) → %s", f"{len(frame):,}", out_path)
    logger.info("Wrote budget metadata → %s", meta_path)
    return out_path, meta_path


def load_processed_dataframe(settings: Settings | None = None) -> pd.DataFrame:
    """Load the processed restaurant store for downstream phases."""
    settings = settings or get_settings()
    path = processed_path(settings)
    if not path.exists():
        raise FileNotFoundError(
            f"Processed restaurant store not found at {path}. "
            "Run: python -m src.ingestion"
        )
    try:
        return pd.read_parquet(path)
    except Exception as exc:  # noqa: BLE001 - corrupt artifact (D11)
        raise RuntimeError(
            f"Failed to read processed store at {path}. "
            "Re-run ingestion: python -m src.ingestion"
        ) from exc


def load_budget_metadata(settings: Settings | None = None) -> dict[str, Any]:
    """Load persisted budget threshold metadata."""
    settings = settings or get_settings()
    path = budget_meta_path(settings)
    if not path.exists():
        raise FileNotFoundError(
            f"Budget metadata not found at {path}. Run: python -m src.ingestion"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def preprocess(
    settings: Settings | None = None,
    *,
    force_download: bool = False,
    raw: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Run preprocessing and persist the processed store."""
    settings = settings or get_settings()
    raw_frame = raw if raw is not None else load_raw_dataframe(
        settings, force_download=force_download
    )
    processed, meta = preprocess_dataframe(
        raw_frame,
        city=settings.default_city,
        low_percentile=settings.budget_low_percentile,
        high_percentile=settings.budget_high_percentile,
    )
    save_processed(processed, meta, settings)
    return processed


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = get_settings()
    frame = preprocess(settings)
    meta = load_budget_metadata(settings)
    print(f"Processed rows: {len(frame):,}")
    print(f"Store: {processed_path(settings)}")
    print(f"Budget thresholds: {meta['budget_thresholds']}")


if __name__ == "__main__":
    main()
