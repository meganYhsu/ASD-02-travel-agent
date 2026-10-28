
"""Run the shared agentic loop's Multi-Agent Workflow Review."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI

from multi_agent_collector import collect
from multi_agent_pipeline import (
    build_implementation_prompt,
    build_review_prompt,
)


APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parents[1]
REPORT_DIR = APP_DIR / "review_logs"

MODEL = os.getenv("OLLAMA_REVIEW_MODEL", "qwen2.5:3b")
OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434/v1",
)

client = OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama", # pragma: allowlist secret
    timeout=300.0,
    max_retries=0,
)


def call_ai(system_prompt: str, user_prompt: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
        max_tokens=220,
    )

    answer = (response.choices[0].message.content or "").strip()
    if not answer:
        raise ValueError("The AI model returned an empty response.")

    return answer


def main():
    print("\n=== MULTI-AGENT WORKFLOW REVIEW ===")

    print("\n[1/3] OBSERVE: Collecting workflow evidence...")
    ok, evidence = collect(APP_DIR, REPO_ROOT)

    if not ok:
        print(f"Evidence collection failed: {evidence}")
        return

    workflow = json.loads(evidence)["workflow"]
    workflow_id = workflow["workflow_id"]

    print(f"Workflow ID: {workflow_id}")
    print(f"Workflow status: {workflow['status']}")

    print("\n[2/3] IMPLEMENTATION: Assessing workflow...")

    implementation_prompt = build_implementation_prompt(
        "Assess the recorded Multi-Agent workflow execution.",
        evidence,
    )

    print(f"Evidence characters: {len(evidence)}")
    print(f"Implementation prompt characters: {len(implementation_prompt)}")

    implementation_result = None
    review_result = None
    error = None

    try:
        implementation_result = call_ai(
            "You are an evidence-based software workflow assessor. "
            "Do not invent successful tests or approvals.",
            implementation_prompt,
        )
        print(implementation_result)

        print("\n[3/3] REVIEW: Validating assessment...")

        review_prompt = build_review_prompt(
            implementation_result,
            evidence,
        )

        review_result = call_ai(
            "You are an independent software review validator. "
            "Identify unsupported claims and the highest-priority risk.",
            review_prompt,
        )
        print(review_result)

    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        print(f"\nAI review failed: {error}")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    report = {
        "review_mode": "multi_agent",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_workflow_id": workflow_id,
        "source_workflow_status": workflow["status"],
        "model": MODEL,
        "implementation_assessment": implementation_result,
        "review_recommendation": review_result,
        "review_status": (
            "completed" if review_result is not None else "failed"
        ),
        "human_release_decision": "pending",
        "error": error,
    }

    report_path = REPORT_DIR / f"multi_agent_review_{workflow_id}.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\nReview report saved: {report_path}")
    print(f"Review status: {report['review_status']}")
    if report["review_status"] != "completed":
        raise SystemExit(1)
    print("Human release decision: pending")


if __name__ == "__main__":
    main()
