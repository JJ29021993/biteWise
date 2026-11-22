"""Parse and validate LLM recommendation responses (Phase 3)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from src.llm.models import ParsedLLMResponse, ParsedRecommendationItem

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(
    r"```(?:json)?\s*(.*?)\s*```",
    re.DOTALL | re.IGNORECASE,
)
_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")


class ParseError(ValueError):
    """Raised when model output cannot be recovered into structured JSON."""


def _strip_fences(text: str) -> str:
    match = _FENCE_RE.search(text)
    if match:
        return match.group(1).strip()
    return text.strip()


def _extract_json_object(text: str) -> str:
    """Pull the outermost JSON object/array from prose-wrapped content."""
    stripped = text.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        return stripped

    start_obj = stripped.find("{")
    start_arr = stripped.find("[")
    if start_obj < 0 and start_arr < 0:
        raise ParseError("No JSON object or array found in model output.")

    if start_obj < 0:
        start = start_arr
        open_ch, close_ch = "[", "]"
    elif start_arr < 0 or start_obj < start_arr:
        start = start_obj
        open_ch, close_ch = "{", "}"
    else:
        start = start_arr
        open_ch, close_ch = "[", "]"

    depth = 0
    in_string = False
    escape = False
    for idx in range(start, len(stripped)):
        ch = stripped[idx]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return stripped[start : idx + 1]
    raise ParseError("Unbalanced JSON brackets in model output.")


def _close_truncated_json(payload: str) -> str:
    """
    Best-effort repair when the model hits max_tokens mid-JSON.

    Closes an open string, drops a dangling trailing comma, then closes
    any remaining { / [ brackets.
    """
    text = payload.rstrip()
    in_string = False
    escape = False
    stack: list[str] = []

    for ch in text:
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch in "{[":
            stack.append(ch)
        elif ch in "}]" and stack:
            opener = stack[-1]
            if (opener == "{" and ch == "}") or (opener == "[" and ch == "]"):
                stack.pop()

    if in_string:
        text += '"'

    text = text.rstrip()
    if text.endswith(","):
        text = text[:-1].rstrip()

    # Drop a dangling `"key":` / `"key": ` with no value after truncation.
    text = re.sub(r',?\s*"[^"\\]*(?:\\.[^"\\]*)*"\s*:\s*$', "", text)

    closers = {"{": "}", "[": "]"}
    while stack:
        text += closers[stack.pop()]
    return text


def _loads_with_repair(payload: str) -> Any:
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        repaired = _TRAILING_COMMA_RE.sub(r"\1", payload)
        # Common LLM slip: single quotes around keys/strings.
        if "'" in repaired and '"' not in repaired:
            repaired = repaired.replace("'", '"')
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            truncated = _close_truncated_json(repaired)
            try:
                return json.loads(truncated)
            except json.JSONDecodeError as exc:
                raise ParseError(f"Malformed JSON: {exc}") from exc


def extract_json_payload(text: str) -> Any:
    """Recover a Python object from raw / fenced / prose-wrapped model text."""
    if text is None or not str(text).strip():
        raise ParseError("Empty model output.")
    cleaned = _strip_fences(str(text))
    # Truncated replies may never reach a closing brace — take from first "{"/"[".
    try:
        candidate = _extract_json_object(cleaned)
    except ParseError:
        stripped = cleaned.strip()
        start_obj = stripped.find("{")
        start_arr = stripped.find("[")
        starts = [i for i in (start_obj, start_arr) if i >= 0]
        if not starts:
            raise
        candidate = stripped[min(starts) :]
    return _loads_with_repair(candidate)


def _coerce_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_explanation(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    # Soft length guard for UI (R12)
    if len(text) > 800:
        return text[:797].rstrip() + "..."
    return text


def _normalize_items(raw: Any) -> list[ParsedRecommendationItem]:
    if raw is None:
        return []
    if isinstance(raw, dict):
        # Sometimes models wrap a single item as an object.
        raw = [raw]
    if not isinstance(raw, list):
        raise ParseError("'recommendations' must be a list.")

    items: list[ParsedRecommendationItem] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if name is not None:
            name = str(name).strip() or None
        items.append(
            ParsedRecommendationItem(
                restaurant_id=_coerce_int(entry.get("restaurant_id")),
                name=name,
                rank=_coerce_int(entry.get("rank")),
                explanation=_coerce_explanation(entry.get("explanation")),
            )
        )
    return items


class ResponseParser:
    """Convert raw model text into a ParsedLLMResponse."""

    def parse(self, text: str) -> ParsedLLMResponse:
        payload = extract_json_payload(text)

        # Accept either a top-level object or a bare recommendations array.
        if isinstance(payload, list):
            return ParsedLLMResponse(
                summary=None,
                recommendations=_normalize_items(payload),
                raw_json={"recommendations": payload},
            )
        if not isinstance(payload, dict):
            raise ParseError("Top-level JSON must be an object or array.")

        summary = payload.get("summary")
        if summary is not None:
            summary = str(summary).strip() or None
            if summary and len(summary) > 600:
                summary = summary[:597].rstrip() + "..."

        recommendations = _normalize_items(
            payload.get("recommendations")
            or payload.get("results")
            or payload.get("restaurants")
        )
        return ParsedLLMResponse(
            summary=summary,
            recommendations=recommendations,
            raw_json=payload,
        )


def parse_response(text: str) -> ParsedLLMResponse:
    """Convenience wrapper around ResponseParser.parse."""
    return ResponseParser().parse(text)
