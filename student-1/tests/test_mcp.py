"""Student 1 - shared MCP integration checks.

Run with the database API (6001) and backend (5001) already started:
    python tests/test_mcp.py

MCP_ENABLED=false (CI): the backend must refuse cleanly with "MCP is disabled".
MCP_ENABLED=true (local): the shared MCP server (7004) must also be running,
and every student-1 tool must return a structured result.
"""

import os
import requests

BACKEND = os.getenv("BACKEND_URL", "http://127.0.0.1:5001")
MCP_ENABLED = os.getenv("MCP_ENABLED", "true").lower() not in ("false", "0", "no")

TOOLS = ("get_traveler_profile", "get_traveler_interests", "get_accessibility_needs")


def call(tool_name, traveler_id):
    return requests.post(f"{BACKEND}/mcp/tool",
                         data={"tool_name": tool_name, "traveler_id": traveler_id},
                         timeout=20)


def check(label, ok):
    print(f"  {label:44s} -> {'PASS' if ok else 'FAIL'}")
    return ok


def run():
    results = [
        check("reject tool outside student-1 boundary",
              call("total_activity_count", 1).status_code == 400),
        check("reject missing traveler_id",
              call("get_traveler_profile", "").status_code == 400),
        check("reject non-numeric traveler_id",
              call("get_traveler_profile", "abc").status_code == 400),
    ]

    if MCP_ENABLED:
        for tool in TOOLS:
            resp = call(tool, 1)
            results.append(check(f"{tool} returns a result",
                                 resp.status_code == 200 and tool in resp.text))
        resp = call("get_traveler_profile", 9999)
        results.append(check("unknown traveler reported by tool",
                             resp.status_code == 200 and "Traveler not found" in resp.text))
    else:
        resp = call("get_traveler_profile", 1)
        results.append(check("MCP disabled response",
                             resp.status_code == 503 and "MCP is disabled" in resp.text))

    passed = sum(results)
    print(f"\n{passed} passed, {len(results) - passed} failed "
          f"(MCP {'enabled' if MCP_ENABLED else 'disabled'})")
    return passed == len(results)


if __name__ == "__main__":
    raise SystemExit(0 if run() else 1)
