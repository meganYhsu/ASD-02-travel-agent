def test_entry_requirements_crud_and_filter(client):
    created = client.post(
        "/api/entry-requirements",
        json={
            "destination_country": "Spain",
            "traveller_nationality": "Australian",
            "requirement_type": "Passport required",
            "document_type": "Passport",
            "description": "Demonstration passport rule.",
            "minimum_validity_days": 90,
            "is_required": True,
        },
    )
    assert created.status_code == 201
    record_id = created.get_json()["data"]["id"]
    fetched = client.get(f"/api/entry-requirements/{record_id}")
    assert fetched.status_code == 200
    updated = client.put(
        f"/api/entry-requirements/{record_id}",
        json={"minimum_validity_days": 120},
    )
    assert updated.get_json()["data"]["minimum_validity_days"] == 120
    filtered = client.get(
        "/api/entry-requirements",
        query_string={"destination": "Spain", "nationality": "Australian"},
    )
    assert filtered.status_code == 200
    assert any(item["id"] == record_id for item in filtered.get_json()["data"])
    deleted = client.delete(f"/api/entry-requirements/{record_id}")
    assert deleted.status_code == 204


def test_entry_requirements_seed_and_validation(client):
    listed = client.get("/api/entry-requirements")
    assert len(listed.get_json()["data"]) >= 10
    invalid = client.post("/api/entry-requirements", json={"destination_country": "Spain"})
    assert invalid.status_code == 400
