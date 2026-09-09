def test_packing_list_crud(client):
    created = client.post(
        "/api/packing-lists",
        json={
            "trip_id": "trip-test",
            "traveller_id": "traveller-001",
            "destination": "Portugal",
            "start_date": "2026-08-01",
            "end_date": "2026-08-08",
            "climate": "mild",
            "planned_activities": ["sightseeing"],
        },
    )
    assert created.status_code == 201
    record_id = created.get_json()["data"]["id"]
    fetched = client.get(f"/api/packing-lists/{record_id}")
    assert fetched.status_code == 200
    updated = client.put(f"/api/packing-lists/{record_id}", json={"climate": "hot"})
    assert updated.get_json()["data"]["climate"] == "hot"
    listed = client.get("/api/packing-lists", query_string={"trip_id": "trip-test"})
    assert any(item["id"] == record_id for item in listed.get_json()["data"])
    deleted = client.delete(f"/api/packing-lists/{record_id}")
    assert deleted.status_code == 204


def test_invalid_travel_dates(client):
    response = client.post(
        "/api/packing-lists",
        json={
            "trip_id": "trip-bad",
            "traveller_id": "traveller-001",
            "destination": "Portugal",
            "start_date": "2026-08-10",
            "end_date": "2026-08-01",
            "climate": "mild",
            "planned_activities": "sightseeing",
        },
    )
    assert response.status_code == 400


def test_packing_seed_count(client):
    response = client.get("/api/packing-lists")
    assert len(response.get_json()["data"]) >= 10
