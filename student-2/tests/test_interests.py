"""CRUD and constraint coverage for the Interests table."""


def test_seed_data_has_at_least_ten_records(client):
    assert len(client.get("/api/interests").get_json()["data"]) >= 10


def test_create_update_delete_interest(client, new_traveler):
    created = client.post(
        "/api/interests",
        json={"traveler_id": new_traveler, "interest_category": "Beaches", "priority": "high"},
    )
    assert created.status_code == 201
    record_id = created.get_json()["data"]["id"]

    updated = client.put(f"/api/interests/{record_id}", json={"priority": "low"})
    assert updated.get_json()["data"]["priority"] == "low"

    assert client.delete(f"/api/interests/{record_id}").status_code == 204


def test_priority_defaults_to_medium(client, new_traveler):
    response = client.post(
        "/api/interests",
        json={"traveler_id": new_traveler, "interest_category": "Shopping"},
    )
    assert response.get_json()["data"]["priority"] == "medium"


def test_unknown_category_is_rejected(client, new_traveler):
    response = client.post(
        "/api/interests",
        json={"traveler_id": new_traveler, "interest_category": "Extreme Ironing"},
    )
    assert response.status_code == 400
    assert "interest_category" in response.get_json()["error"]


def test_duplicate_interest_per_traveler_is_rejected(client, new_traveler):
    payload = {"traveler_id": new_traveler, "interest_category": "Nightlife"}
    assert client.post("/api/interests", json=payload).status_code == 201
    assert client.post("/api/interests", json=payload).status_code == 409


def test_filter_by_traveler(client):
    response = client.get("/api/interests?traveler_id=1")
    assert response.status_code == 200
    assert all(item["traveler_id"] == 1 for item in response.get_json()["data"])
