"""Student 3 - budget review through the shared Multi-Agent server, from the terminal.

    Terminal -> budget backend (evidence) -> shared Multi-Agent server
             -> Planner -> Worker -> Reviewer -> human decision in this terminal
             -> budget backend -> shared server review + budget database

Run from the repository root (budget backend and shared server running):
    python student-3/tools/budget_review_cli.py --trip-id 1
    python student-3/tools/budget_review_cli.py --trip-id 1 --focus "food spending"
"""

import argparse
import os
import re
import sys
import textwrap

import requests

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:5003").rstrip("/")
SERVER_URL = os.getenv("MULTI_AGENT_SERVICE_URL", "http://127.0.0.1:6767").rstrip("/")
DECISIONS = {"1": "Accept", "2": "Partially Accept", "3": "Reject"}


def fail(message):
    sys.exit(f"ERROR: {message}")


def section(title, text):
    print(f"\n--- {title} " + "-" * max(0, 60 - len(title)))
    for paragraph in str(text or "(no output)").splitlines() or [""]:
        print(textwrap.fill(paragraph, 88) if paragraph.strip() else "")


def agent(title, result, field):
    status = result.get("status", "missing")
    label = f"{title} ({result.get('model', '?')}, {status})"
    section(label, result.get(field))
    if result.get("error"):
        print(f"error: {result['error']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--trip-id", type=int, default=1)
    parser.add_argument("--focus", default="")
    args = parser.parse_args()

    # 1. The same request the UI sends, built by the budget backend
    try:
        resp = requests.get(f"{BACKEND_URL}/multi-agent/evidence/{args.trip_id}", timeout=30)
        body = resp.json()
    except (requests.RequestException, ValueError) as exc:
        fail(f"budget backend unavailable at {BACKEND_URL}: {exc}")
    if resp.status_code >= 400:
        fail(body.get("error", f"HTTP {resp.status_code}"))
    if args.focus:
        body["user_request"] += f" Focus on: {args.focus[:200]}"

    spending = body["context"]["spending"]
    print(f"Service: {body['service']}  Task: {body['task']}")
    print(f"Request: {body['user_request']}")
    print(f"Evidence: spent {spending['spent']} of {body['context']['budget']['total_budget']} "
          f"{body['context']['budget']['currency']}, {spending['expense_count']} expenses")
    print("\nRunning Planner -> Worker -> Reviewer on the shared server "
          "(this can take a few minutes)...")

    # 2. Planner -> Worker -> Reviewer
    try:
        resp = requests.post(f"{SERVER_URL}/workflow", json=body, timeout=420)
        workflow = resp.json()
    except (requests.RequestException, ValueError) as exc:
        fail(f"shared Multi-Agent server unavailable at {SERVER_URL}: {exc}")
    if resp.status_code >= 400:
        fail(workflow.get("error", f"HTTP {resp.status_code}"))

    workflow_id = workflow["workflow_id"]
    print(f"\nWorkflow {workflow_id}  status: {workflow['status']}  "
          f"({workflow.get('duration_ms', 0) / 1000:.0f} s)")
    agent("1. PLANNER", workflow.get("planner_result") or {}, "plan")
    agent("2. WORKER", workflow.get("worker_result") or {}, "output")
    agent("3. REVIEWER", workflow.get("reviewer_result") or {}, "review")

    # 3. Human review - sent through the budget backend so the outcome is saved
    print("\nHUMAN REVIEW")
    for key, label in DECISIONS.items():
        print(f"{key} - {label}")
    while True:
        choice = input("Decision: ").strip()
        if choice in DECISIONS:
            break
        print("Enter 1, 2 or 3.")
    while True:
        reason = input("Reason (at least 20 characters): ").strip()
        if len(reason) >= 20:
            break
        print("Please write at least 20 characters.")
    evidence = input("Evidence (optional): ").strip()

    try:
        resp = requests.post(
            f"{BACKEND_URL}/multi-agent/workflow/{workflow_id}/decision",
            data={"decision": DECISIONS[choice], "reason": reason, "evidence": evidence},
            timeout=60,
        )
    except requests.RequestException as exc:
        fail(f"budget backend unavailable at {BACKEND_URL}: {exc}")
    text = re.sub(r"<[^>]+>", " ", resp.text)
    recorded = re.search(r"Human decision:\s*([A-Za-z ]+?)\s{2,}", text)
    saved = re.search(r"(Recommendation #\d+ saved[^.]*\.|The decision was recorded[^.]*\.)", text)
    refused = re.search(r"Decision not recorded:[^<\n]*", text)
    if refused:
        fail(refused.group(0).strip())
    print(f"\nRecorded: {recorded.group(1).strip() if recorded else DECISIONS[choice]}")
    if saved:
        print(saved.group(1))
    print(f"Logs: ai-services/multi-agent-server/workflow_history.jsonl, "
          f"coordination_audit.jsonl, human_reviews.jsonl (workflow {workflow_id})")


if __name__ == "__main__":
    main()
