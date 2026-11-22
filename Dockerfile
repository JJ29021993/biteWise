# BiteWise FastAPI — see docs/deployment-plan.md
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    API_HOST=0.0.0.0 \
    RUN_INGESTION=true
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
RUN mkdir -p /app/data/processed /app/data/raw \
    && if [ ! -f /app/data/processed/restaurants.parquet ]; then \
         python -m src.ingestion; \
       fi

EXPOSE 8000

# No shell entrypoint — Windows CRLF on *.sh was causing Railway 502
# ("exec /entrypoint.sh: no such file or directory"). Boot logic lives in
# ``python -m src.api`` instead. Shell-form CMD expands $PORT at runtime.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=5 \
    CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/health" || exit 1

CMD sh -c 'echo "BiteWise boot PORT=${PORT:-8000}"; exec python -m src.api'
