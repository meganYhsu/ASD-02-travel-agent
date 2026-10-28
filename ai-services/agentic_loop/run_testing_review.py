
"""Run the Release 2 Testing Report Review using local Ollama."""

import json
import os
import uuid
import argparse
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI

from testing_collector import collect
from testing_pipeline import (
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
        max_tokens= 180,
    )

    answer = (response.choices[0].message.content or "").strip()

    if not answer:
        raise ValueError("AI model returned an empty response.")

    return answer


def parse_args():
    parser = argparse.ArgumentParser(
        description="Release 2 Testing Report Review"
    )

    parser.add_argument(
        "--student",
        choices=[
            "student-1",
            "student-2",
            "student-3",
            "student-4",
            "student-5",
            "all",
        ],
        default="all",
        help="Select the student or review all students",
    )

    return parser.parse_args()


def main():
    args = parse_args()
    print(f"Selected testing scope: {args.student}")
    print("\n=== TESTING REPORT REVIEW ===")

    print("\n[1/3] OBSERVE: Collecting testing evidence...")
    ok, evidence = collect(APP_DIR, REPO_ROOT,student=args.student,)

    if not ok:
        print(f"Evidence collection failed: {evidence}")
        return

    parsed = json.loads(evidence)
    pre_reports = parsed["pre_commit_reports"]
    post_reports = parsed["post_commit_reports"]

    print(f"Pre-commit reports: {len(pre_reports)}")
    print(f"Post-commit reports: {len(post_reports)}")
    print(f"Evidence characters: {len(evidence)}")

    assessment = None
    review = None
    error = None

    try:
        print("\n[2/3] IMPLEMENTATION: Assessing testing evidence...")

        implementation_prompt = build_implementation_prompt(
            "Review available Release 2 testing reports.",
            evidence,
        )

        print(f"Implementation prompt characters: {len(implementation_prompt)}")

        assessment = call_ai(
            "You are a testing and security evidence assessor. "
            "Use only provided reports; distinguish verified, "
            "failed and missing evidence. Never invent test results.",
            implementation_prompt,
        )

        print(assessment)

        print("\n[3/3] REVIEW: Validating assessment...")

        review_prompt = build_review_prompt(assessment, evidence)

        review = call_ai(
            "You are an independent testing evidence reviewer. "
            "Check claims against original reports. "
            "Never assume missing CI/CD results passed.",
            review_prompt,
        )

        print(review)

    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        print(f"\nTesting review failed: {error}")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    report = {
        "review_id": str(uuid.uuid4()),
        "review_mode": "testing",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "pre_commit_report_sources": [
            item["source"] for item in pre_reports
        ],
        "post_commit_report_sources": [
            item["source"] for item in post_reports
        ],
        "post_commit_evidence_status": parsed[
            "post_commit_evidence_status"
        ],
        "implementation_assessment": assessment,
        "review_recommendation": review,
        "review_status": (
            "completed" if assessment and review else "failed"
        ),
        "human_release_decision": "pending",
        "error": error,
    }

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = REPORT_DIR / f"testing_review_{timestamp}_{report['review_id'][:8]}.json"

    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\nReview report saved: {report_path}")
    print(f"Review status: {report['review_status']}")
    print("Human release decision: pending")


if __name__ == "__main__":
    main()
