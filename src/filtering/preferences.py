"""User preference models and validation (Phase 2)."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.config import Settings, get_settings

BudgetLabel = Literal["low", "medium", "high"]

ALLOWED_BUDGETS: tuple[BudgetLabel, ...] = ("low", "medium", "high")

# City aliases for this Bangalore-centric dataset snapshot.
LOCATION_ALIASES: dict[str, str] = {
    "bangalore": "bangalore",
    "bengaluru": "bangalore",
    "blr": "bangalore",
}

_WHITESPACE = re.compile(r"\s+")
DEFAULT_ADDITIONAL_PREFS_MAX_CHARS = 500


class PreferenceValidationError(ValueError):
    """Raised when user preferences cannot be normalized."""


class UserPreferences(BaseModel):
    """Validated, normalized preferences used by the filter layer."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    location: str = Field(..., min_length=1, description="City or neighborhood")
    budget: BudgetLabel
    cuisine: str | None = Field(
        default=None,
        description="Optional cuisine name or comma-separated list (OR match).",
    )
    min_rating: float = Field(default=0.0, ge=0.0, le=5.0)
    additional_preferences: str | None = Field(
        default=None,
        description="Soft free-text preferences for the LLM (not hard-filtered).",
    )
    top_k: int = Field(default=5, ge=1)

    # Derived / normalized helpers filled during validation
    cuisine_list: list[str] = Field(default_factory=list)
    location_normalized: str = Field(default="")
    is_city_level_location: bool = Field(default=False)

    @field_validator("location", mode="before")
    @classmethod
    def _blank_location_is_missing(cls, value: Any) -> Any:
        if value is None:
            return value
        if isinstance(value, str) and not value.strip():
            raise PreferenceValidationError("location cannot be blank.")
        return value

    @field_validator("cuisine", mode="before")
    @classmethod
    def _blank_cuisine_is_none(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("budget", mode="before")
    @classmethod
    def _normalize_budget(cls, value: Any) -> str:
        if isinstance(value, str):
            normalized = value.strip().casefold()
            if normalized in ALLOWED_BUDGETS:
                return normalized
            raise PreferenceValidationError(
                f"Invalid budget '{value}'. Allowed: {', '.join(ALLOWED_BUDGETS)}"
            )
        raise PreferenceValidationError(
            f"Invalid budget type {type(value).__name__}. Expected one of: "
            f"{', '.join(ALLOWED_BUDGETS)}"
        )

    @field_validator("min_rating", mode="before")
    @classmethod
    def _coerce_min_rating(cls, value: Any) -> float:
        if value is None or (isinstance(value, str) and not value.strip()):
            return 0.0
        if isinstance(value, bool):
            raise PreferenceValidationError("min_rating must be a number between 0 and 5.")
        try:
            rating = float(value)
        except (TypeError, ValueError) as exc:
            raise PreferenceValidationError(
                f"min_rating must be a number between 0 and 5 (got {value!r})."
            ) from exc
        if rating < 0.0 or rating > 5.0:
            # Clamp into valid range (P05)
            return max(0.0, min(5.0, rating))
        return rating

    @field_validator("top_k", mode="before")
    @classmethod
    def _coerce_top_k(cls, value: Any) -> int:
        if value is None or (isinstance(value, str) and not value.strip()):
            return 5
        try:
            top_k = int(value)
        except (TypeError, ValueError) as exc:
            raise PreferenceValidationError(f"top_k must be an integer (got {value!r}).") from exc
        if top_k < 1:
            raise PreferenceValidationError("top_k must be >= 1.")
        return top_k

    @field_validator("additional_preferences", mode="before")
    @classmethod
    def _normalize_additional(cls, value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        text = _WHITESPACE.sub(" ", value).strip()
        return text or None

    @model_validator(mode="after")
    def _derive_fields(self) -> UserPreferences:
        location = _WHITESPACE.sub(" ", self.location).strip()
        if not location:
            raise PreferenceValidationError("location is required.")

        location_key = location.casefold()
        aliased = LOCATION_ALIASES.get(location_key, location_key)
        is_city = aliased in {city.casefold() for city in ("Bangalore",)} or (
            aliased == "bangalore"
        )

        cuisine_raw = self.cuisine
        if cuisine_raw is None:
            cuisine: str | None = None
            cuisine_list: list[str] = []
        else:
            cuisine = _WHITESPACE.sub(" ", str(cuisine_raw)).strip() or None
            cuisine_list = _parse_cuisine_list(cuisine) if cuisine else []
            if cuisine and not cuisine_list:
                raise PreferenceValidationError("cuisine must include at least one value.")

        additional = self.additional_preferences
        if additional and len(additional) > DEFAULT_ADDITIONAL_PREFS_MAX_CHARS:
            additional = additional[:DEFAULT_ADDITIONAL_PREFS_MAX_CHARS].rstrip()

        self.location = location
        self.cuisine = cuisine
        self.location_normalized = aliased
        self.is_city_level_location = is_city
        self.cuisine_list = cuisine_list
        self.additional_preferences = additional
        return self


def _parse_cuisine_list(cuisine: str) -> list[str]:
    """Split comma-separated cuisines; OR semantics at filter time (P16)."""
    tokens: list[str] = []
    seen: set[str] = set()
    for part in cuisine.split(","):
        token = part.strip()
        if not token:
            continue
        key = token.casefold()
        if key in seen:
            continue
        seen.add(key)
        tokens.append(token)
    return tokens


def validate_preferences(
    payload: UserPreferences | dict[str, Any] | None = None,
    *,
    settings: Settings | None = None,
    **kwargs: Any,
) -> UserPreferences:
    """
    Validate and normalize user preferences.

    Accepts a mapping, keyword args, or an existing UserPreferences instance.
    Clamps top_k to the configured candidate_cap.
    """
    settings = settings or get_settings()

    if payload is None:
        data: dict[str, Any] = dict(kwargs)
    elif isinstance(payload, UserPreferences):
        data = payload.model_dump()
        data.update(kwargs)
    elif isinstance(payload, dict):
        data = {**payload, **kwargs}
    else:
        raise PreferenceValidationError(
            f"Unsupported preferences payload type: {type(payload).__name__}"
        )

    # Apply defaults before model validation
    data.setdefault("min_rating", 0.0)
    data.setdefault("top_k", settings.default_top_k)
    data.setdefault("additional_preferences", None)
    data.setdefault("cuisine", None)

    try:
        prefs = UserPreferences.model_validate(data)
    except PreferenceValidationError:
        raise
    except Exception as exc:  # noqa: BLE001 - normalize pydantic errors
        raise PreferenceValidationError(str(exc)) from exc

    # Clamp top_k to candidate_cap (P07)
    if prefs.top_k > settings.candidate_cap:
        prefs.top_k = settings.candidate_cap

    return prefs
