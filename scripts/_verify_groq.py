"""One-off connectivity check for Groq. Do not print secrets."""

from __future__ import annotations

from src.config.settings import PROJECT_ROOT, Settings, get_settings
from src.llm.client import GroqLLMClient, LLMError


def _diagnose_env() -> None:
    env_path = PROJECT_ROOT / ".env"
    print("env_path:", env_path)
    print("env_exists:", env_path.exists())
    if not env_path.exists():
        return
    for i, line in enumerate(env_path.read_text(encoding="utf-8").splitlines(), 1):
        upper = line.upper()
        if "KEY" not in upper and "GROQ" not in upper and "LLM_API" not in upper:
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            print(f"line {i}: commented/blank key-related line")
            continue
        if "=" not in line:
            print(f"line {i}: key-related line without '='")
            continue
        name, _, val = line.partition("=")
        value = val.strip().strip('"').strip("'")
        print(
            f"line {i}: name={name.strip()!r} value_len={len(value)} empty={not bool(value)}"
        )


def main() -> int:
    _diagnose_env()
    get_settings.cache_clear()
    settings = Settings()
    key = settings.llm_api_key
    print("provider:", settings.llm_provider)
    print("model:", settings.llm_model)
    print("base_url:", settings.llm_base_url)
    print("api_key_loaded:", bool(key))
    if key and len(key) > 7:
        print("api_key_prefix:", f"{key[:7]}...")
    else:
        print("api_key_prefix: (missing/short)")

    if not key:
        print("status: FAILED")
        print("error: GROQ_API_KEY / LLM_API_KEY not loaded from .env")
        return 1

    client = GroqLLMClient(settings=settings)
    try:
        text = client.complete(
            [
                {
                    "role": "system",
                    "content": "Reply with a single short JSON object only.",
                },
                {
                    "role": "user",
                    "content": 'Return {"ok": true, "provider": "groq"}.',
                },
            ],
            max_tokens=128,
        )
        print("status: SUCCESS")
        print("response:", text[:300].replace("\n", " "))
        return 0
    except LLMError as exc:
        print("status: FAILED")
        print("error:", exc)
        cause = exc.__cause__
        if cause is not None:
            print("cause_type:", type(cause).__name__)
            print("cause:", str(cause)[:800])
        return 1
    except Exception as exc:  # noqa: BLE001
        print("status: FAILED")
        print("error_type:", type(exc).__name__)
        print("error:", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
