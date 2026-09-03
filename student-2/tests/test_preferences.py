"""CRUD and constraint coverage for the Preferences table."""


def test_seed_data_has_at_least_ten_records(client):
    assert len(client.get("/api/preferences").get_json()["data"]) >= 10


def test_create_and_update_preferences(client, new_traveler):
    created = client.post(
        "/api/preferences",
        json={
            "traveler_id": new_traveler,
            "budget_min": 1000,
            "budget_max": 2500,
            "currency": "AUD",
            "pace": "balanced",
            "preferred_trip_length_days": 8,
        },
    )
    assert created.status_code == 201
    record_id = created.get_json()["data"]["id"]

    updated = client.put(f"/api/preferences/{record_id}", json={"pace": "packed"})
    assert updated.status_code == 200
    assert updated.get_json()["data"]["pace"] == "packed"

    assert client.delete(f"/api/preferences/{record_id}").status_code == 204


def test_currency_defaults_to_aud(client, new_traveler):
    response = client.post(
        "/api/preferences",
        json={"traveler_id": new_traveler, "budget_min": 100, "budget_max": 200, "pace": "relaxed"},
    )
    assert response.get_json()["data"]["currency"] == "AUD"


def test_budget_max_below_min_is_rejected(client, new_traveler):
    response = client.post(
        "/api/preferences",
        json={"traveler_id": new_traveler, "budget_min": 5000, "budget_max": 100, "pace": "relaxed"},
    )
    assert response.status_code == 400
    assert "budget_max" in response.get_json()["error"]


def test_negative_budget_is_rejected(client, new_traveler):
    response = client.post(
        "/api/preferences",
        json={"traveler_id": new_traveler, "budget_min": -50, "budget_max": 100, "pace": "relaxed"},
    )
    assert response.status_code == 400


def test_invalid_pace_is_rejected(client, new_traveler):
    response = client.post(
        "/api/preferences",
        json={"traveler_id": new_traveler, "budget_min": 1, "budget_max": 2, "pace": "sprint"},
    )
    assert response.status_code == 400
    assert "pace" in response.get_json()["error"]


def test_one_preference_set_per_traveler(client, new_traveler):
    payload = {"traveler_id": new_traveler, "budget_min": 1, "budget_max": 2, "pace": "relaxed"}
    assert client.post("/api/preferences", json=payload).status_code == 201
    assert client.post("/api/preferences", json=payload).status_code == 409


def test_unknown_traveler_is_rejected(client):
    response = client.post(
        "/api/preferences",
        json={"traveler_id": 999999, "budget_min": 1, "budget_max": 2, "pace": "relaxed"},
    )
    assert response.status_code == 400
