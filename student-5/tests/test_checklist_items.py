def _create_list(client):
    created = client.post(
        "/api/packing-lists",
        json={
            "trip_id": "trip-check",
            "traveller_id": "traveller-001",
            "destination": "Italy",
            "start_date": "2026-05-01",
            "end_date": "2026-05-05",
            "climate": "mild",
            "planned_activities": "sightseeing",
        },
    )
    return created.get_json()["data"]["id"]


def test_checklist_crud_and_completion(client):
    packing_id = _create_list(client)
    created = client.post(
        "/api/checklist-items",
        json={
            "packing_list_id": packing_id,
            "item_name": "Socks",
            "category": "Clothing",
            "quantity": 4,
        },
    )
    assert created.status_code == 201
    record_id = created.get_json()["data"]["id"]
    fetched = client.get(f"/api/checklist-items/{record_id}")
    assert fetched.status_code == 200
    updated = client.put(f"/api/checklist-items/{record_id}", json={"quantity": 6})
    assert updated.get_json()["data"]["quantity"] == 6
    listed = client.get("/api/checklist-items", query_string={"packing_list_id": packing_id})
    assert any(item["id"] == record_id for item in listed.get_json()["data"])
    completed = client.patch(
        f"/api/checklist-items/{record_id}/complete",
        json={"is_completed": True},
    )
    assert completed.status_code == 200
    assert completed.get_json()["data"]["is_completed"] is True
    assert completed.get_json()["data"]["completed_at"]
    undone = client.patch(
        f"/api/checklist-items/{record_id}/complete",
        json={"is_completed": False},
    )
    assert undone.get_json()["data"]["is_completed"] is False
    assert undone.get_json()["data"]["completed_at"] is None
    progress = client.get(f"/api/packing-lists/{packing_id}/progress")
    assert progress.status_code == 200
    deleted = client.delete(f"/api/checklist-items/{record_id}")
    assert deleted.status_code == 204


def test_checklist_seed_and_invalid(client):
    listed = client.get("/api/checklist-items")
    assert len(listed.get_json()["data"]) >= 10
    invalid = client.post(
        "/api/checklist-items",
        json={"packing_list_id": 1, "item_name": "X", "category": "Clothing", "quantity": 0},
    )
    assert invalid.status_code == 400
