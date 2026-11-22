"""Stable recommendation response DTOs for Phase 4+ (UI / API)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class RecommendationItem:
    """One grounded restaurant recommendation in the public response contract."""

    rank: int
    name: str
    cuisine: str | None
    rating: float | None
    estimated_cost: str | None
    location: str | None
    explanation: str
    restaurant_id: int | None = None
    budget: str | None = None
    cost_for_two: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RecommendationMeta:
    """Transparency + operational flags for a recommendation call."""

    candidates_considered: int = 0
    candidates_before_cap: int = 0
    filters_requested: list[str] = field(default_factory=list)
    filters_applied: list[str] = field(default_factory=list)
    filters_relaxed: list[str] = field(default_factory=list)
    relaxed: bool = False
    top_k: int = 0
    candidate_cap: int = 0
    budget_range: dict[str, Any] | None = None
    empty_reason: str | None = None
    llm_fallback: bool = False
    llm_error: str | None = None
    dry_run: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RecommendationResponse:
    """End-to-end recommend() result matching architecture contracts."""

    summary: str | None
    recommendations: list[RecommendationItem]
    meta: RecommendationMeta
    preferences: dict[str, Any] | None = None

    @property
    def is_empty(self) -> bool:
        return not self.recommendations

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "meta": self.meta.to_dict(),
            "preferences": self.preferences,
        }
