"""AI-Mode endpoints and the Plan -> Act -> Observe -> Adapt loop."""

import pytest


def test_summarise_profile_returns_deterministic_set_plus_ai_text(client):
    response = client.post("/api/ai/summarise-profile", json={"traveler_id": 1})
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["phase"] == "PLAN"
    assert data["persisted"] is False
    assert data["review_required"] is True
    assert data["preference_set"]["traveler_id"] == 1
    assert data["summary"].startswith("Mid-range traveller")


def test_hallucinated_interest_categories_are_filtered(client):
    data = client.post("/api/ai/summarise-profile", json={"traveler_id": 1}).get_json()["data"]
    categories = [item["interest_category"] for item in data["suggested_interests"]]
    assert "Not A Real Category" not in categories
    assert "Beaches" in categories


def test_already_selected_interests_are_not_suggested(client):
    profile = client.get("/api/travelers/1/profile").get_json()["data"]
    existing = set(profile["preference_set"]["interests"])
    data = client.post("/api/ai/summarise-profile", json={"traveler_id": 1}).get_json()["data"]
    suggested = {item["interest_category"] for item in data["suggested_interests"]}
    assert not (suggested & existing)


def test_prompt_is_grounded_in_stored_records(client, api_app):
    client.post("/api/ai/summarise-profile", json={"traveler_id": 1})
    prompt = api_app.config["FAKE_OLLAMA"].prompts[-1]
    assert "Do not invent" in prompt
    assert "Aiko Tanaka" in prompt


def test_check_completeness_merges_ai_next_steps(client, new_traveler):
    response = client.post("/api/ai/check-completeness", json={"traveler_id": new_traveler})
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["phase"] == "OBSERVE"
    assert "Add at least three interests." in data["recommendations"]
    # The deterministic score is never overwritten by the model.
    assert data["score"] < 100


def test_apply_suggested_interests_persists_only_accepted(client, new_traveler):
    response = client.post(
        "/api/ai/apply-suggested-interests",
        json={
            "traveler_id": new_traveler,
            "interests": [
                {"interest_category": "Beaches", "priority": "high"},
                {"interest_category": "Fabricated Category"},
            ],
        },
    )
    assert response.status_code == 201
    data = response.get_json()["data"]
    assert data["phase"] == "ACT"
    assert len(data["saved"]) == 1
    assert data["saved"][0]["interest_category"] == "Beaches"
    assert len(data["skipped"]) == 1


def test_apply_requires_non_empty_list(client, new_traveler):
    response = client.post(
        "/api/ai/apply-suggested-interests", json={"traveler_id": new_traveler, "interests": []}
    )
    assert response.status_code == 400


def test_ollama_failure_is_surfaced_not_crashed(client, api_app):
    import sys

    OllamaError = sys.modules["student2_api_app"].OllamaError
    api_app.config["OLLAMA"].error = OllamaError("AI service unavailable", 503)
    response = client.post("/api/ai/summarise-profile", json={"traveler_id": 1})
    assert response.status_code == 503
    assert response.get_json()["success"] is False


def test_agentic_status_exposes_four_phases(client):
    response = client.get("/api/agentic/status?traveler_id=1")
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert set(data) == {"plan", "act", "observe", "adapt"}
    assert data["observe"]["completeness_score"] == 100
    assert data["observe"]["ready_for_trip_planning"] is True
    assert data["adapt"]["recommended_next_steps"]


def test_agentic_adapt_reacts_to_an_incomplete_profile(client, new_traveler):
    data = client.get(f"/api/agentic/status?traveler_id={new_traveler}").get_json()["data"]
    assert data["observe"]["ready_for_trip_planning"] is False
    steps = " ".join(data["adapt"]["recommended_next_steps"])
    assert "threshold" in steps or "budget" in steps


@pytest.mark.parametrize("payload", [{}, {"traveler_id": "abc"}, {"traveler_id": 0}])
def test_ai_endpoints_reject_bad_traveler_ids(client, payload):
    assert client.post("/api/ai/summarise-profile", json=payload).status_code == 400
