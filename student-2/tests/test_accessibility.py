"""CRUD and constraint coverage for the AccessibilityNeeds table."""


def test_seed_data_has_at_least_ten_records(client):
    assert len(client.get("/api/accessibility-needs").get_json()["data"]) >= 10


def test_create_update_delete_need(client, new_traveler):
    created = client.post(
        "/api/accessibility-needs",
        json={
            "traveler_id": new_traveler,
            "requirement": "Step-free access",
            "dietary_restriction": "Vegan",
            "notes": "Ground-floor rooms only.",
        },
    )
    assert created.status_code == 201
    record = created.get_json()["data"]
    assert record["notes"] == "Ground-floor rooms only."

    updated = client.put(
        f"/api/accessibility-needs/{record['id']}", json={"dietary_restriction": "Halal"}
    )
    assert updated.get_json()["data"]["dietary_restriction"] == "Halal"

    assert client.delete(f"/api/accessibility-needs/{record['id']}").status_code == 204


def test_notes_are_optional(client, new_traveler):
    response = client.post(
        "/api/accessibility-needs",
        json={"traveler_id": new_traveler, "requirement": "None", "dietary_restriction": "None"},
    )
    assert response.status_code == 201
    assert response.get_json()["data"]["notes"] is None


def test_unknown_requirement_is_rejected(client, new_traveler):
    response = client.post(
        "/api/accessibility-needs",
        json={"traveler_id": new_traveler, "requirement": "Teleportation", "dietary_restriction": "None"},
    )
    assert response.status_code == 400


def test_unknown_dietary_restriction_is_rejected(client, new_traveler):
    response = client.post(
        "/api/accessibility-needs",
        json={"traveler_id": new_traveler, "requirement": "None", "dietary_restriction": "Carnivore"},
    )
    assert response.status_code == 400


def test_deleting_traveler_cascades_to_needs(client, new_traveler):
    client.post(
        "/api/accessibility-needs",
        json={"traveler_id": new_traveler, "requirement": "None", "dietary_restriction": "Vegan"},
    )
    client.delete(f"/api/travelers/{new_traveler}")
    remaining = client.get(f"/api/accessibility-needs?traveler_id={new_traveler}").get_json()["data"]
    assert remaining == []
