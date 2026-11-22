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


def _resolve_bind() -> tuple[str, int]:
    """
    Pick host/port for uvicorn.

    Railway injects PORT and (often) a public-networking *Target Port* of 8000
    from EXPOSE/API_PORT. Prefer an explicit API_PORT when both are set so the
    process matches that target; otherwise use PORT. Always bind 0.0.0.0 when
    either PaaS signal is present (ignore pasted local API_HOST=127.0.0.1).
    """
    paas_port = os.environ.get("PORT")
    api_port = os.environ.get("API_PORT")

    if paas_port or api_port:
        host = "0.0.0.0"
        if api_port:
            port = int(api_port)
        else:
            port = int(paas_port)  # type: ignore[arg-type]
        return host, port

    from src.config import get_settings

    settings = get_settings()
    return settings.api_host, settings.api_port


def main() -> None:
    _ensure_processed_store()

    import uvicorn

    host, port = _resolve_bind()

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
