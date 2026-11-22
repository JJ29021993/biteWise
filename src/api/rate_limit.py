"""Simple in-memory sliding-window rate limiter for public API deployments."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class SlidingWindowRateLimiter:
    """Per-key request counter over a fixed window (default: 60 seconds)."""

    def __init__(self, *, max_requests: int, window_seconds: float = 60.0) -> None:
        if max_requests < 1:
            raise ValueError("max_requests must be >= 1")
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> tuple[bool, int]:
        """
        Record a hit for ``key``.

        Returns (allowed, remaining). Remaining is 0 when denied.
        """
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            bucket = self._hits[key]
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self.max_requests:
                return False, 0
            bucket.append(now)
            remaining = self.max_requests - len(bucket)
            return True, remaining


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Reject excess requests with HTTP 429. Skips health/docs by default."""

    def __init__(
        self,
        app,
        *,
        limiter: SlidingWindowRateLimiter,
        exempt_paths: frozenset[str] | None = None,
        key_fn: Callable[[Request], str] | None = None,
    ) -> None:
        super().__init__(app)
        self.limiter = limiter
        self.exempt_paths = exempt_paths or frozenset(
            {"/health", "/docs", "/openapi.json", "/redoc", "/"}
        )
        self.key_fn = key_fn or _client_ip

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path.rstrip("/") or "/"
        # Normalize: treat /health/ same as /health for exemption.
        if path in self.exempt_paths or request.url.path in self.exempt_paths:
            return await call_next(request)

        key = self.key_fn(request)
        allowed, remaining = self.limiter.allow(key)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": (
                        "Rate limit exceeded. Try again shortly "
                        f"(max {self.limiter.max_requests} requests per "
                        f"{int(self.limiter.window_seconds)}s)."
                    )
                },
                headers={
                    "Retry-After": str(int(self.limiter.window_seconds)),
                    "X-RateLimit-Limit": str(self.limiter.max_requests),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.limiter.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"
