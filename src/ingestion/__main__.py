"""CLI entrypoint for the full Phase 1 ingestion pipeline.

Usage:
    python -m src.ingestion
    python -m src.ingestion --force-download
"""

from __future__ import annotations

import argparse
import logging
import time

from src.config import get_settings
from src.ingestion.load_dataset import load_raw_dataframe, raw_cache_path
from src.ingestion.preprocess import (
    load_budget_metadata,
    preprocess_dataframe,
    processed_path,
    save_processed,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download, clean, and persist the Zomato restaurant store.",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Ignore local raw cache and re-download from Hugging Face.",
    )
    return parser


def run(*, force_download: bool = False) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = get_settings()
    started = time.perf_counter()

    raw = load_raw_dataframe(settings, force_download=force_download)
    processed, meta = preprocess_dataframe(
        raw,
        city=settings.default_city,
        low_percentile=settings.budget_low_percentile,
        high_percentile=settings.budget_high_percentile,
    )
    out_path, meta_path = save_processed(processed, meta, settings)

    elapsed = time.perf_counter() - started
    thresholds = load_budget_metadata(settings)["budget_thresholds"]

    print("Ingestion complete")
    print(f"  Raw cache : {raw_cache_path(settings)}")
    print(f"  Processed : {out_path} ({len(processed):,} rows)")
    print(f"  Metadata  : {meta_path}")
    print(
        "  Budget    : "
        f"low <= {thresholds['low_max']}, "
        f"medium <= {thresholds['medium_max']}, "
        "else high"
    )
    print(f"  Elapsed   : {elapsed:.2f}s")
    print(f"  Reload via: {processed_path(settings)}")


def main() -> None:
    args = build_parser().parse_args()
    run(force_download=args.force_download)


if __name__ == "__main__":
    main()
