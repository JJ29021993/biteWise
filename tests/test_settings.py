"""Smoke tests for Phase 0 / Phase 7 configuration defaults."""

from __future__ import annotations

from src.config import Settings, get_settings
from src.config.settings import DEFAULT_GROQ_BASE_URL, DEFAULT_GROQ_MODEL


def test_settings_defaults():
    settings = Settings(llm_api_key=None)
    assert settings.default_top_k == 5
    assert settings.candidate_cap == 50
    assert settings.hf_dataset_id == "ManikaSaini/zomato-restaurant-recommendation"
    assert settings.data_raw_dir.name == "raw"
    assert settings.data_processed_dir.name == "processed"
    assert settings.llm_temperature == 0.2
    assert settings.llm_mock_mode is False
    assert settings.api_rate_limit_per_minute == 60
    assert settings.api_host == "127.0.0.1"
    assert settings.api_port == 8000


def test_settings_default_to_groq():
    settings = Settings(llm_api_key=None)
    assert settings.llm_provider == "groq"
    assert settings.llm_base_url == DEFAULT_GROQ_BASE_URL
    assert settings.llm_model == DEFAULT_GROQ_MODEL
    assert "groq.com" in settings.llm_base_url


def test_get_settings_returns_settings_instance():
    get_settings.cache_clear()
    settings = get_settings()
    assert isinstance(settings, Settings)


def test_settings_env_overrides(monkeypatch):
    monkeypatch.setenv("DEFAULT_TOP_K", "3")
    monkeypatch.setenv("CANDIDATE_CAP", "25")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.1-8b-instant")
    monkeypatch.setenv("LLM_MOCK_MODE", "true")
    monkeypatch.setenv("API_RATE_LIMIT_PER_MINUTE", "10")
    settings = Settings(_env_file=None)
    assert settings.default_top_k == 3
    assert settings.candidate_cap == 25
    assert settings.llm_model == "llama-3.1-8b-instant"
    assert settings.llm_mock_mode is True
    assert settings.api_rate_limit_per_minute == 10


def test_api_port_accepts_paas_port_env(monkeypatch):
    monkeypatch.delenv("API_PORT", raising=False)
    monkeypatch.setenv("PORT", "8080")
    settings = Settings(_env_file=None)
    assert settings.api_port == 8080


def test_api_port_prefers_paas_port_over_api_port(monkeypatch):
    monkeypatch.setenv("API_PORT", "8001")
    monkeypatch.setenv("PORT", "8080")
    settings = Settings(_env_file=None)
    assert settings.api_port == 8080


def test_api_disable_docs_default_false():
    settings = Settings(llm_api_key=None)
    assert settings.api_disable_docs is False


def test_blank_api_key_becomes_none():
    settings = Settings(llm_api_key="   ")
    assert settings.llm_api_key is None


def test_cors_origins_list_parsing():
    settings = Settings(
        api_cors_origins="http://localhost:8501, http://127.0.0.1:8501"
    )
    assert settings.cors_origins_list() == [
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ]
    assert Settings(api_cors_origins="*").cors_origins_list() == ["*"]
    assert Settings(api_cors_origins="").cors_origins_list() == []


def test_cors_origin_regex_default_allows_vercel():
    settings = Settings(llm_api_key=None)
    assert settings.cors_origin_regex() == r"https://.*\.vercel\.app"
    assert Settings(api_cors_origin_regex="").cors_origin_regex() is None
    assert Settings(api_cors_origin_regex="   ").cors_origin_regex() is None
