"""Groq LLM client (OpenAI-compatible) with retries and mock mode (Phase 3)."""

from __future__ import annotations

import logging
import time
from typing import Any, Protocol, Sequence

from src.config import Settings, get_settings
from src.llm.models import BuiltPrompt, PromptMessage

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    """Raised when the LLM provider call fails after retries."""


class LLMClient(Protocol):
    """Provider-agnostic completion interface."""

    def complete(
        self,
        messages: Sequence[PromptMessage | dict[str, str]] | BuiltPrompt,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Return raw assistant text for a chat completion."""


def _normalize_messages(
    messages: Sequence[PromptMessage | dict[str, str]] | BuiltPrompt,
) -> list[dict[str, str]]:
    if isinstance(messages, BuiltPrompt):
        return messages.as_openai_messages()
    normalized: list[dict[str, str]] = []
    for item in messages:
        if isinstance(item, PromptMessage):
            normalized.append({"role": item.role, "content": item.content})
        else:
            normalized.append({"role": str(item["role"]), "content": str(item["content"])})
    return normalized


class MockLLMClient:
    """Deterministic client for tests / dry-run without API spend."""

    def __init__(self, response_text: str | None = None) -> None:
        self.response_text = response_text
        self.calls: list[list[dict[str, str]]] = []

    def complete(
        self,
        messages: Sequence[PromptMessage | dict[str, str]] | BuiltPrompt,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        del temperature, max_tokens
        normalized = _normalize_messages(messages)
        self.calls.append(normalized)
        if self.response_text is not None:
            return self.response_text
        # Minimal valid JSON so parsers can exercise the happy path in mock mode.
        return (
            '{"summary": "Mock shortlist based on your filters.",'
            ' "recommendations": []}'
        )


class GroqLLMClient:
    """
    Chat completions against Groq's OpenAI-compatible API.

    Uses the official `openai` Python SDK with base_url pointed at Groq.
    """

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        client: Any | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.api_key = api_key if api_key is not None else self.settings.llm_api_key
        self.base_url = base_url or self.settings.llm_base_url
        self.model = model or self.settings.llm_model
        self._client = client

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self.api_key:
            raise LLMError("Missing Groq API key (set GROQ_API_KEY or LLM_API_KEY).")
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - env dependent
            raise LLMError(
                "The openai package is required for Groq. Install with: pip install -e \".[llm]\""
            ) from exc
        self._client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.settings.llm_timeout_seconds,
        )
        return self._client

    def complete(
        self,
        messages: Sequence[PromptMessage | dict[str, str]] | BuiltPrompt,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        normalized = _normalize_messages(messages)
        temp = self.settings.llm_temperature if temperature is None else temperature
        tokens = self.settings.llm_max_tokens if max_tokens is None else max_tokens
        # Groq converts temperature 0 to 1e-8; keep a tiny positive floor for stability.
        if temp <= 0:
            temp = 1e-8

        max_attempts = self.settings.llm_max_retries + 1
        last_error: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                client = self._get_client()
                # Note: openai/gpt-oss-* on Groq often rejects response_format=
                # json_object ("Failed to validate JSON") even for simple prompts.
                # PromptBuilder already asks for JSON; ResponseParser recovers it.
                response = client.chat.completions.create(
                    model=self.model,
                    messages=normalized,
                    temperature=temp,
                    max_tokens=tokens,
                )
                content = response.choices[0].message.content
                if content is None or not str(content).strip():
                    raise LLMError("LLM returned empty content.")
                return str(content)
            except LLMError:
                raise
            except Exception as exc:  # noqa: BLE001 - normalize provider errors
                last_error = exc
                retryable = _is_retryable(exc)
                logger.warning(
                    "Groq LLM call failed (attempt %s/%s, retryable=%s): %s",
                    attempt,
                    max_attempts,
                    retryable,
                    type(exc).__name__,
                )
                if not retryable or attempt >= max_attempts:
                    break
                time.sleep(min(2 ** (attempt - 1), 4))

        raise LLMError(
            f"Groq LLM request failed after {max_attempts} attempt(s): "
            f"{type(last_error).__name__ if last_error else 'unknown'}"
        ) from last_error


def _is_retryable(exc: Exception) -> bool:
    """Best-effort classification of transient provider failures."""
    name = type(exc).__name__.lower()
    message = str(exc).lower()
    if any(token in name for token in ("timeout", "ratelimit", "apiconnection", "internal")):
        return True
    # Prefer whole-phrase / status checks — avoid matching substrings like
    # "rate" inside "generate".
    retry_phrases = (
        "rate limit",
        "rate_limit",
        "too many requests",
        "429",
        "timeout",
        "timed out",
        "503",
        "502",
        "500",
        "overloaded",
        "temporarily unavailable",
        "connection error",
        "connection reset",
    )
    return any(token in message for token in retry_phrases)


def create_llm_client(
    *,
    settings: Settings | None = None,
    mock_response: str | None = None,
) -> LLMClient:
    """
    Factory: mock client when LLM_MOCK_MODE / missing key, else Groq client.
    """
    settings = settings or get_settings()
    if settings.llm_mock_mode or mock_response is not None:
        return MockLLMClient(response_text=mock_response)
    if not settings.llm_api_key:
        logger.info("No Groq API key configured; using MockLLMClient.")
        return MockLLMClient()
    return GroqLLMClient(settings=settings)


def complete(
    messages: Sequence[PromptMessage | dict[str, str]] | BuiltPrompt,
    *,
    settings: Settings | None = None,
    client: LLMClient | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    """Call the configured LLM provider (convenience wrapper)."""
    llm = client or create_llm_client(settings=settings)
    return llm.complete(messages, temperature=temperature, max_tokens=max_tokens)
