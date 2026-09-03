"""Aggregated profile, structured preference set and deterministic completeness."""


def test_profile_aggregates_all_four_tables(client):
    response = client.get("/api/travelers/1/profile")
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert set(data).issuperset(
        {"traveler", "preferences", "interests", "accessibility_needs", "preference_set", "completeness"}
    )
    assert data["traveler"]["id"] == 1
    assert len(data["interests"]) >= 1


def test_preference_set_is_flattened_for_other_services(client):
    data = client.get("/api/travelers/1/profile").get_json()["data"]["preference_set"]
    assert data["traveler_id"] == 1
    assert isinstance(data["interests"], list)
    assert data["budget"]["currency"] == "AUD"
    assert data["pace"] in {"relaxed", "balanced", "packed"}
    # "None" entries are filtered out of the outbound contract.
    assert "None" not in data["dietary_restrictions"]
    assert "None" not in data["accessibility_requirements"]


def test_top_interests_only_contains_high_priority(client):
    profile = client.get("/api/travelers/1/profile").get_json()["data"]
    high = {i["interest_category"] for i in profile["interests"] if i["priority"] == "high"}
    assert set(profile["preference_set"]["top_interests"]) == high


def test_seeded_profile_is_complete(client):
    data = client.get("/api/travelers/1/completeness").get_json()["data"]
    assert data["score"] == 100
    assert data["is_complete"] is True
    assert data["ready_for_trip_planning"] is True
    assert data["missing"] == []


def test_new_traveler_is_incomplete(client, new_traveler):
    data = client.get(f"/api/travelers/{new_traveler}/completeness").get_json()["data"]
    assert data["score"] < 100
    assert data["ready_for_trip_planning"] is False
    assert set(data["missing"]) == {"preferences", "interests", "accessibility_needs"}


def test_score_increases_as_profile_is_filled(client, new_traveler):
    before = client.get(f"/api/travelers/{new_traveler}/completeness").get_json()["data"]["score"]
    client.post(
        "/api/preferences",
        json={"traveler_id": new_traveler, "budget_min": 500, "budget_max": 1500, "pace": "relaxed"},
    )
    after = client.get(f"/api/travelers/{new_traveler}/completeness").get_json()["data"]["score"]
    assert after > before


def test_partial_interests_earn_partial_credit(client, new_traveler):
    client.post(
        "/api/interests", json={"traveler_id": new_traveler, "interest_category": "Beaches"}
    )
    data = client.get(f"/api/travelers/{new_traveler}/completeness").get_json()["data"]
    assert data["counts"]["interests"] == 1
    assert any("interests" in rec for rec in data["recommendations"])


def test_missing_traveler_returns_404(client):
    assert client.get("/api/travelers/999999/profile").status_code == 404
    assert client.get("/api/travelers/999999/completeness").status_code == 404
