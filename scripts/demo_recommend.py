"""Manual Phase 4 demo: print recommendations for a few preference sets.

Usage:
    python scripts/demo_recommend.py
    python scripts/demo_recommend.py --dry-run
    python scripts/demo_recommend.py --live
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running as a script without installing editable package quirks.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services import recommend  # noqa: E402

SAMPLE_PREFERENCES: list[dict] = [
    {
        "location": "Indiranagar",
        "budget": "medium",
        "cuisine": "Italian",
        "min_rating": 4.0,
        "additional_preferences": "family-friendly, quiet ambience",
        "top_k": 3,
    },
    {
        "location": "Koramangala",
        "budget": "low",
        "cuisine": "South Indian",
        "min_rating": 4.0,
        "additional_preferences": "quick service",
        "top_k": 3,
    },
    {
        "location": "Bangalore",
        "budget": "high",
        "cuisine": "Japanese, Sushi",
        "min_rating": 4.2,
        "additional_preferences": "great for a date night",
        "top_k": 3,
    },
]


def _print_result(label: str, result) -> None:
    print("=" * 72)
    print(label)
    print("-" * 72)
    if result.summary:
        print(f"Summary: {result.summary}")
    print(
        f"Meta: candidates={result.meta.candidates_considered} "
        f"applied={result.meta.filters_applied} "
        f"relaxed={result.meta.filters_relaxed} "
        f"llm_fallback={result.meta.llm_fallback} "
        f"dry_run={result.meta.dry_run}"
    )
    if result.meta.empty_reason:
        print(f"Empty: {result.meta.empty_reason}")
    if result.meta.error:
        print(f"Error: {result.meta.error}")
    for rec in result.recommendations:
        print(
            f"  #{rec.rank} {rec.name} | {rec.cuisine} | "
            f"{rec.rating} | {rec.estimated_cost} | {rec.location}"
        )
        print(f"      {rec.explanation}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Demo Phase 4 recommend() pipeline")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Call Groq with GROQ_API_KEY from .env (default is dry-run / mock LLM)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full JSON payloads instead of a short text view",
    )
    args = parser.parse_args()
    dry_run = not args.live

    print(f"Mode: {'dry-run / mock LLM' if dry_run else 'live Groq'}")
    for i, prefs in enumerate(SAMPLE_PREFERENCES, start=1):
        result = recommend(prefs, dry_run=dry_run)
        label = f"Sample {i}: {prefs['location']} / {prefs['budget']} / {prefs['cuisine']}"
        if args.json:
            print("=" * 72)
            print(label)
            print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
            print()
        else:
            _print_result(label, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
