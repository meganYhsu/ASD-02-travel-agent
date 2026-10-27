import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List

from openai import APITimeoutError, OpenAI


logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parents[1]
PROMPT_PATH = BASE_DIR / "prompts" / "planner_prompt.txt"

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434/v1"
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen2.5:3b"
)

OLLAMA_TIMEOUT_SECONDS = float(
    os.getenv("OLLAMA_TIMEOUT_SECONDS", "240")
)

FAST_MODE = os.getenv(
    "FAST_MODE",
    "true"
).lower() == "true"

PLANNER_MAX_TOKENS = int(
    os.getenv(
        "PLANNER_MAX_TOKENS",
        "120" if FAST_MODE else "300"
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


def default_steps() -> List[Dict[str, Any]]:
    return [
        {
            "step": 1,
            "agent": "planner_agent",
            "action": "Identify the supplied service facts needed for the task"
        },
        {
            "step": 2,
            "agent": "worker_agent",
            "action": "Answer using the supplied service context"
        },
        {
            "step": 3,
            "agent": "reviewer_agent",
            "action": "Check the answer against the supplied context and flag missing evidence"
        },
        {
            "step": 4,
            "agent": "human_reviewer",
            "action": "Accept, partially accept, or reject"
        }
    ]


def call_model(
        user_request: str
) -> str:
    prompt = user_request

    started_at = time.monotonic()
    logger.info(
        "Planner model call started: base_url=%s model=%s timeout=%ss prompt_chars=%s",
        OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT_SECONDS, len(prompt)
    )
    try:
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
            max_tokens=PLANNER_MAX_TOKENS
        )

        output = (response.choices[0].message.content or "").strip()
        if not output:
            raise ValueError("Model returned an empty response")
        logger.info("Planner model call completed in %.2fs", time.monotonic() - started_at)
        return output

    except Exception:
        logger.exception("Planner model call failed after %.2fs", time.monotonic() - started_at)
        raise


def plan_workflow(
        user_request: str
) -> Dict[str, Any]:
    try:
        plan = call_model(user_request)
    except Exception as exc:
        return {
            "status": "timeout" if isinstance(exc, (APITimeoutError, TimeoutError)) else "error",
            "agent": "planner_agent",
            "model": OLLAMA_MODEL,
            "plan": "Planner could not generate a plan. Human review is required.",
            "error": f"{type(exc).__name__}: {exc}",
            "human_approval_required": True
        }
    return {
        "status": "success",
        "agent": "planner_agent",
        "model": OLLAMA_MODEL,
        "objective": user_request,
        "plan": plan,
        "steps": default_steps(),
        "human_approval_required": True
    }


if __name__ == "__main__":
    import json

    result = plan_workflow(
        "Summarise the saved itinerary and flag missing travel details."
    )

    print(
        json.dumps(
            result,
            indent=2
        )
    )
