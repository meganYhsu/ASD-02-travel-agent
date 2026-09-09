def test_pretrip_task_crud_and_completion(client):
    created = client.post(
        "/api/pre-trip-tasks",
        json={
            "trip_id": "trip-task",
            "traveller_id": "traveller-001",
            "task_name": "Notify bank",
            "description": "Tell the bank about travel dates.",
            "due_date": "2026-08-01",
            "priority": "medium",
        },
    )
    assert created.status_code == 201
    record_id = created.get_json()["data"]["id"]
    fetched = client.get(f"/api/pre-trip-tasks/{record_id}")
    assert fetched.status_code == 200
    updated = client.put(f"/api/pre-trip-tasks/{record_id}", json={"priority": "high"})
    assert updated.get_json()["data"]["priority"] == "high"
    listed = client.get("/api/pre-trip-tasks", query_string={"trip_id": "trip-task"})
    assert any(item["id"] == record_id for item in listed.get_json()["data"])
    completed = client.patch(
        f"/api/pre-trip-tasks/{record_id}/complete",
        json={"is_completed": True},
    )
    assert completed.get_json()["data"]["is_completed"] is True
    assert completed.get_json()["data"]["completed_at"]
    undone = client.patch(
        f"/api/pre-trip-tasks/{record_id}/complete",
        json={"is_completed": False},
    )
    assert undone.get_json()["data"]["is_completed"] is False
    assert undone.get_json()["data"]["completed_at"] is None
    progress = client.get("/api/pre-trip-tasks/progress", query_string={"trip_id": "trip-task"})
    assert progress.status_code == 200
    deleted = client.delete(f"/api/pre-trip-tasks/{record_id}")
    assert deleted.status_code == 204


def test_pretrip_seed_and_invalid_priority(client):
    listed = client.get("/api/pre-trip-tasks")
    assert len(listed.get_json()["data"]) >= 10
    invalid = client.post(
        "/api/pre-trip-tasks",
        json={
            "trip_id": "trip-task",
            "traveller_id": "traveller-001",
            "task_name": "X",
            "description": "Y",
            "due_date": "2026-08-01",
            "priority": "urgent",
        },
    )
    assert invalid.status_code == 400
