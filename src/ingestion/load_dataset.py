"""Load the Zomato dataset from Hugging Face and cache a raw local copy.

Usage:
    python -m src.ingestion.load_dataset
    python -m src.ingestion          # full ingest + preprocess pipeline
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from datasets import load_dataset as hf_load_dataset

from src.config import Settings, get_settings
from src.ingestion.columns import OPTIONAL_RAW_COLUMNS, RAW_CACHE_FILENAME, REQUIRED_RAW_COLUMNS

logger = logging.getLogger(__name__)


class DatasetSchemaError(ValueError):
    """Raised when the Hugging Face dataset is missing required columns."""


def raw_cache_path(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    return settings.data_raw_dir / RAW_CACHE_FILENAME


def validate_raw_schema(columns: list[str] | pd.Index) -> None:
    """Fail fast if required columns are missing (edge case D02)."""
    present = set(columns)
    missing = [col for col in REQUIRED_RAW_COLUMNS if col not in present]
    if missing:
        raise DatasetSchemaError(
            "Hugging Face dataset is missing required columns: "
            f"{missing}. Present columns: {sorted(present)}"
        )


def _select_raw_columns(frame: pd.DataFrame) -> pd.DataFrame:
    validate_raw_schema(frame.columns)
    keep = [
        col
        for col in (*REQUIRED_RAW_COLUMNS, *OPTIONAL_RAW_COLUMNS)
        if col in frame.columns
    ]
    return frame.loc[:, keep].copy()


def download_hf_dataset(
    settings: Settings | None = None,
    *,
    split: str = "train",
) -> pd.DataFrame:
    """Download the HF dataset and return a raw pandas DataFrame."""
    settings = settings or get_settings()
    dataset_id = settings.hf_dataset_id
    logger.info("Loading Hugging Face dataset '%s' (split=%s)", dataset_id, split)

    try:
        dataset = hf_load_dataset(dataset_id, split=split)
    except Exception as exc:  # noqa: BLE001 - surface actionable failure (D01)
        raise RuntimeError(
            f"Failed to download Hugging Face dataset '{dataset_id}'. "
            "Check network access and the dataset id, then retry."
        ) from exc

    frame = dataset.to_pandas()
    return _select_raw_columns(frame)


def save_raw_dataframe(frame: pd.DataFrame, path: Path) -> Path:
    """Persist the raw frame atomically as Parquet."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        frame.to_parquet(tmp_path, index=False)
        tmp_path.replace(path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise
    logger.info("Wrote raw cache (%s rows) → %s", f"{len(frame):,}", path)
    return path


def load_raw_dataframe(
    settings: Settings | None = None,
    *,
    force_download: bool = False,
    split: str = "train",
) -> pd.DataFrame:
    """Return raw restaurant rows, using local cache when available."""
    settings = settings or get_settings()
    cache_path = raw_cache_path(settings)

    if cache_path.exists() and not force_download:
        logger.info("Loading raw cache from %s", cache_path)
        frame = pd.read_parquet(cache_path)
        validate_raw_schema(frame.columns)
        return frame

    frame = download_hf_dataset(settings, split=split)
    save_raw_dataframe(frame, cache_path)
    return frame


def load_dataset(
    settings: Settings | None = None,
    *,
    force_download: bool = False,
) -> pd.DataFrame:
    """Public entry: load (and cache) the raw Zomato dataset."""
    return load_raw_dataframe(settings, force_download=force_download)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = get_settings()
    frame = load_dataset(settings)
    print(f"Raw rows: {len(frame):,}")
    print(f"Columns: {list(frame.columns)}")
    print(f"Cache: {raw_cache_path(settings)}")


if __name__ == "__main__":
    main()
