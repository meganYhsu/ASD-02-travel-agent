"""Release 2 post-commit endpoint tests for the Student 1 backend/API.

The two endpoint functions under test (student-1/backend/app.py):

    1. add_traveler      POST /travelers                         (Create)
    2. update_traveler   POST /travelers/<traveler_id>/update    (Update)

Each request goes through the real backend and the real database API on a
fresh seeded SQLite file (see conftest.py), so a passing test means the row
really was written, not just that the backend answered 200.
"""

import pytest

NEW_TRAVELER = {
    "name": "Release Two Tester",
    "email": "release.two@example.com",
    "home_location": "Melbourne, Australia",
    "travel_style": "budget",
}


def find_by_email(db_api, email):
    return [t for t in db_api.get("/travelers").get_json() if t["email"] == email]


# ------------------------------------------------------ 1. POST /travelers
class TestAddTraveler:

    def test_creates_traveler_and_returns_profile(self, backend_client, db_api):
        before = len(db_api.get("/travelers").get_json())

        resp = backend_client.post("/travelers", data=NEW_TRAVELER)

        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "<h3>Release Two Tester</h3>" in html
        assert "Melbourne, Australia" in html
        assert len(db_api.get("/travelers").get_json()) == before + 1
        saved = find_by_email(db_api, NEW_TRAVELER["email"])
        assert len(saved) == 1
        assert saved[0]["travel_style"] == "budget"

    def test_trims_whitespace_before_saving(self, backend_client, db_api):
        padded = {**NEW_TRAVELER, "name": "  Padded Name  ",
                  "home_location": "  Perth  "}

        resp = backend_client.post("/travelers", data=padded)

        assert resp.status_code == 200
        saved = find_by_email(db_api, NEW_TRAVELER["email"])[0]
        assert saved["name"] == "Padded Name"
        assert saved["home_location"] == "Perth"

    @pytest.mark.parametrize("missing", ["name", "email", "home_location"])
    def test_rejects_missing_required_field(self, backend_client, db_api, missing, calls):
        before = len(db_api.get("/travelers").get_json())

        resp = backend_client.post("/travelers", data={**NEW_TRAVELER, missing: "  "})

        assert resp.status_code == 400
        assert "required" in resp.get_data(as_text=True)
        assert len(db_api.get("/travelers").get_json()) == before
        assert calls == []  # validated before the database is called

    def test_rejects_invalid_email_from_database_validation(self, backend_client):
        resp = backend_client.post("/travelers",
                                   data={**NEW_TRAVELER, "email": "not-an-email"})

        assert resp.status_code == 400
        assert "class='error'" in resp.get_data(as_text=True)

    def test_rejects_duplicate_email(self, backend_client, db_api):
        resp = backend_client.post(
            "/travelers", data={**NEW_TRAVELER, "email": "traveller.one@example.com"})

        assert resp.status_code == 409
        assert "already exists" in resp.get_data(as_text=True)
        assert len(find_by_email(db_api, "traveller.one@example.com")) == 1

    def test_escapes_html_in_name(self, backend_client):
        resp = backend_client.post(
            "/travelers", data={**NEW_TRAVELER, "name": "<script>alert(1)</script>"})

        html = resp.get_data(as_text=True)
        assert resp.status_code == 200
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_database_down_returns_503(self, db_down):
        resp = db_down.post("/travelers", data=NEW_TRAVELER)

        assert resp.status_code == 503
        assert "Could not save the traveller" in resp.get_data(as_text=True)


# ------------------------------------ 2. POST /travelers/<id>/update
class TestUpdateTraveler:

    def test_updates_every_field(self, backend_client, db_api):
        changes = {"name": "Traveller One Renamed", "email": "one.renamed@example.com",
                   "home_location": "Brisbane, Australia", "travel_style": "luxury"}

        resp = backend_client.post("/travelers/1/update", data=changes)

        assert resp.status_code == 200
        assert "<h3>Traveller One Renamed</h3>" in resp.get_data(as_text=True)
        saved = db_api.get("/travelers/1").get_json()
        assert {k: saved[k] for k in changes} == changes

    def test_leaves_child_rows_untouched(self, backend_client, db_api):
        before = db_api.get("/preference-set/1").get_json()

        backend_client.post("/travelers/1/update",
                            data={**NEW_TRAVELER, "email": "traveller.one@example.com"})

        after = db_api.get("/preference-set/1").get_json()
        assert after["preferences"] == before["preferences"]
        assert after["interests"] == before["interests"]
        assert after["accessibility_needs"] == before["accessibility_needs"]

    def test_unknown_traveler_returns_404(self, backend_client):
        resp = backend_client.post("/travelers/9999/update", data=NEW_TRAVELER)

        assert resp.status_code == 404
        assert "not found" in resp.get_data(as_text=True)

    def test_rejects_missing_required_field(self, backend_client, db_api, calls):
        original = db_api.get("/travelers/1").get_json()

        resp = backend_client.post("/travelers/1/update",
                                   data={**NEW_TRAVELER, "name": ""})

        assert resp.status_code == 400
        assert db_api.get("/travelers/1").get_json() == original
        assert calls == []

    def test_rejects_invalid_travel_style(self, backend_client, db_api):
        original = db_api.get("/travelers/1").get_json()

        resp = backend_client.post("/travelers/1/update",
                                   data={**NEW_TRAVELER, "travel_style": "platinum"})

        assert resp.status_code == 400
        assert db_api.get("/travelers/1").get_json() == original

    def test_rejects_email_owned_by_another_traveler(self, backend_client, db_api):
        other = db_api.get("/travelers/2").get_json()["email"]

        resp = backend_client.post("/travelers/1/update",
                                   data={**NEW_TRAVELER, "email": other})

        assert resp.status_code == 409
        assert db_api.get("/travelers/1").get_json()["email"] != other

    def test_database_down_returns_503(self, db_down):
        resp = db_down.post("/travelers/1/update", data=NEW_TRAVELER)

        assert resp.status_code == 503
        assert "Could not update the traveller" in resp.get_data(as_text=True)
