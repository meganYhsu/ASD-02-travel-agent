from ollama_client import OllamaClient, OllamaError, extract_json


def test_successful_structured_generation(client, api_app):
    response = client.post(
        "/api/ai/generate-pretrip-checklist",
        json={
            "trip_id": "trip-001",
            "traveller_id": "traveller-001",
            "destination": "Japan",
            "start_date": "2026-09-01",
            "end_date": "2026-09-10",
            "climate": "rainy",
            "planned_activities": ["hiking", "business meeting"],
        },
    )
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["persisted"] is False
    assert data["review_required"] is True
    assert data["packing_items"][0]["item_name"] == "Rain jacket"
    assert data["pre_trip_tasks"][0]["task_name"] == "Confirm travel insurance"
    listed = client.get("/api/packing-lists", query_string={"trip_id": "trip-001"})
    original = [item for item in listed.get_json()["data"] if item["destination"] == "Japan"]
    assert original


def test_generation_missing_input(client):
    response = client.post("/api/ai/generate-pretrip-checklist", json={"trip_id": "trip-001"})
    assert response.status_code == 400


def test_save_after_review_persists_ai_flags(client):
    generated = client.post(
        "/api/ai/generate-pretrip-checklist",
        json={
            "trip_id": "trip-ai",
            "traveller_id": "traveller-001",
            "destination": "Japan",
            "start_date": "2026-09-01",
            "end_date": "2026-09-10",
            "climate": "rainy",
            "planned_activities": ["hiking"],
        },
    ).get_json()["data"]
    saved = client.post(
        "/api/ai/save-pretrip-checklist",
        json={
            "trip": generated["trip"],
            "packing_items": generated["packing_items"],
            "pre_trip_tasks": generated["pre_trip_tasks"],
        },
    )
    assert saved.status_code == 201
    body = saved.get_json()["data"]
    assert body["checklist_items"][0]["is_ai_generated"] is True
    assert body["pre_trip_tasks"][0]["is_ai_generated"] is True


def test_malformed_ai_response(api_app, client):
    api_app.config["OLLAMA"].error = OllamaError("Malformed AI response", 502)
    response = client.post(
        "/api/ai/check-compliance",
        json={
            "trip_id": "trip-001",
            "traveller_id": "traveller-001",
            "destination": "Japan",
            "nationality": "Australian",
            "departure_date": "2026-09-01",
            "return_date": "2026-09-10",
        },
    )
    assert response.status_code == 502


def test_ollama_unavailable(api_app, client):
    api_app.config["OLLAMA"].error = OllamaError("AI service unavailable", 503)
    response = client.post(
        "/api/ai/check-compliance",
        json={
            "trip_id": "trip-001",
            "traveller_id": "traveller-001",
            "destination": "Japan",
            "nationality": "Australian",
            "departure_date": "2026-09-01",
            "return_date": "2026-09-10",
        },
    )
    assert response.status_code == 503


def test_timeout_handling():
    def boom(_prompt):
        raise OllamaError("AI service timed out", 503)

    client = OllamaClient(generate_fn=lambda prompt: (_ for _ in ()).throw(OllamaError("AI service timed out", 503)))
    try:
        client.generate_json("hello")
        assert False, "expected timeout"
    except OllamaError as exc:
        assert exc.status == 503


def test_extract_json_from_markdown():
    parsed = extract_json("```json\n{\"summary\": \"ok\"}\n```")
    assert parsed["summary"] == "ok"


def test_ollama_timeout_via_generate_fn():
    wrapped = OllamaClient(generate_fn=lambda _prompt: (_ for _ in ()).throw(OllamaError("AI service timed out", 503)))
    try:
        wrapped.generate_json("prompt")
        assert False
    except OllamaError as exc:
        assert "timed out" in exc.message
