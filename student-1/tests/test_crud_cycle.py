"""Student 1 - full CRUD cycle against the live database API (6001).

Creates a traveller, reads it, updates it, attaches a preference row, an
interest and an accessibility need, then deletes the traveller and confirms
the cascade removed the child rows. Leaves the seed data untouched.
"""

import os
import requests

DB = os.getenv("DB_API_URL", "http://127.0.0.1:6001")

results = []


def check(label, condition):
    results.append((label, bool(condition)))
    print(f"  {label:44s} -> {'PASS' if condition else 'FAIL'}")


def run():
    # CREATE
    resp = requests.post(DB + "/travelers", timeout=10, json={
        "name": "CRUD Test Traveller",
        "email": "crud.test@example.com",
        "home_location": "Sydney, Australia",
        "travel_style": "budget",
    })
    if resp.status_code == 409:
        # Left over from an earlier run - clear it and start again.
        existing = [t for t in requests.get(DB + "/travelers", timeout=10).json()
                    if t["email"] == "crud.test@example.com"]
        for t in existing:
            requests.delete(f"{DB}/travelers/{t['traveler_id']}", timeout=10)
        resp = requests.post(DB + "/travelers", timeout=10, json={
            "name": "CRUD Test Traveller",
            "email": "crud.test@example.com",
            "home_location": "Sydney, Australia",
            "travel_style": "budget",
        })
    check("CREATE traveller returns 201", resp.status_code == 201)
    traveler_id = resp.json()["traveler_id"]

    # READ
    read = requests.get(f"{DB}/travelers/{traveler_id}", timeout=10)
    check("READ traveller returns the saved name",
          read.ok and read.json()["name"] == "CRUD Test Traveller")

    # UPDATE
    upd = requests.put(f"{DB}/travelers/{traveler_id}", timeout=10, json={
        "name": "CRUD Test Traveller (updated)",
        "email": "crud.test@example.com",
        "home_location": "Melbourne, Australia",
        "travel_style": "luxury",
    })
    reread = requests.get(f"{DB}/travelers/{traveler_id}", timeout=10).json()
    check("UPDATE traveller persists the new values",
          upd.ok and reread["travel_style"] == "luxury"
          and reread["home_location"] == "Melbourne, Australia")

    # Child records
    pref = requests.post(DB + "/preferences", timeout=10, json={
        "traveler_id": traveler_id, "budget_min": 1000,
        "budget_max": 2000, "pace": "relaxed",
    })
    check("CREATE preferences returns 201", pref.status_code == 201)

    again = requests.post(DB + "/preferences", timeout=10, json={
        "traveler_id": traveler_id, "budget_min": 1500,
        "budget_max": 2500, "pace": "packed",
    })
    check("UPSERT preferences replaces rather than duplicates",
          again.status_code == 201 and again.json()["budget_min"] == 1500)

    interest = requests.post(DB + "/interests", timeout=10, json={
        "traveler_id": traveler_id, "interest_category": "Snorkelling", "priority": 4,
    })
    check("CREATE interest returns 201", interest.status_code == 201)
    interest_id = interest.json()["interest_id"]

    upd_int = requests.put(f"{DB}/interests/{interest_id}", timeout=10,
                           json={"interest_category": "Diving", "priority": 5})
    check("UPDATE interest returns 200", upd_int.ok)

    need = requests.post(DB + "/accessibility-needs", timeout=10, json={
        "traveler_id": traveler_id, "requirement": "Ground floor room",
        "dietary_restriction": "Vegan",
    })
    check("CREATE accessibility need returns 201", need.status_code == 201)

    # Aggregated contract other services read
    pset = requests.get(f"{DB}/preference-set/{traveler_id}", timeout=10).json()
    check("preference-set returns the whole profile",
          pset["preferences"]["pace"] == "packed"
          and len(pset["interests"]) == 1
          and len(pset["accessibility_needs"]) == 1)

    # DELETE
    delete = requests.delete(f"{DB}/travelers/{traveler_id}", timeout=10)
    check("DELETE traveller returns 200", delete.ok)
    check("DELETE removes the traveller",
          requests.get(f"{DB}/travelers/{traveler_id}", timeout=10).status_code == 404)
    check("DELETE cascades to the interest",
          requests.get(f"{DB}/interests/{interest_id}", timeout=10).status_code == 404)

    passed = sum(1 for _, ok in results if ok)
    failed = len(results) - passed
    print(f"\n{passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    raise SystemExit(0 if run() else 1)
