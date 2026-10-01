from rag_client import RagError


class FakeRag:
    def __init__(self, error=None):
        self.error = error
        self.questions = []

    def query(self, question):
        self.questions.append(question)
        if self.error:
            raise self.error
        return {
            "answer": "Check your passport expiry before departure.",
            "sources": [{"source": "travel-preparation.md", "section": "Document checks"}],
            "mode": "generated",
            "disclaimer": "Verify travel requirements against official sources.",
        }


def test_assistant_forwards_question_and_sources(api_app):
    fake_rag = FakeRag()
    api_app.config["RAG"] = fake_rag
    response = api_app.test_client().post(
        "/api/ai/assistant",
        json={"question": "When should I check my passport?"},
    )
    data = response.get_json()["data"]
    assert response.status_code == 200
    assert fake_rag.questions == ["When should I check my passport?"]
    assert data["sources"][0]["section"] == "Document checks"


def test_assistant_rejects_empty_question(client):
    response = client.post("/api/ai/assistant", json={"question": "  "})
    assert response.status_code == 400
    assert response.get_json()["error"] == "question is required"


def test_assistant_reports_shared_service_failure(api_app):
    api_app.config["RAG"] = FakeRag(RagError("Shared travel assistant is unavailable"))
    response = api_app.test_client().post(
        "/api/ai/assistant",
        json={"question": "What should I pack?"},
    )
    assert response.status_code == 503
    assert response.get_json()["error"] == "Shared travel assistant is unavailable"