"""Student 1 - deployment smoke test through the public frontend.

Runs against the containers in CI and against the AWS deployment:

    python student-1/tests/cloud_smoke.py --frontend http://127.0.0.1:3001
    python student-1/tests/cloud_smoke.py --frontend http://<alb-dns>:3001 \\
        --json student-1/evidence/cloud/cloud-smoke.json

Every call goes browser-style through the frontend's /api proxy, so it
exercises frontend -> backend -> database. It creates, reads, updates and
deletes its own traveller and leaves the seed data alone. With
--expect-ai off (the cloud baseline) each AI route must refuse with 503.
"""

import argparse
import json
import sys
import time
import uuid
from pathlib import Path

import requests

results = []


def check(label, ok, detail=""):
    results.append({"check": label, "passed": bool(ok), "detail": detail})
    print(f"  {label:48s} -> {'PASS' if ok else 'FAIL'} {detail}")


def main():
    parser = argparse.ArgumentParser(description="Student 1 deployment smoke test")
    parser.add_argument("--frontend", required=True, help="Public frontend base URL")
    parser.add_argument("--expect-ai", choices=("off", "on"), default="off")
    parser.add_argument("--json", type=Path, help="Write the results here")
    args = parser.parse_args()
    base = args.frontend.rstrip("/")
    api = f"{base}/api"
    session = requests.Session()

    def call(method, path, **kwargs):
        try:
            return session.request(method, path, timeout=30, **kwargs)
        except requests.RequestException as exc:
            check(f"{method} {path}", False, type(exc).__name__)
            return None

    print(f"Student 1 smoke test against {base} (AI expected {args.expect_ai})")

    resp = call("GET", f"{base}/health")
    check("frontend /health", resp is not None and resp.ok)
    resp = call("GET", f"{api}/health")
    health = resp.json() if resp is not None and resp.ok else {}
    check("backend /health through the proxy", health.get("status") == "ok")
    if args.expect_ai == "off":
        flags = [k for k in ("ai_mode_enabled", "mcp_enabled", "rag_enabled",
                             "multi_agent_enabled") if health.get(k)]
        check("all AI services disabled", health and not flags, ", ".join(flags))

    resp = call("GET", base + "/")
    check("page renders", resp is not None and resp.ok and "Traveler Preferences" in resp.text)

    resp = call("GET", f"{api}/travelers")
    check("READ traveller list from the database",
          resp is not None and resp.ok and "<option value=" in resp.text)

    email = f"smoke.{uuid.uuid4().hex[:8]}@example.com"
    resp = call("POST", f"{api}/travelers", data={
        "name": "Smoke Test Traveller", "email": email,
        "home_location": "Sydney, Australia", "travel_style": "budget"})
    check("CREATE traveller", resp is not None and resp.ok
          and "Smoke Test Traveller" in resp.text)

    traveler_id = None
    resp = call("GET", f"{api}/travelers")
    if resp is not None and resp.ok:
        # The picker lists every traveller; the newest is the one just created.
        ids = [int(part.split("'")[0]) for part in resp.text.split("value='")[1:]]
        traveler_id = max(ids) if ids else None

    if traveler_id:
        resp = call("POST", f"{api}/travelers/{traveler_id}/update", data={
            "name": "Smoke Test Updated", "email": email,
            "home_location": "Melbourne, Australia", "travel_style": "luxury"})
        check("UPDATE traveller", resp is not None and resp.ok
              and "Smoke Test Updated" in resp.text)
        resp = call("POST", f"{api}/interests", data={
            "traveler_id": traveler_id, "interest_category": "Museums", "priority": 4})
        check("CREATE interest", resp is not None and resp.ok and "Museums" in resp.text)
        resp = call("POST", f"{api}/completeness/{traveler_id}")
        check("deterministic completeness check", resp is not None and resp.ok
              and "% complete" in resp.text)

        if args.expect_ai == "off":
            for label, path, data in (
                    ("AI-Mode summary refused", f"summarise/{traveler_id}", {}),
                    ("Multi-Agent refused", "multi-agent/workflow",
                     {"traveler_id": traveler_id}),
                    ("MCP refused", "mcp/tool", {"traveler_id": traveler_id,
                                                 "tool_name": "get_traveler_profile"}),
                    ("RAG refused", "rag/ask", {"question": "test"})):
                resp = call("POST", f"{api}/{path}", data=data)
                check(label, resp is not None and resp.status_code == 503)

        resp = call("POST", f"{api}/travelers/{traveler_id}/delete")
        check("DELETE traveller", resp is not None and resp.ok)
        resp = call("GET", f"{api}/profile/{traveler_id}")
        check("deleted traveller is gone", resp is not None and resp.status_code == 404)
    else:
        check("find the created traveller", False)

    passed = sum(r["passed"] for r in results)
    print(f"\n{passed} passed, {len(results) - passed} failed")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps({
            "frontend": base, "expect_ai": args.expect_ai,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "passed": passed, "failed": len(results) - passed, "results": results,
        }, indent=2), encoding="utf-8")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
