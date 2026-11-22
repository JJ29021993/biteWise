"""LLM prompt building, Groq client, parsing, and grounded ranking (Phase 3)."""

from src.llm.client import (
    GroqLLMClient,
    LLMClient,
    LLMError,
    MockLLMClient,
    complete,
    create_llm_client,
)
from src.llm.engine import (
    RecommendationEngine,
    deterministic_rank,
    format_estimated_cost,
    merge_with_candidates,
    rank_candidates,
)
from src.llm.models import (
    BuiltPrompt,
    ParsedLLMResponse,
    ParsedRecommendationItem,
    PromptMessage,
    RankedRecommendation,
    RecommendationEngineResult,
)
from src.llm.parser import ParseError, ResponseParser, parse_response
from src.llm.prompt_builder import PromptBuilder, build_prompt, candidates_to_records

__all__ = [
    "BuiltPrompt",
    "GroqLLMClient",
    "LLMClient",
    "LLMError",
    "MockLLMClient",
    "ParseError",
    "ParsedLLMResponse",
    "ParsedRecommendationItem",
    "PromptBuilder",
    "PromptMessage",
    "RankedRecommendation",
    "RecommendationEngine",
    "RecommendationEngineResult",
    "ResponseParser",
    "build_prompt",
    "candidates_to_records",
    "complete",
    "create_llm_client",
    "deterministic_rank",
    "format_estimated_cost",
    "merge_with_candidates",
    "parse_response",
    "rank_candidates",
]
