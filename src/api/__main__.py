"""Run the API with uvicorn: ``python -m src.api``."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _ensure_processed_store() -> None:
    """Best-effort bake of the Parquet store before serving (Docker / Railway)."""
    if os.environ.get("RUN_INGESTION", "true").lower() in {"0", "false", "no"}:
        return

    processed_dir = Path(
        os.environ.get("DATA_PROCESSED_DIR", "/app/data/processed")
    )
    # Local runs use repo-relative data/; only auto-ingest in container layouts.
    if not str(processed_dir).startswith("/app"):
        return

    store = processed_dir / "restaurants.parquet"
    if store.is_file():
        print(f"Processed store found at {store}", flush=True)
        return

    print(f"Processed store missing at {store}; running ingestion...", flush=True)
    try:
        from src.ingestion.__main__ import run as ingest_run

        ingest_run(force_download=False)
    except Exception as exc:  # noqa: BLE001 — never block API boot
        print(
            f"WARNING: ingestion failed ({exc!r}). "
            "Starting API anyway (health will be degraded).",
            flush=True,
        )


def main() -> None:
    _ensure_processed_store()

    # Import after optional ingestion so a missing store does not fail import paths.
    import uvicorn

    from src.config import get_settings

    settings = get_settings()
    host = settings.api_host
    port = settings.api_port

    # Railway/Render/Fly inject PORT and proxy to it. Always bind publicly in that case,
    # even if someone copied local API_HOST=127.0.0.1 into the platform env.
    if os.environ.get("PORT"):
        host = "0.0.0.0"
        port = int(os.environ["PORT"])

    print(f"BiteWise API listening on http://{host}:{port}", flush=True)
    print(
        f"env PORT={os.environ.get('PORT')!r} API_HOST={os.environ.get('API_HOST')!r} "
        f"API_PORT={os.environ.get('API_PORT')!r}",
        flush=True,
    )
    sys.stdout.flush()

    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        reload=False,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    main()
