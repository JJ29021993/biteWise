"""Unit tests for Phase 6 FastAPI recommendations API."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from src.api.main import create_app
from src.api.rate_limit import SlidingWindowRateLimiter
from src.config import Settings
from src.llm import MockLLMClient
from src.services import RecommenderService

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def candidate_store() -> pd.DataFrame:
    rows = json.loads((FIXTURES / "candidates.json").read_text(encoding="utf-8"))
    frame = pd.DataFrame(rows)
    frame["city"] = "Bangalore"
    frame["cuisine_tokens"] = frame["cuisines"].map(
        lambda s: [p.strip() for p in str(s).split(",")]
    )
    frame["listed_in_city"] = frame["location"]
    return frame


@pytest.fixture
def budget_thresholds() -> dict:
    return {"low_max": 500.0, "medium_max": 1500.0}


@pytest.fixture
def sample_llm_text() -> str:
    return (FIXTURES / "sample_llm_response.json").read_text(encoding="utf-8")


@pytest.fixture
def api_client(candidate_store, budget_thresholds, sample_llm_text, tmp_path):
    store_file = tmp_path / "restaurants.parquet"
    # Presence-only check for /health; service uses injected frame.
    store_file.write_bytes(b"placeholder")
    settings = Settings(
        data_processed_dir=tmp_path,
        candidate_cap=50,
        default_top_k=3,
        api_rate_limit_per_minute=1000,
        api_cors_origins="http://localhost:8501",
        llm_mock_mode=False,
    )
    service = RecommenderService(
        settings=settings,
        client=MockLLMClient(response_text=sample_llm_text),
        restaurants=candidate_store,
        budget_thresholds=budget_thresholds,
        dry_run=False,
    )
    app = create_app(settings=settings, service=service, enable_rate_limit=False)
    return TestClient(app)


def test_health_ok_when_store_present(api_client):
    res = api_client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["store_ready"] is True


def test_health_degraded_when_store_missing(candidate_store, budget_thresholds, tmp_path):
    settings = Settings(data_processed_dir=tmp_path / "empty")
    service = RecommenderService(
        settings=settings,
        restaurants=candidate_store,
        budget_thresholds=budget_thresholds,
        dry_run=True,
    )
    app = create_app(settings=settings, service=service, enable_rate_limit=False)
    client = TestClient(app)
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "degraded"
    assert body["store_ready"] is False
    assert body["detail"]


def test_recommendations_happy_path(api_client):
    res = api_client.post(
        "/api/recommendations",
        json={
            "location": "Indiranagar",
            "budget": "medium",
            "cuisine": "Italian",
            "min_rating": 4.0,
            "additional_preferences": "family-friendly",
            "top_k": 3,
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["summary"]
    assert len(body["recommendations"]) == 3
    assert body["recommendations"][0]["name"] == "Trattoria X"
    assert body["recommendations"][0]["estimated_cost"] == "₹1,200 for two"
    assert "meta" in body
    assert "location" in body["meta"]["filters_applied"]
    assert body["preferences"]["cuisine"] == "Italian"


def test_recommendations_dry_run(api_client):
    res = api_client.post(
        "/api/recommendations",
        json={
            "location": "Indiranagar",
            "budget": "medium",
            "cuisine": "Italian",
            "min_rating": 4.0,
            "top_k": 2,
            "dry_run": True,
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["meta"]["dry_run"] is True
    assert len(body["recommendations"]) == 2


def test_invalid_budget_returns_422(api_client):
    res = api_client.post(
        "/api/recommendations",
        json={
            "location": "Indiranagar",
            "budget": "rich",
            "cuisine": "Italian",
        },
    )
    assert res.status_code == 422
    assert "detail" in res.json()


def test_missing_required_field_returns_422(api_client):
    # cuisine is optional; budget remains required
    res = api_client.post(
        "/api/recommendations",
        json={"location": "Indiranagar", "cuisine": "Italian"},
    )
    assert res.status_code == 422


def test_recommendations_without_cuisine_ok(api_client):
    res = api_client.post(
        "/api/recommendations",
        json={
            "location": "Indiranagar",
            "budget": "medium",
            "min_rating": 4.0,
            "top_k": 2,
            "dry_run": True,
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert "cuisine" not in body["meta"]["filters_applied"]
    assert body["preferences"]["cuisine"] is None


def test_extra_fields_rejected(api_client):
    res = api_client.post(
        "/api/recommendations",
        json={
            "location": "Indiranagar",
            "budget": "medium",
            "cuisine": "Italian",
            "unknown_field": "nope",
        },
    )
    assert res.status_code == 422


def test_cors_allows_configured_origin(api_client):
    res = api_client.options(
        "/api/recommendations",
        headers={
            "Origin": "http://localhost:8501",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert res.status_code in (200, 204)
    assert res.headers.get("access-control-allow-origin") == "http://localhost:8501"


def test_rate_limiter_blocks_after_limit():
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=60.0)
    assert limiter.allow("ip")[0] is True
    assert limiter.allow("ip")[0] is True
    allowed, remaining = limiter.allow("ip")
    assert allowed is False
    assert remaining == 0


def test_rate_limit_middleware_returns_429(
    candidate_store, budget_thresholds, sample_llm_text, tmp_path
):
    settings = Settings(
        data_processed_dir=tmp_path,
        api_rate_limit_per_minute=2,
        api_cors_origins="http://localhost:8501",
    )
    service = RecommenderService(
        settings=settings,
        client=MockLLMClient(response_text=sample_llm_text),
        restaurants=candidate_store,
        budget_thresholds=budget_thresholds,
        dry_run=True,
    )
    app = create_app(settings=settings, service=service, enable_rate_limit=True)
    client = TestClient(app)
    payload = {
        "location": "Indiranagar",
        "budget": "medium",
        "cuisine": "Italian",
        "top_k": 1,
        "dry_run": True,
    }
    assert client.post("/api/recommendations", json=payload).status_code == 200
    assert client.post("/api/recommendations", json=payload).status_code == 200
    blocked = client.post("/api/recommendations", json=payload)
    assert blocked.status_code == 429
    assert "Rate limit" in blocked.json()["detail"]
    # Health remains available
    assert client.get("/health").status_code == 200


def test_openapi_includes_recommendations_path(api_client):
    schema = api_client.get("/openapi.json").json()
    assert "/api/recommendations" in schema["paths"]
    assert "/api/options" in schema["paths"]
    assert "/health" in schema["paths"]
    post = schema["paths"]["/api/recommendations"]["post"]
    assert "RecommendationRequest" in str(post) or "application/json" in str(
        post["requestBody"]
    )


def test_cors_allows_vercel_preview_origin(
    candidate_store, budget_thresholds, sample_llm_text, tmp_path
):
    settings = Settings(
        data_processed_dir=tmp_path,
        api_cors_origins="http://localhost:3000",
        api_cors_origin_regex=r"https://.*\.vercel\.app",
    )
    service = RecommenderService(
        settings=settings,
        client=MockLLMClient(response_text=sample_llm_text),
        restaurants=candidate_store,
        budget_thresholds=budget_thresholds,
        dry_run=True,
    )
    app = create_app(settings=settings, service=service, enable_rate_limit=False)
    client = TestClient(app)
    origin = "https://bite-wise-tau.vercel.app"
    res = client.options(
        "/api/options",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == origin


def test_docs_disabled_when_configured(
    candidate_store, budget_thresholds, sample_llm_text, tmp_path
):
    settings = Settings(
        data_processed_dir=tmp_path,
        api_disable_docs=True,
        api_cors_origins="http://localhost:3000",
    )
    service = RecommenderService(
        settings=settings,
        client=MockLLMClient(response_text=sample_llm_text),
        restaurants=candidate_store,
        budget_thresholds=budget_thresholds,
        dry_run=True,
    )
    app = create_app(settings=settings, service=service, enable_rate_limit=False)
    client = TestClient(app)
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404
    assert client.get("/health").status_code == 200


def test_options_endpoint_returns_locations_and_cuisines(api_client):
    res = api_client.get("/api/options")
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body["locations"], list)
    assert isinstance(body["cuisines"], list)
    assert body["locations"]
    assert "default_location" in body
