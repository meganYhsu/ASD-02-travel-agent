"""Run the Student 1 preference review on the shared Multi-Agent server from
the terminal: Planner -> Worker -> Reviewer -> Human Review.

Needs the Student 1 backend (with MULTI_AGENT_ENABLED=true) and the shared
Multi-Agent server running. The evidence is the same body the frontend sends,
taken from the backend's /multi-agent/evidence/<traveler_id> route.

    python student-1/tools/preferences_review_cli.py --traveler-id 1
    python student-1/tools/preferences_review_cli.py --traveler-id 1 \\
        --decision Accept --reason "Brief matches the saved profile exactly." \\
        --save student-1/evidence/multi-agent/cli-run.json
"""

import argparse
import json
import sys
import textwrap
from pathlib import Path

import requests

DECISIONS = ("Accept", "Partially Accept", "Reject")
MIN_REASON = 20


def fail(message):
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def call(method, url, timeout, payload=None):
    try:
        resp = requests.request(method, url, json=payload, timeout=timeout)
    except requests.RequestException as exc:
        fail(f"{url} is unavailable ({type(exc).__name__}).")
    try:
        data = resp.json()
    except ValueError:
        fail(f"{url} returned HTTP {resp.status_code} without JSON.")
    if not resp.ok:
        fail(f"{url} returned HTTP {resp.status_code}: {data.get('error', data)}")
    return data


def show(title, result, key):
    result = result or {}
    print(f"\n=== {title}  [{result.get('status', 'unknown')}] {result.get('model', '')}")
    print(textwrap.indent(str(result.get(key, "")).strip(), "  "))
    if result.get("error"):
        print(f"  error: {result['error']}")


def ask_decision():
    print("\n=== 4. Human review")
    for number, decision in enumerate(DECISIONS, 1):
        print(f"  {number}. {decision}")
    while True:
        choice = input("Decision [1-3]: ").strip()
        if choice in ("1", "2", "3"):
            decision = DECISIONS[int(choice) - 1]
            break
    while True:
        reason = input(f"Reason or correction (min {MIN_REASON} chars): ").strip()
        if len(reason) >= MIN_REASON:
            break
    evidence = input("Evidence checked (optional): ").strip()
    return decision, reason, evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--traveler-id", type=int, required=True)
    parser.add_argument("--request", default="",
                        help="What the agents should check (default: the feature's standard review).")
    parser.add_argument("--backend-url", default="http://127.0.0.1:5001")
    parser.add_argument("--multi-agent-url", default="http://127.0.0.1:6767")
    parser.add_argument("--timeout", type=int, default=420)
    parser.add_argument("--decision", choices=DECISIONS,
                        help="Record this decision without prompting.")
    parser.add_argument("--reason", default="")
    parser.add_argument("--evidence", default="")
    parser.add_argument("--save", type=Path, help="Write the final workflow JSON here.")
    args = parser.parse_args()
    if args.decision and len(args.reason.strip()) < MIN_REASON:
        parser.error(f"--reason must be at least {MIN_REASON} characters with --decision")

    backend = args.backend_url.rstrip("/")
    agents = args.multi_agent_url.rstrip("/")

    print(f"PLAN   fetching traveller {args.traveler_id}'s preference set from {backend}")
    params = f"?user_request={requests.utils.quote(args.request)}" if args.request else ""
    body = call("GET", f"{backend}/multi-agent/evidence/{args.traveler_id}{params}", 30)
    context = body["context"]
    print(f"       {context['traveler']['name']} - completeness "
          f"{context['completeness']['score']}%, {len(context['interests'])} interests, "
          f"{len(context['accessibility_needs'])} needs")

    print(f"ACT    POST {agents}/workflow (service={body['service']}, task={body['task']})")
    print("       waiting for the Planner, Worker and Reviewer agents...")
    workflow = call("POST", f"{agents}/workflow", args.timeout, body)
    workflow_id = workflow["workflow_id"]
    print(f"OBSERVE workflow {workflow_id} - {workflow['status']} "
          f"in {workflow.get('duration_ms', 0) / 1000:.1f}s")

    show("1. Planner", workflow.get("planner_result"), "plan")
    show("2. Worker", workflow.get("worker_result"), "output")
    show("3. Reviewer", workflow.get("reviewer_result"), "review")

    if args.decision:
        decision, reason, evidence = args.decision, args.reason.strip(), args.evidence.strip()
        print(f"\n=== 4. Human review\n  {decision}: {reason}")
    else:
        decision, reason, evidence = ask_decision()

    workflow = call("POST", f"{agents}/workflow/{workflow_id}/review", 30,
                    {"decision": decision, "reason": reason, "evidence": evidence})
    recorded = workflow["human_decision"]
    print(f"\nADAPT  human decision {recorded['decision']} recorded at {recorded['timestamp']}")

    if args.save:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        args.save.write_text(json.dumps(workflow, indent=2), encoding="utf-8")
        print(f"       saved to {args.save}")


if __name__ == "__main__":
    main()
