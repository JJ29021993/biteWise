"""Run the Phase 4 demo via `python -m src.services`."""

from __future__ import annotations

import runpy
from pathlib import Path


def main() -> None:
    demo = Path(__file__).resolve().parents[2] / "scripts" / "demo_recommend.py"
    runpy.run_path(str(demo), run_name="__main__")


if __name__ == "__main__":
    main()
