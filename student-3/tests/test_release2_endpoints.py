"""Release 2 post-commit CI tests - two backend/API endpoint functions.

    1. GET  /dashboard/<trip_id>   dashboard()    budget totals per trip
    2. POST /expenses              add_expense()  create an expense (CRUD)

Each endpoint is tested for its normal result, invalid input, a missing
record and an unavailable database. The backend talks to the real database
API (in-process, fresh SQLite file per test), so the numbers checked here
are the numbers the UI shows.

Run from student-3/:
    python -m pytest tests/test_release2_endpoints.py -v
"""

from datetime import date

import pytest


def db_totals(db_api, trip_id):
    budget = db_api.get(f"/budgets/{trip_id}").get_json()
    expenses = db_api.get(f"/expenses?trip_id={trip_id}").get_json()
    spent = sum(e["amount"] for e in expenses)
    return budget["total_budget"], spent, expenses


# ---------------------------------------------------- 1. GET /dashboard/<id>
def test_dashboard_shows_budget_spent_and_remaining(backend_client, db_api):
    total, spent, expenses = db_totals(db_api, 1)

    resp = backend_client.get("/dashboard/1")
    html = resp.get_data(as_text=True)

    assert resp.status_code == 200
    assert f"Total: {total:.2f} AUD" in html
    assert f"Spent: {spent:.2f}" in html
    assert f"Remaining: {total - spent:.2f}" in html
    for e in expenses:
        assert e["category_name"] in html


def test_dashboard_lists_categories_by_amount_spent(backend_client, db_api):
    _, _, expenses = db_totals(db_api, 1)
    per_cat = {}
    for e in expenses:
        per_cat[e["category_name"]] = per_cat.get(e["category_name"], 0) + e["amount"]
    expected_order = sorted(per_cat, key=per_cat.get, reverse=True)

    html = backend_client.get("/dashboard/1").get_data(as_text=True)
    summary_table = html.split("<h4>Expenses</h4>")[0]
    positions = [summary_table.index(f"<td>{name}</td>") for name in expected_order]

    assert positions == sorted(positions)


def test_dashboard_unknown_trip_returns_404(backend_client):
    resp = backend_client.get("/dashboard/999")

    assert resp.status_code == 404
    assert "No budget set for trip 999" in resp.get_data(as_text=True)


def test_dashboard_escapes_user_text(backend_client, db_api):
    db_api.post("/expenses", json={"trip_id": 1, "category_id": 2,
                                   "description": "<script>alert(1)</script>",
                                   "amount": 1, "expense_date": "2026-09-04"})

    html = backend_client.get("/dashboard/1").get_data(as_text=True)

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_dashboard_database_down_returns_503(db_down):
    resp = db_down.get("/dashboard/1")

    assert resp.status_code == 503
    assert "unavailable" in resp.get_data(as_text=True)


# ------------------------------------------------------- 2. POST /expenses
def test_add_expense_saves_it_and_returns_updated_dashboard(backend_client, db_api, calls):
    total, spent_before, before = db_totals(db_api, 1)

    resp = backend_client.post("/expenses", data={
        "trip_id": "1", "category_id": "2", "description": "Okonomiyaki lunch",
        "amount": "18.50", "expense_date": "2026-09-04"})

    _, spent_after, after = db_totals(db_api, 1)
    html = resp.get_data(as_text=True)
    sent = [c["json"] for c in calls if c["method"] == "POST"][0]

    assert resp.status_code == 200
    assert sent == {"trip_id": 1, "category_id": 2, "description": "Okonomiyaki lunch",
                    "amount": 18.5, "expense_date": "2026-09-04"}
    assert len(after) == len(before) + 1
    assert spent_after == pytest.approx(spent_before + 18.5)
    assert "Okonomiyaki lunch" in html
    assert f"Spent: {spent_after:.2f}" in html
    assert f"Remaining: {total - spent_after:.2f}" in html


def test_add_expense_without_date_uses_today(backend_client, db_api):
    backend_client.post("/expenses", data={"trip_id": "1", "category_id": "3",
                                           "description": "Taxi", "amount": "25"})

    _, _, expenses = db_totals(db_api, 1)
    saved = [e for e in expenses if e["description"] == "Taxi"][0]

    assert saved["expense_date"] == date.today().isoformat()


@pytest.mark.parametrize("form", [
    {"trip_id": "1", "category_id": "2", "amount": "10"},                       # no description
    {"trip_id": "1", "category_id": "2", "description": "   ", "amount": "10"},  # blank
    {"trip_id": "1", "category_id": "2", "description": "Tea"},                  # no amount
    {"trip_id": "1", "category_id": "2", "description": "Tea", "amount": "ten"}, # not a number
])
def test_add_expense_rejects_invalid_input(backend_client, db_api, calls, form):
    _, _, before = db_totals(db_api, 1)

    resp = backend_client.post("/expenses", data=form)

    _, _, after = db_totals(db_api, 1)
    assert resp.status_code == 400
    assert "required" in resp.get_data(as_text=True)
    assert not [c for c in calls if c["method"] == "POST"]   # DB API never called
    assert len(after) == len(before)


def test_add_expense_database_down_returns_503(db_down):
    resp = db_down.post("/expenses", data={"trip_id": "1", "category_id": "2",
                                           "description": "Tea", "amount": "4"})

    assert resp.status_code == 503
    assert "Could not save the expense" in resp.get_data(as_text=True)
