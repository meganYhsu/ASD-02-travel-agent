
"""Run Release 2 Cloud Deployment Report Review using local Ollama.

Reviews shared AWS EC2 deployment evidence.
Does not deploy services or execute AWS commands.
"""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI

from cloud_collector import collect
from cloud_pipeline import (
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
    """Call the local Ollama model."""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
        max_tokens=350,
    )

    answer = (response.choices[0].message.content or "").strip()

    if not answer:
        raise ValueError("AI model returned an empty response.")

    return answer


def parse_args():
    parser = argparse.ArgumentParser(
        description="Release 2 Cloud Deployment Report Review"
    )

    parser.add_argument(
        "--student",
        choices=["all"],
        default="all",
        help="Cloud deployment is reviewed at shared application scope.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    print(f"Selected cloud scope: {args.student}")
    print("\n=== CLOUD DEPLOYMENT REPORT REVIEW ===")

    print("\n[1/3] OBSERVE: Collecting cloud deployment evidence...")

    ok, evidence = collect(APP_DIR, REPO_ROOT)

    if not ok:
        print(f"Cloud evidence collection failed: {evidence}")
        return 1

    parsed = json.loads(evidence)

    configuration = parsed["configuration"]
    deployment_logs = parsed["deployment_logs"]
    health_checks = parsed["health_checks"]
    deployment_reports = parsed["deployment_reports"]

    print(
        "Deployment workflow found:",
        configuration["workflow"]["exists"],
    )
    print(
        "Deployment files found:",
        sum(
            item["exists"]
            for item in configuration["deployment_files"]
        ),
    )
    print(f"Deployment logs: {len(deployment_logs)}")
    print(f"Health check reports: {len(health_checks)}")
    print(f"Deployment reports: {len(deployment_reports)}")
    print(f"Evidence characters: {len(evidence)}")

    assessment = None
    review = None
    error = None

    try:
        print(
            "\n[2/3] IMPLEMENTATION: "
            "Assessing deployment evidence..."
        )

        implementation_prompt = build_implementation_prompt(
            "Review the shared AWS EC2 deployment readiness "
            "for the ASD-02 Travel Agent application.",
            evidence,
        )

        print(
            "Implementation prompt characters:",
            len(implementation_prompt),
        )

        assessment = call_ai(
            "You are a cloud deployment evidence assessor. "
            "Use only supplied evidence. "
            "Distinguish configuration from successful execution. "
            "Never invent GitHub Actions or AWS EC2 results.",
            implementation_prompt,
        )

        print(assessment)

        print("\n[3/3] REVIEW: Validating deployment assessment...")

        review_prompt = build_review_prompt(
            assessment,
            evidence,
        )

        print("Review prompt characters:", len(review_prompt))

        review = call_ai(
            "You are an independent cloud deployment reviewer. "
            "Check the initial assessment against the original evidence. "
            "Do not infer deployment success from YAML or script presence. "
            "Explicitly identify unsupported claims.",
            review_prompt,
        )

        print(review)

    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        print(f"\nCloud review failed: {error}")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    review_status = (
        "completed" if assessment and review and not error
        else "failed"
    )

    report = {
        "review_id": str(uuid.uuid4()),
        "review_mode": "cloud",
        "selected_student": args.student,
        "deployment_scope": parsed["deployment_scope"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "configuration": configuration,
        "deployment_log_sources": [
            item["source"] for item in deployment_logs
        ],
        "health_check_sources": [
            item["source"] for item in health_checks
        ],
        "deployment_report_sources": [
            item["source"] for item in deployment_reports
        ],
        "deployment_verification_status": parsed[
            "deployment_verification_status"
        ],
        "evidence": parsed,
        "implementation": assessment,
        "review": review,
        "implementation_assessment": assessment,
        "review_recommendation": review,
        "review_status": review_status,
        "human_release_decision": "pending",
        "error": error,
    }

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )

    report_path = REPORT_DIR / (
        f"cloud_review_{timestamp}_{report['review_id'][:8]}.json"
    )

    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\nReview report saved: {report_path}")
    print(f"Review status: {report['review_status']}")
    print(
        "Deployment verification:",
        report["deployment_verification_status"],
    )
    print("Human release decision: pending")

    return 0 if review_status == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
