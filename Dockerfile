# BiteWise FastAPI — see docs/deployment-plan.md
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    API_HOST=0.0.0.0
# Do not hardcode API_PORT — Railway injects PORT and proxies to it.

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install package deps before copying full tree (better layer cache)
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir -e ".[data,llm,api]"

# Baked processed store from git (restaurants.parquet). Fallback: ingest at build.
COPY data/processed ./data/processed
COPY data/raw/.gitkeep ./data/raw/.gitkeep
COPY scripts/docker-entrypoint.sh /entrypoint.sh
# Strip CR so Windows CRLF checkouts cannot break the Linux shebang (Railway 502).
RUN sed -i 's/\r$//' /entrypoint.sh \
    && chmod +x /entrypoint.sh \
    && mkdir -p /app/data/processed /app/data/raw \
    && if [ ! -f /app/data/processed/restaurants.parquet ]; then \
         python -m src.ingestion; \
       fi

# Safety net at container start if a volume hides the baked store
ENV RUN_INGESTION=true

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT:-${API_PORT:-8000}}/health" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "-m", "src.api"]
