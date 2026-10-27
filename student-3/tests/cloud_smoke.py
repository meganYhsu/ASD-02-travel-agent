"""Student 3 - deployment smoke test through the public frontend.

Everything goes through the frontend's /api proxy, exactly as a browser
would, so one run proves:

  1. availability    the frontend and its /health answer
  2. communication   frontend -> backend -> database (backend /health, dashboard)
  3. CRUD            create, read, update and delete one expense
  4. cloud baseline  AI-Mode, MCP, RAG and Multi-Agent are disabled (HTTP 503)
  5. performance     average response time over repeated dashboard requests

Run (from student-3/):
    python tests/cloud_smoke.py --frontend http://<load-balancer-dns>:3003
    python tests/cloud_smoke.py --frontend http://localhost:3003 --expect-ai on
    python tests/cloud_smoke.py --frontend ... --json cloud-smoke.json

Exit code 0 only when every check passes. The JSON file is the evidence
input for the Cloud Deployment Review mode of the agentic loop.
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone

import requests

TIMEOUT = 30
AI_ROUTES = [
    ("AI-Mode", "POST", "/api/analyse/{trip}", "AI_MODE_ENABLED=false"),
    ("MCP", "GET", "/api/mcp/tools", "MCP_ENABLED=false"),
    ("RAG", "POST", "/api/rag/query", "RAG_ENABLED=false"),
    ("Multi-Agent", "POST", "/api/multi-agent/budget-review/{trip}",
     "MULTI_AGENT_ENABLED=false"),
]
AI_FLAGS = ("ai_mode_enabled", "mcp_enabled", "rag_enabled", "multi_agent_enabled")


class Smoke:
    def __init__(self, base):
        self.base = base.rstrip("/")
        self.results = []

    def call(self, method, path, **kwargs):
        started = time.perf_counter()
        resp = requests.request(method, f"{self.base}{path}", timeout=TIMEOUT, **kwargs)
        return resp, (time.perf_counter() - started) * 1000

    def check(self, group, name, passed, detail="", ms=None):
        self.results.append({"group": group, "check": name, "passed": bool(passed),
                             "detail": detail, "ms": round(ms, 1) if ms else None})
        timing = f" ({ms:.0f} ms)" if ms else ""
        print(f"  {'PASS' if passed else 'FAIL'}  {group:14s} {name}{timing}"
              + (f" - {detail}" if detail and not passed else ""))
        return passed

    def safe(self, group, name, fn):
        try:
            return fn()
        except requests.RequestException as exc:
            return self.check(group, name, False, f"request failed: {exc}")


def row_for(html, text):
    """The dashboard table row that contains the given description."""
    for row in html.split("<tr>"):
        if f"<td>{text}</td>" in row:
            return row
    return None


def run(base, trip, expect_ai, repeats):
    s = Smoke(base)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    description = f"Cloud smoke test {stamp}"
    state = {}

    print(f"Student 3 smoke test against {s.base} (trip {trip}, AI expected {expect_ai})\n")

    # 1. availability
    def page():
        resp, ms = s.call("GET", "/")
        return s.check("availability", "frontend page", resp.status_code == 200
                       and "Budget &amp; Expense Tracking" in resp.text,
                       f"HTTP {resp.status_code}", ms)
    s.safe("availability", "frontend page", page)

    def frontend_health():
        resp, ms = s.call("GET", "/health")
        return s.check("availability", "frontend /health", resp.status_code == 200,
                       f"HTTP {resp.status_code}", ms)
    s.safe("availability", "frontend /health", frontend_health)

    # 2. communication
    def backend_health():
        resp, ms = s.call("GET", "/api/health")
        data = resp.json() if resp.status_code == 200 else {}
        state["flags"] = {k: data.get(k) for k in AI_FLAGS}
        return s.check("communication", "frontend -> backend /health",
                       resp.status_code == 200, f"HTTP {resp.status_code}", ms)
    s.safe("communication", "frontend -> backend /health", backend_health)

    def dashboard():
        resp, ms = s.call("GET", f"/api/dashboard/{trip}")
        return s.check("communication", "backend -> database (dashboard)",
                       resp.status_code == 200 and f"Trip {trip} budget" in resp.text,
                       f"HTTP {resp.status_code}", ms)
    s.safe("communication", "backend -> database (dashboard)", dashboard)

    # 3. CRUD
    def create():
        resp, ms = s.call("POST", "/api/expenses", data={
            "trip_id": trip, "category_id": 2, "description": description,
            "amount": "12.30", "expense_date": datetime.now().date().isoformat()})
        row = row_for(resp.text, description)
        match = re.search(r"/api/expenses/(\d+)/edit", row or "")
        if match:
            state["expense_id"] = match.group(1)
        return s.check("crud", "create expense", resp.status_code == 200 and match,
                       f"HTTP {resp.status_code}, row found: {bool(row)}", ms)
    s.safe("crud", "create expense", create)

    def read():
        resp, ms = s.call("GET", f"/api/dashboard/{trip}")
        return s.check("crud", "read expense on dashboard",
                       resp.status_code == 200 and row_for(resp.text, description),
                       f"HTTP {resp.status_code}", ms)
    s.safe("crud", "read expense on dashboard", read)

    def update():
        expense_id = state.get("expense_id")
        if not expense_id:
            return s.check("crud", "update expense", False, "no expense id from create")
        resp, ms = s.call("POST", f"/api/expenses/{expense_id}/update", data={
            "trip_id": trip, "category_id": 3, "description": description,
            "amount": "45.60", "expense_date": datetime.now().date().isoformat()})
        row = row_for(resp.text, description) or ""
        return s.check("crud", "update expense", resp.status_code == 200
                       and "<td>45.60</td>" in row and "<td>Transport</td>" in row,
                       f"HTTP {resp.status_code}", ms)
    s.safe("crud", "update expense", update)

    def delete():
        expense_id = state.get("expense_id")
        if not expense_id:
            return s.check("crud", "delete expense", False, "no expense id from create")
        resp, ms = s.call("POST", f"/api/expenses/{expense_id}/delete",
                          data={"trip_id": trip})
        return s.check("crud", "delete expense", resp.status_code == 200
                       and row_for(resp.text, description) is None,
                       f"HTTP {resp.status_code}", ms)
    s.safe("crud", "delete expense", delete)

    # 4. cloud baseline: AI services off
    flags = state.get("flags") or {}
    if expect_ai == "off":
        s.check("ai-baseline", "backend reports all AI flags off",
                bool(flags) and all(v is False for v in flags.values()),
                json.dumps(flags))
        for label, method, path, message in AI_ROUTES:
            def disabled(label=label, method=method, path=path, message=message):
                resp, ms = s.call(method, path.format(trip=trip),
                                  data={"question": "What is my budget?"})
                return s.check("ai-baseline", f"{label} disabled (503)",
                               resp.status_code == 503 and message in resp.text,
                               f"HTTP {resp.status_code}", ms)
            s.safe("ai-baseline", f"{label} disabled (503)", disabled)
    else:
        s.check("ai-baseline", "backend reports all AI flags on",
                bool(flags) and all(v is True for v in flags.values()),
                json.dumps(flags))

    # 5. performance
    times, failures = [], 0
    for _ in range(repeats):
        try:
            resp, ms = s.call("GET", f"/api/dashboard/{trip}")
            if resp.status_code == 200:
                times.append(ms)
            else:
                failures += 1
        except requests.RequestException:
            failures += 1
    average = sum(times) / len(times) if times else 0
    s.check("performance", f"{len(times)}/{repeats} dashboard requests succeeded",
            failures == 0, f"{failures} failed", average)

    passed = sum(r["passed"] for r in s.results)
    total = len(s.results)
    print(f"\n{passed}/{total} checks passed - average dashboard response "
          f"{average:.0f} ms over {len(times)} requests")
    return {
        "service": "student-3 Budget & Expense Tracking",
        "frontend": s.base,
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "expect_ai": expect_ai,
        "ai_flags": flags,
        "passed": passed,
        "total": total,
        "average_response_ms": round(average, 1),
        "successful_requests": len(times),
        "failed_requests": failures,
        "checks": s.results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--frontend", required=True,
                        help="public frontend URL, e.g. http://<alb-dns>:3003")
    parser.add_argument("--trip-id", type=int, default=1)
    parser.add_argument("--expect-ai", choices=["off", "on"], default="off")
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--json", help="write the results to this file")
    args = parser.parse_args()

    report = run(args.frontend, args.trip_id, args.expect_ai, args.repeats)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        print(f"Results written to {args.json}")
    sys.exit(0 if report["passed"] == report["total"] else 1)


if __name__ == "__main__":
    main()
