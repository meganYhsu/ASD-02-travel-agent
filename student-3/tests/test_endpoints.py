"""Student 3 - live endpoint smoke tests.

Run with the database API (6003) and backend (5003) already started:
    python tests/test_endpoints.py
Records pre/post-testing evidence for the technical report.
"""

import requests

DB = "http://127.0.0.1:6003"
BACKEND = "http://127.0.0.1:5003"

CHECKS = [
    ("DB: list categories",        "GET",  f"{DB}/categories",        None),
    ("DB: list expenses trip 1",   "GET",  f"{DB}/expenses?trip_id=1", None),
    ("DB: budget for trip 1",      "GET",  f"{DB}/budgets/1",          None),
    ("DB: recommendations",        "GET",  f"{DB}/recommendations",    None),
    ("DB: reject bad expense",     "POST", f"{DB}/expenses",           {}),
    ("Backend: dashboard trip 1",  "GET",  f"{BACKEND}/dashboard/1",   None),
]


def run():
    passed = failed = 0
    for label, method, url, body in CHECKS:
        try:
            resp = requests.request(method, url, json=body, timeout=5)
            expect_error = body == {}
            ok = (400 <= resp.status_code < 500) if expect_error else resp.ok
            status = "PASS" if ok else f"FAIL (HTTP {resp.status_code})"
        except requests.RequestException as exc:
            ok, status = False, f"FAIL ({exc})"
        print(f"  {label:32s} -> {status}")
        passed, failed = passed + ok, failed + (not ok)
    print(f"\n{passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    raise SystemExit(0 if run() else 1)
