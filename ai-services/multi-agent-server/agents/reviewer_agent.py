import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict

from openai import APITimeoutError, OpenAI


logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parents[1]
PROMPT_PATH = BASE_DIR / "prompts" / "reviewer_prompt.txt"

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434/v1"
)

OLLAMA_REVIEW_MODEL = os.getenv(
    "OLLAMA_REVIEW_MODEL",
    "qwen2.5:3b"
)

OLLAMA_TIMEOUT_SECONDS = float(
    os.getenv("OLLAMA_TIMEOUT_SECONDS", "240")
)

FAST_MODE = os.getenv(
    "FAST_MODE",
    "true"
).lower() == "true"

REVIEWER_MAX_TOKENS = int(
    os.getenv(
        "REVIEWER_MAX_TOKENS",
        "160" if FAST_MODE else "400"
    )
)

client = OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama",  # pragma: allowlist secret
    timeout=OLLAMA_TIMEOUT_SECONDS,
    max_retries=0
)


def load_prompt() -> str:
    return PROMPT_PATH.read_text(
        encoding="utf-8"
    ).strip()


def call_model(
        user_request: str,
        worker_result: Dict[str, Any]
) -> str:
    prompt = (
        f"Request and saved data:\n{user_request}\nWorker result:\n"
        + json.dumps(worker_result, ensure_ascii=False, separators=(",", ":"))
    )

    started_at = time.monotonic()
    logger.info(
        "Reviewer model call started: base_url=%s model=%s timeout=%ss prompt_chars=%s",
        OLLAMA_BASE_URL, OLLAMA_REVIEW_MODEL, OLLAMA_TIMEOUT_SECONDS, len(prompt)
    )
    try:
        response = client.chat.completions.create(
            model=OLLAMA_REVIEW_MODEL,
            messages=[
                {"role": "system", "content": load_prompt()},
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            max_tokens=REVIEWER_MAX_TOKENS
        )

        output = (response.choices[0].message.content or "").strip()
        if not output:
            raise ValueError("Model returned an empty response")
        logger.info("Reviewer model call completed in %.2fs", time.monotonic() - started_at)
        return output

    except Exception:
        logger.exception("Reviewer model call failed after %.2fs", time.monotonic() - started_at)
        raise


def review_output(
        user_request: str,
        worker_result: Dict[str, Any]
) -> Dict[str, Any]:
    try:
        review = call_model(user_request, worker_result)
    except Exception as exc:
        return {
            "status": "timeout" if isinstance(exc, (APITimeoutError, TimeoutError)) else "error",
            "agent": "reviewer_agent",
            "model": OLLAMA_REVIEW_MODEL,
            "review": "Reviewer could not assess the answer. Human review is required.",
            "error": f"{type(exc).__name__}: {exc}",
            "human_approval_required": True
        }
    return {
        "status": "success",
        "agent": "reviewer_agent",
        "model": OLLAMA_REVIEW_MODEL,
        "review": review,
        "human_approval_required": True
    }


if __name__ == "__main__":
    sample_worker_result = {
        "status": "success",
        "agent": "worker_agent",
        "output": "No saved itinerary data was provided.",
        "human_approval_required": True
    }

    result = review_output(
        "Check the itinerary summary against the saved travel details.",
        sample_worker_result
    )

    print(
        json.dumps(
            result,
            indent=2
        )
    )
