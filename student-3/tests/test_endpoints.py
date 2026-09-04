import requests

DB = "http://localhost:6003"
BACKEND = "http://localhost:5003"

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
        if ok:
            passed += 1
        else:
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    run()