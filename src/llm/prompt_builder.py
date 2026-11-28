"""Build grounded LLM prompts from preferences and candidates (Phase 3)."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from src.filtering.preferences import UserPreferences
from src.llm.models import BuiltPrompt, PromptMessage

SYSTEM_INSTRUCTIONS = """You are a restaurant recommendation assistant.
Rank and explain restaurants ONLY from the provided candidate list.
Do NOT invent restaurants, names, ratings, costs, cuisines, or locations.
Do NOT overwrite factual fields from the candidate data.
Hard filters already applied by the system take priority over soft preferences.
If soft preferences conflict with hard filters, note the tension briefly but still recommend from the given candidates.
Personalize every summary and explanation to this user's filters: location, budget, cuisine, minimum rating, and additional_preferences when they sent any.
Say why this specific restaurant fits that combination. Do not write a generic "highly rated" or "great choice" line.
Use the candidate's real cuisine, rating, cost, and location when you connect it to their filters.
If they set a minimum rating, say whether this rating clears it. If they set a budget, say how the cost sits in that budget. Name their location and cuisine.
When additional_preferences are present, connect them only to fields that are actually in the candidate data. Do not invent ambience, service speed, or menu items.
Keep each explanation to 1-2 short sentences.
Respond with a single JSON object only — no markdown fences, no prose outside JSON."""

OUTPUT_SCHEMA_HINT = """Required JSON shape:
{
  "summary": "optional short overview of the shortlist",
  "recommendations": [
    {
      "restaurant_id": <int from candidates>,
      "name": "<exact name from candidates>",
      "rank": <1-based integer>,
      "explanation": "<1-2 short sentences why this fits>"
    }
  ]
}
Rules:
- Include at most top_k recommendations.
- Prefer restaurant_id for identity; name must match a candidate exactly when used.
- Only recommend restaurants present in candidates.
- Rank 1 = best fit.
- Keep the JSON compact so it finishes completely."""

CANDIDATE_COLUMNS: tuple[str, ...] = (
    "restaurant_id",
    "name",
    "location",
    "cuisines",
    "rating",
    "cost_for_two",
    "budget",
    "votes",
    "rest_type",
)


def _json_safe(value: Any) -> Any:
    """Convert numpy / pandas scalars to plain Python JSON types."""
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except (ValueError, AttributeError):
            pass
    if pd.isna(value):
        return None
    return value


def candidates_to_records(candidates: pd.DataFrame) -> list[dict[str, Any]]:
    """Serialize candidate rows to compact JSON-friendly dicts."""
    if candidates.empty:
        return []

    cols = [c for c in CANDIDATE_COLUMNS if c in candidates.columns]
    records: list[dict[str, Any]] = []
    for row in candidates[cols].to_dict(orient="records"):
        clean = {key: _json_safe(val) for key, val in row.items()}
        records.append(clean)
    return records


def preferences_to_prompt_dict(preferences: UserPreferences) -> dict[str, Any]:
    """Normalized preference block for the user message."""
    return {
        "location": preferences.location,
        "budget": preferences.budget,
        "cuisine": preferences.cuisine,
        "cuisine_list": list(preferences.cuisine_list),
        "min_rating": preferences.min_rating,
        "additional_preferences": preferences.additional_preferences,
        "top_k": preferences.top_k,
    }


class PromptBuilder:
    """Convert preferences + candidates into a grounded chat prompt."""

    def build(
        self,
        preferences: UserPreferences,
        candidates: pd.DataFrame,
        *,
        top_k: int | None = None,
    ) -> BuiltPrompt:
        if candidates is None or candidates.empty:
            raise ValueError("Cannot build prompt with an empty candidate set.")

        k = top_k if top_k is not None else preferences.top_k
        k = max(1, min(int(k), len(candidates)))

        prefs_block = preferences_to_prompt_dict(preferences)
        prefs_block["top_k"] = k
        candidate_records = candidates_to_records(candidates)

        soft = preferences.additional_preferences
        soft_section = (
            f"\nSoft preferences (interpret only; do not invent restaurants):\n{soft}\n"
            if soft
            else "\nSoft preferences: none\n"
        )

        user_content = (
            "User preferences (JSON):\n"
            f"{json.dumps(prefs_block, ensure_ascii=False, indent=2)}\n"
            f"{soft_section}\n"
            f"Candidate restaurants ({len(candidate_records)} items, JSON array):\n"
            f"{json.dumps(candidate_records, ensure_ascii=False, indent=2)}\n\n"
            f"Return at most {k} recommendations.\n"
            f"{OUTPUT_SCHEMA_HINT}"
        )

        messages = [
            PromptMessage(role="system", content=SYSTEM_INSTRUCTIONS),
            PromptMessage(role="user", content=user_content),
        ]
        return BuiltPrompt(messages=messages, candidate_count=len(candidate_records), top_k=k)


def build_prompt(
    preferences: UserPreferences,
    candidates: pd.DataFrame,
    *,
    top_k: int | None = None,
) -> BuiltPrompt:
    """Convenience wrapper around PromptBuilder.build."""
    return PromptBuilder().build(preferences, candidates, top_k=top_k)
