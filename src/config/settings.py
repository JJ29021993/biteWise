"""Environment-backed application settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Groq OpenAI-compatible endpoint + a strong default chat model.
DEFAULT_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
# llama-3.3-70b-versatile was retired for free/dev tiers (2026-08-16).
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"


class Settings(BaseSettings):
    """Central configuration loaded from environment variables / `.env`."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Paths
    project_root: Path = Field(default=PROJECT_ROOT)
    data_raw_dir: Path = Field(default=PROJECT_ROOT / "data" / "raw")
    data_processed_dir: Path = Field(default=PROJECT_ROOT / "data" / "processed")

    # Dataset
    hf_dataset_id: str = Field(
        default="ManikaSaini/zomato-restaurant-recommendation",
        description="Hugging Face dataset id used in Phase 1 ingestion.",
    )
    default_city: str = Field(
        default="Bangalore",
        description="City label applied to this dataset snapshot.",
    )
    budget_low_percentile: float = Field(default=33.0, ge=0, le=100)
    budget_high_percentile: float = Field(default=66.0, ge=0, le=100)

    # Recommendation defaults (Phase 7 demo defaults)
    default_top_k: int = Field(
        default=5,
        ge=1,
        description="Default shortlist size when the caller omits top_k.",
    )
    candidate_cap: int = Field(
        default=50,
        ge=1,
        description="Max filtered candidates passed to the LLM (cost/latency bound).",
    )

    # LLM (Groq via OpenAI-compatible API)
    llm_provider: str = Field(default="groq", alias="LLM_PROVIDER")
    llm_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GROQ_API_KEY", "LLM_API_KEY"),
        description="Groq API key (GROQ_API_KEY preferred; LLM_API_KEY also accepted).",
    )
    llm_base_url: str = Field(
        default=DEFAULT_GROQ_BASE_URL,
        validation_alias=AliasChoices("GROQ_BASE_URL", "LLM_BASE_URL"),
    )
    llm_model: str = Field(
        default=DEFAULT_GROQ_MODEL,
        validation_alias=AliasChoices("GROQ_MODEL", "LLM_MODEL"),
    )
    llm_temperature: float = Field(default=0.2, alias="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=2048, alias="LLM_MAX_TOKENS")
    llm_timeout_seconds: float = Field(default=45.0, alias="LLM_TIMEOUT_SECONDS")
    llm_max_retries: int = Field(default=2, ge=0, alias="LLM_MAX_RETRIES")
    llm_mock_mode: bool = Field(
        default=False,
        alias="LLM_MOCK_MODE",
        description="When true, skip live LLM calls (deterministic / fixture path).",
    )

    # API (Phase 6)
    api_cors_origins: str = Field(
        default=(
            "http://localhost:3000,http://127.0.0.1:3000,"
            "https://bite-wise-tau.vercel.app"
        ),
        alias="API_CORS_ORIGINS",
        description="Comma-separated allowed CORS origins (* disables credentialed CORS).",
    )
    api_cors_origin_regex: str | None = Field(
        default=r"https://.*\.vercel\.app",
        alias="API_CORS_ORIGIN_REGEX",
        description=(
            "Optional regex for CORS origins (e.g. Vercel preview URLs). "
            "Set empty to disable."
        ),
    )
    api_rate_limit_per_minute: int = Field(
        default=60,
        ge=1,
        alias="API_RATE_LIMIT_PER_MINUTE",
        description="Max requests per client IP per rolling minute (exempt: /health, docs).",
    )
    api_host: str = Field(
        default="127.0.0.1",
        alias="API_HOST",
        description="Bind address. Use 0.0.0.0 in containers / public deploys.",
    )
    api_port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        # Prefer PORT so Railway/Render/Fly routing works even if API_PORT is set in the image.
        validation_alias=AliasChoices("PORT", "API_PORT"),
        description="Listen port. PORT (PaaS) wins over API_PORT when both are set.",
    )
    api_disable_docs: bool = Field(
        default=False,
        alias="API_DISABLE_DOCS",
        description="When true, disable /docs, /redoc, and /openapi.json.",
    )

    @field_validator("llm_api_key", mode="before")
    @classmethod
    def _blank_api_key_is_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    def cors_origins_list(self) -> list[str]:
        """Parse API_CORS_ORIGINS into a list for FastAPI CORSMiddleware."""
        raw = (self.api_cors_origins or "").strip()
        if not raw:
            return []
        if raw == "*":
            return ["*"]
        return [part.strip() for part in raw.split(",") if part.strip()]

    def cors_origin_regex(self) -> str | None:
        """Return a non-empty CORS origin regex, or None when disabled."""
        raw = (self.api_cors_origin_regex or "").strip()
        return raw or None


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
