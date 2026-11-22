"""FastAPI application — Phase 6 REST API for the recommendation pipeline.

Run:
    uvicorn src.api.main:app --reload
    python -m src.api
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.rate_limit import RateLimitMiddleware, SlidingWindowRateLimiter
from src.api.schemas import (
    ErrorResponse,
    HealthResponse,
    OptionsResponse,
    RecommendationRequest,
    RecommendationResponseOut,
)
from src.config import Settings, get_settings
from src.filtering.preferences import PreferenceValidationError
from src.ingestion.preprocess import processed_path
from src.services.models import RecommendationResponse
from src.services.recommender import RecommenderService, get_recommender_service
from src.ui.options import DEFAULT_LOCATION, get_cuisine_options, get_location_options

_SERVICE_ATTR = "recommender_service"
_SETTINGS_ATTR = "api_settings"


def _to_response_out(result: RecommendationResponse) -> RecommendationResponseOut:
    return RecommendationResponseOut.model_validate(result.to_dict())


def create_app(
    *,
    settings: Settings | None = None,
    service: RecommenderService | None = None,
    enable_rate_limit: bool | None = None,
) -> FastAPI:
    """
    Build the FastAPI app.

    Pass ``service`` in tests to inject a fixture-backed RecommenderService.
    Rate limiting defaults on; set ``enable_rate_limit=False`` in unit tests.
    """
    cfg = settings or get_settings()
    rate_limit_on = (
        cfg.api_rate_limit_per_minute > 0
        if enable_rate_limit is None
        else bool(enable_rate_limit)
    )

    docs_kwargs: dict[str, Any] = {}
    if cfg.api_disable_docs:
        docs_kwargs = {
            "docs_url": None,
            "redoc_url": None,
            "openapi_url": None,
        }

    app = FastAPI(
        title="BiteWise Restaurant Recommender API",
        description=(
            "Filter-then-LLM restaurant recommendations. "
            "POST preferences to `/api/recommendations`; facts come from the "
            "local Zomato store, explanations from Groq (or dry-run mock)."
        ),
        version="0.1.0",
        responses={
            422: {"model": ErrorResponse, "description": "Validation error"},
            429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        },
        **docs_kwargs,
    )
    setattr(app.state, _SETTINGS_ATTR, cfg)
    if service is not None:
        setattr(app.state, _SERVICE_ATTR, service)

    origins = cfg.cors_origins_list()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins
        or [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=origins != ["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    if rate_limit_on:
        app.add_middleware(
            RateLimitMiddleware,
            limiter=SlidingWindowRateLimiter(
                max_requests=cfg.api_rate_limit_per_minute,
                window_seconds=60.0,
            ),
        )

    @app.exception_handler(PreferenceValidationError)
    async def _preference_validation_handler(
        _request: Request, exc: PreferenceValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc)},
        )

    @app.exception_handler(RequestValidationError)
    async def _request_validation_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Keep FastAPI's structured error list for OpenAPI clients.
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors()},
        )

    def get_settings_dep() -> Settings:
        return getattr(app.state, _SETTINGS_ATTR)

    def get_service_dep(
        settings_dep: Settings = Depends(get_settings_dep),
    ) -> RecommenderService:
        existing = getattr(app.state, _SERVICE_ATTR, None)
        if existing is not None:
            return existing
        return get_recommender_service(settings=settings_dep)

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {
            "service": "BiteWise Restaurant Recommender API",
            "docs": "/docs",
            "health": "/health",
            "recommendations": "POST /api/recommendations",
        }

    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["ops"],
        summary="Liveness / readiness probe",
    )
    def health(settings_dep: Settings = Depends(get_settings_dep)) -> HealthResponse:
        store = processed_path(settings_dep)
        ready = store.is_file()
        # A07: degraded when processed store is missing.
        if ready:
            return HealthResponse(
                status="ok",
                store_ready=True,
                store_path=str(store),
                dry_run_default=bool(settings_dep.llm_mock_mode),
                detail=None,
            )
        return HealthResponse(
            status="degraded",
            store_ready=False,
            store_path=str(store),
            dry_run_default=bool(settings_dep.llm_mock_mode),
            detail=(
                "Processed restaurant store not found. "
                "Run `python -m src.ingestion` before serving recommendations."
            ),
        )

    @app.get(
        "/api/options",
        response_model=OptionsResponse,
        tags=["recommendations"],
        summary="Location and cuisine choices for the UI",
    )
    def get_options(
        settings_dep: Settings = Depends(get_settings_dep),
    ) -> OptionsResponse:
        locations = get_location_options(settings=settings_dep)
        cuisines = get_cuisine_options(settings=settings_dep)
        default = DEFAULT_LOCATION
        if default not in locations and locations:
            default = locations[0]
        return OptionsResponse(
            locations=locations,
            cuisines=cuisines,
            default_location=default,
        )

    @app.post(
        "/api/recommendations",
        response_model=RecommendationResponseOut,
        tags=["recommendations"],
        summary="Rank restaurants for user preferences",
        responses={
            422: {"model": ErrorResponse, "description": "Invalid preference payload"},
        },
    )
    def create_recommendations(
        body: RecommendationRequest,
        service_dep: RecommenderService = Depends(get_service_dep),
    ) -> RecommendationResponseOut:
        payload: dict[str, Any] = body.model_dump(
            exclude={"dry_run"},
            exclude_none=False,
        )
        result = service_dep.recommend(payload, dry_run=body.dry_run)
        return _to_response_out(result)

    return app


# ASGI entry for `uvicorn src.api.main:app`
app = create_app()
