"""DTOs for Phase 3 LLM ranking and grounded recommendations."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class PromptMessage:
    """Single chat message for the LLM client."""

    role: str
    content: str


@dataclass(frozen=True)
class BuiltPrompt:
    """System + user messages plus compact metadata for logging."""

    messages: list[PromptMessage]
    candidate_count: int
    top_k: int

    def as_openai_messages(self) -> list[dict[str, str]]:
        return [{"role": m.role, "content": m.content} for m in self.messages]


@dataclass
class ParsedRecommendationItem:
    """One item as returned by the model (pre-merge)."""

    restaurant_id: int | None = None
    name: str | None = None
    rank: int | None = None
    explanation: str = ""


@dataclass
class ParsedLLMResponse:
    """Structured parse result from model text."""

    summary: str | None = None
    recommendations: list[ParsedRecommendationItem] = field(default_factory=list)
    raw_json: dict[str, Any] | None = None


@dataclass
class RankedRecommendation:
    """Grounded recommendation: dataset facts + optional LLM explanation."""

    rank: int
    restaurant_id: int
    name: str
    cuisine: str | None
    rating: float | None
    estimated_cost: str | None
    cost_for_two: float | None
    location: str | None
    budget: str | None
    explanation: str
    votes: int = 0
    rest_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RecommendationEngineResult:
    """Output of the Phase 3 ranking engine."""

    summary: str | None
    recommendations: list[RankedRecommendation]
    llm_fallback: bool = False
    llm_error: str | None = None
    candidates_considered: int = 0
    top_k: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "llm_fallback": self.llm_fallback,
            "llm_error": self.llm_error,
            "candidates_considered": self.candidates_considered,
            "top_k": self.top_k,
        }
