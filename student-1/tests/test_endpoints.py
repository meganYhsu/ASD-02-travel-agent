"""Student 1 - live endpoint smoke tests.

Run with the database API (6001) and backend (5001) already started:
    python tests/test_endpoints.py
Records pre/post-testing evidence for the technical report.
"""

import os
import requests

DB = os.getenv("DB_API_URL", "http://127.0.0.1:6001")
BACKEND = os.getenv("BACKEND_URL", "http://127.0.0.1:5001")

CHECKS = [
    ("DB: list travelers",          "GET",    f"{DB}/travelers",             None),
    ("DB: traveler 1",              "GET",    f"{DB}/travelers/1",           None),
    ("DB: preferences for 1",       "GET",    f"{DB}/preferences/1",         None),
    ("DB: interests for 1",         "GET",    f"{DB}/interests?traveler_id=1", None),
    ("DB: needs for 1",             "GET",    f"{DB}/accessibility-needs?traveler_id=1", None),
    ("DB: preference set for 1",    "GET",    f"{DB}/preference-set/1",      None),
    ("DB: reject bad traveler",     "POST",   f"{DB}/travelers",             {}),
    ("DB: reject bad email",        "POST",   f"{DB}/travelers",
     {"name": "X", "email": "not-an-email", "home_location": "Y", "travel_style": "budget"}),
    ("DB: reject bad travel_style", "POST",   f"{DB}/travelers",
     {"name": "X", "email": "x@example.com", "home_location": "Y", "travel_style": "platinum"}),
    ("DB: reject inverted budget",  "POST",   f"{DB}/preferences",
     {"traveler_id": 1, "budget_min": 5000, "budget_max": 100}),
    ("DB: reject bad priority",     "POST",   f"{DB}/interests",
     {"traveler_id": 1, "interest_category": "Food", "priority": 9}),
    ("DB: 404 unknown traveler",    "GET",    f"{DB}/travelers/9999",        None),
    ("Backend: profile 1",          "GET",    f"{BACKEND}/profile/1",        None),
    ("Backend: traveler options",   "GET",    f"{BACKEND}/travelers",        None),
    ("Backend: preference set 1",   "GET",    f"{BACKEND}/preference-set/1", None),
    ("Backend: health",             "GET",    f"{BACKEND}/health",           None),
]


def expects_error(label, body):
    return "reject" in label or "404" in label


def run():
    passed = failed = 0
    for label, method, url, body in CHECKS:
        try:
            resp = requests.request(method, url, json=body, timeout=10)
            if expects_error(label, body):
                ok = 400 <= resp.status_code < 500
            else:
                ok = resp.ok
            status = "PASS" if ok else f"FAIL (HTTP {resp.status_code})"
        except requests.RequestException as exc:
            ok, status = False, f"FAIL ({exc})"
        print(f"  {label:32s} -> {status}")
        passed, failed = passed + ok, failed + (not ok)
    print(f"\n{passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    raise SystemExit(0 if run() else 1)
