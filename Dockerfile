# BiteWise FastAPI — see docs/deployment-plan.md
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    API_HOST=0.0.0.0 \
    API_PORT=8000

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install package deps before copying full tree (better layer cache)
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir -e ".[data,llm,api]"

# Baked processed store when present at build time (gitignored locally, copied if exists)
COPY data/processed ./data/processed
COPY data/raw/.gitkeep ./data/raw/.gitkeep
COPY scripts/docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh \
    && mkdir -p /app/data/processed /app/data/raw

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${API_PORT:-8000}/health" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "-m", "src.api"]
