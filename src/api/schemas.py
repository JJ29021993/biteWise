"""Pydantic request/response models for the REST API (Phase 6).

Aligned with architecture.md §3.2 and Phase 4 RecommendationResponse DTOs.
Unknown fields are rejected (extra=forbid) so invalid payloads return clear 4xx.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

BudgetLabel = Literal["low", "medium", "high"]


class RecommendationRequest(BaseModel):
    """POST /api/recommendations body — public preference fields only."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "location": "Indiranagar",
                    "budget": "medium",
                    "cuisine": "Italian",
                    "min_rating": 4.0,
                    "additional_preferences": "family-friendly, quiet ambience",
                    "top_k": 5,
                    "dry_run": True,
                }
            ]
        },
    )

    location: str = Field(..., min_length=1, description="City or neighborhood")
    budget: BudgetLabel
    cuisine: str | None = Field(
        default=None,
        description="Optional cuisine name or comma-separated list (OR match). "
        "Omit or leave empty to match any cuisine.",
    )
    min_rating: float = Field(default=0.0, ge=0.0, le=5.0)
    additional_preferences: str | None = Field(
        default=None,
        description="Soft free-text preferences for the LLM (not hard-filtered).",
    )
    top_k: int = Field(default=5, ge=1, description="Number of recommendations to return")
    dry_run: bool | None = Field(
        default=None,
        description="If true, skip live LLM calls (mock explanations). "
        "Omit to use server default / LLM_MOCK_MODE.",
    )


class RecommendationItemOut(BaseModel):
    """One grounded restaurant recommendation."""

    model_config = ConfigDict(extra="forbid")

    rank: int
    name: str
    cuisine: str | None = None
    rating: float | None = None
    estimated_cost: str | None = None
    location: str | None = None
    explanation: str
    restaurant_id: int | None = None
    budget: str | None = None
    cost_for_two: float | None = None


class RecommendationMetaOut(BaseModel):
    """Transparency + operational flags."""

    model_config = ConfigDict(extra="forbid")

    candidates_considered: int = 0
    candidates_before_cap: int = 0
    filters_requested: list[str] = Field(default_factory=list)
    filters_applied: list[str] = Field(default_factory=list)
    filters_relaxed: list[str] = Field(default_factory=list)
    relaxed: bool = False
    top_k: int = 0
    candidate_cap: int = 0
    budget_range: dict[str, Any] | None = None
    empty_reason: str | None = None
    llm_fallback: bool = False
    llm_error: str | None = None
    dry_run: bool = False
    error: str | None = None


class RecommendationResponseOut(BaseModel):
    """Stable recommendation payload matching architecture contracts."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "summary": "Here are the best mid-budget Italian picks…",
                    "recommendations": [
                        {
                            "rank": 1,
                            "name": "Trattoria X",
                            "cuisine": "Italian",
                            "rating": 4.5,
                            "estimated_cost": "₹1,200 for two",
                            "location": "Indiranagar",
                            "explanation": "Matches your budget and rating bar.",
                        }
                    ],
                    "meta": {
                        "candidates_considered": 24,
                        "filters_applied": [
                            "location",
                            "budget",
                            "cuisine",
                            "min_rating",
                        ],
                    },
                    "preferences": {
                        "location": "Indiranagar",
                        "budget": "medium",
                        "cuisine": "Italian",
                        "min_rating": 4.0,
                        "additional_preferences": None,
                        "top_k": 5,
                    },
                }
            ]
        },
    )

    summary: str | None = None
    recommendations: list[RecommendationItemOut]
    meta: RecommendationMetaOut
    preferences: dict[str, Any] | None = None


class HealthResponse(BaseModel):
    """Liveness / readiness for uptime checks."""

    status: Literal["ok", "degraded"]
    store_ready: bool
    store_path: str
    dry_run_default: bool
    detail: str | None = None


class OptionsResponse(BaseModel):
    """Dataset-backed filter choices for the web UI."""

    model_config = ConfigDict(extra="forbid")

    locations: list[str]
    cuisines: list[str]
    default_location: str


class ErrorResponse(BaseModel):
    """Machine-readable error body for 4xx responses."""

    detail: str | list[Any]
