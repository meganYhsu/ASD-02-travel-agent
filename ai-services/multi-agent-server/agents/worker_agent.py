import logging
import os
import time
from pathlib import Path
from typing import Any, Dict

try:
    from openai import APITimeoutError, OpenAI
except ModuleNotFoundError:
    APITimeoutError = TimeoutError
    OpenAI = None


logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parents[1]
PROMPT_PATH = BASE_DIR / "prompts" / "worker_prompt.txt"

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434/v1"
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen2.5:3b"
)

OLLAMA_TIMEOUT_SECONDS = float(
    os.getenv("OLLAMA_TIMEOUT_SECONDS", "120")
)

FAST_MODE = os.getenv(
    "FAST_MODE",
    "true"
).lower() == "true"

WORKER_MAX_TOKENS = int(
    os.getenv(
        "WORKER_MAX_TOKENS",
        "180" if FAST_MODE else "400"
    )
)

client = None

if OpenAI:
    client = OpenAI(
        base_url=OLLAMA_BASE_URL,
        api_key="ollama",
        timeout=OLLAMA_TIMEOUT_SECONDS,
        max_retries=0
    )


def load_prompt() -> str:
    return PROMPT_PATH.read_text(
        encoding="utf-8"
    ).strip()


def call_model(
        user_request: str
) -> str:
    prompt = user_request

    started_at = time.monotonic()
    logger.info(
        "Worker model call started: base_url=%s model=%s timeout=%ss prompt_chars=%s",
        OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT_SECONDS, len(prompt)
    )
    try:
        if client is None:
            raise RuntimeError("OpenAI package is not installed.")

        response = client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": load_prompt()},
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            max_tokens=WORKER_MAX_TOKENS
        )

        output = (response.choices[0].message.content or "").strip()
        if not output:
            raise ValueError("Model returned an empty response")
        logger.info("Worker model call completed in %.2fs", time.monotonic() - started_at)
        return output

    except Exception:
        logger.exception("Worker model call failed after %.2fs", time.monotonic() - started_at)
        raise


def generate_output(
        user_request: str
) -> Dict[str, Any]:
    try:
        output = call_model(user_request)
    except Exception as exc:
        return {
            "status": "timeout" if isinstance(exc, (APITimeoutError, TimeoutError)) else "error",
            "agent": "worker_agent",
            "model": OLLAMA_MODEL,
            "output": "Worker could not generate an answer. Human review is required.",
            "error": f"{type(exc).__name__}: {exc}",
            "human_approval_required": True
        }

    return {
        "status": "success",
        "agent": "worker_agent",
        "model": OLLAMA_MODEL,
        "output": output,
        "human_approval_required": True
    }


if __name__ == "__main__":
    import json

    result = generate_output(
        "Summarise the saved itinerary and flag missing travel details."
    )

    print(
        json.dumps(
            result,
            indent=2
        )
    )
