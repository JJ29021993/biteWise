"""Run the API with uvicorn: ``python -m src.api``."""

from __future__ import annotations

import os

import uvicorn

from src.config import get_settings


def main() -> None:
    settings = get_settings()
    host = settings.api_host
    port = settings.api_port

    # Railway/Render/Fly inject PORT and proxy to it. Always bind publicly in that case,
    # even if someone copied local API_HOST=127.0.0.1 into the platform env.
    if os.environ.get("PORT"):
        host = "0.0.0.0"
        port = int(os.environ["PORT"])

    print(f"BiteWise API listening on http://{host}:{port}", flush=True)
    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
