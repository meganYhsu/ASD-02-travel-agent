from pathlib import Path

from app import Retriever, create_app


def make_client(tmp_path: Path, monkeypatch):
    knowledge = tmp_path / "knowledge.md"
    knowledge.write_text(
        "# Guide\n\n## Packing\n\nPack a rain jacket for wet climates.\n\n"
        "## Documents\n\nCheck passport expiry before departure.",
        encoding="utf-8",
    )
    monkeypatch.setenv("RAG_GENERATION_ENABLED", "false")
    app = create_app(Retriever([knowledge]))
    app.config["TESTING"] = True
    return app.test_client()


def test_health_reports_indexed_chunks(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["chunks"] == 2


def test_query_returns_grounded_answer_and_source(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    response = client.post("/query", json={"question": "What should I pack for rain?"})
    data = response.get_json()["data"]
    assert response.status_code == 200
    assert "rain jacket" in data["answer"]
    assert data["sources"][0]["section"] == "Packing"
    assert data["mode"] == "retrieval_only"


def test_query_requires_question(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    response = client.post("/query", json={})
    assert response.status_code == 400
    assert response.get_json()["error"] == "question is required"


def test_query_handles_no_match(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    response = client.post("/query", json={"question": "quantum astrophysics"})
    data = response.get_json()["data"]
    assert response.status_code == 200
    assert data["mode"] == "no_match"
    assert data["sources"] == []