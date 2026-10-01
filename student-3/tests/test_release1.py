"""Release 1 checks that hold without the shared MCP and RAG servers.

In CI the two modes are switched off (MCP_ENABLED=false, RAG_ENABLED=false)
because the shared servers run locally and are not containerised. Three
things are still verifiable there:

  1. /health reports the Release 1 configuration and the tool boundary.
  2. A tool outside this feature's boundary is refused with HTTP 403 even
     with MCP mode off, because the boundary is enforced before the mode
     flag and before the shared MCP server is contacted.
  3. With a mode off, a permitted MCP tool and a RAG query degrade to
     HTTP 503 with an explanatory message instead of failing.

The script also passes when the shared servers are running locally: the
checks that only apply with a mode off are skipped.

Run:  python tests/test_release1.py      (from student-3/)
"""

import os
import sys

import requests

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:5003")
MCP_ENABLED = os.getenv("MCP_ENABLED", "true").lower() == "true"
RAG_ENABLED = os.getenv("RAG_ENABLED", "true").lower() == "true"

EXPECTED_TOOLS = {
    "total_activity_count",
    "total_activities_count_a_day",
    "get_trip_activities_desc",
}

failures = []
checks = 0


def check(label, condition, detail=""):
    global checks
    checks += 1
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}" + (f" -> {detail}" if detail else ""))
    if not condition:
        failures.append(label)


def main():
    print("Release 1 checks")
    print(f"  backend={BACKEND_URL} "
          f"mcp_enabled={MCP_ENABLED} rag_enabled={RAG_ENABLED}")
    print()

    # ---------------------------------------------- configuration
    try:
        health = requests.get(f"{BACKEND_URL}/health", timeout=10).json()
    except Exception as exc:
        print(f"  [FAIL] /health unreachable -> {exc}")
        sys.exit(1)

    check("health reports the shared MCP server",
          bool(health.get("mcp_server")), health.get("mcp_server"))
    check("health reports the shared RAG server",
          bool(health.get("rag_server")), health.get("rag_server"))

    allowed = set(health.get("allowed_mcp_tools") or [])
    check("health reports the tool boundary",
          allowed == EXPECTED_TOOLS, ", ".join(sorted(allowed)))

    # ------------------------------- tool boundary, every environment
    # The backend accepts a form post from the frontend and a JSON body
    # from the shared agentic loop, so both are checked.
    for label, kwargs in (
        ("form body", {"data": {"trip_id": 1}}),
        ("JSON body", {"json": {"trip_id": 1}}),
    ):
        resp = requests.post(
            f"{BACKEND_URL}/mcp/get_travel_requirements",
            timeout=10, **kwargs)

        check(f"tool outside the boundary refused with 403 ({label})",
              resp.status_code == 403, f"HTTP {resp.status_code}")
        check(f"refusal names the feature boundary ({label})",
              "outside the Budget" in resp.text)
        check(f"refusal states the MCP server was not contacted ({label})",
              "not contacted" in resp.text)

    # --------------------------------- degradation with a mode off
    if not MCP_ENABLED:
        resp = requests.post(f"{BACKEND_URL}/mcp/total_activity_count",
                             data={"trip_id": 1}, timeout=10)
        check("permitted tool degrades to 503 with MCP off",
              resp.status_code == 503, f"HTTP {resp.status_code}")
        check("MCP degradation message explains the cause",
              "MCP_ENABLED=false" in resp.text)

        resp = requests.get(f"{BACKEND_URL}/mcp/tools", timeout=10)
        check("tool listing degrades to 503 with MCP off",
              resp.status_code == 503, f"HTTP {resp.status_code}")
    else:
        print("  [SKIP] MCP degradation checks (MCP_ENABLED=true)")

    if not RAG_ENABLED:
        resp = requests.post(f"{BACKEND_URL}/rag/query",
                             data={"question": "anything"}, timeout=10)
        check("RAG query degrades to 503 with RAG off",
              resp.status_code == 503, f"HTTP {resp.status_code}")
        check("RAG degradation message explains the cause",
              "RAG_ENABLED=false" in resp.text)
    else:
        print("  [SKIP] RAG degradation checks (RAG_ENABLED=true)")

    # ------------------------------------------- input validation
    resp = requests.post(f"{BACKEND_URL}/rag/query", data={}, timeout=10)
    check("RAG query with no question is rejected",
          resp.status_code in (400, 503), f"HTTP {resp.status_code}")

    print()
    print(f"{checks - len(failures)}/{checks} checks passed")

    if failures:
        print()
        for label in failures:
            print(f"  failed: {label}")
        sys.exit(1)

    print("Release 1 checks passed")


if __name__ == "__main__":
    main()