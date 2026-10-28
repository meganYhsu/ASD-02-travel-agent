"""Release 2 cloud-baseline tests: with no AI flags set (CI and the AWS
deployment), AI-Mode, MCP, RAG and Multi-Agent are off, and the core CRUD
feature and health checks still work."""

import dotenv
import pytest

from conftest import AI_FLAGS, STUDENT_DIR, load


@pytest.fixture()
def fresh_backend(monkeypatch):
    """Imports the backend again with no AI flags and no .env file."""
    for name in AI_FLAGS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: False)
    return load("student1_backend_fresh", STUDENT_DIR / "backend" / "app.py")


def test_every_ai_service_defaults_to_off(fresh_backend):
    assert fresh_backend.AI_MODE_ENABLED is False
    assert fresh_backend.MCP_ENABLED is False
    assert fresh_backend.RAG_ENABLED is False
    assert fresh_backend.MULTI_AGENT_ENABLED is False


@pytest.mark.parametrize("value, expected", [("true", True), ("1", True),
                                              ("false", False), ("", False)])
def test_flags_turn_on_only_when_set(fresh_backend, monkeypatch, value, expected):
    monkeypatch.setenv("MULTI_AGENT_ENABLED", value)
    assert fresh_backend.flag("MULTI_AGENT_ENABLED") is expected


def test_health_reports_flags(backend_client):
    data = backend_client.get("/health").get_json()

    assert data["status"] == "ok"
    for key in ("ai_mode_enabled", "mcp_enabled", "rag_enabled", "multi_agent_enabled"):
        assert data[key] is False


def test_ai_routes_are_disabled_but_do_not_crash(backend_client, calls):
    assert backend_client.post("/summarise/1").status_code == 503
    assert backend_client.post("/mcp/tool", data={"tool_name": "get_traveler_profile",
                                                  "traveler_id": 1}).status_code == 503
    assert backend_client.post("/rag/ask", data={"question": "hi"}).status_code == 503
    assert backend_client.post("/multi-agent/workflow",
                               data={"traveler_id": 1}).status_code == 503
    assert not any("11434" in c["url"] for c in calls)  # no Ollama call


def test_completeness_score_still_works_without_ai(backend_client):
    resp = backend_client.post("/completeness/1")

    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "% complete" in html
    assert "AI-Mode is disabled" in html


def test_core_crud_works_with_ai_off(backend_client, db_api):
    created = backend_client.post("/travelers", data={
        "name": "Cloud Tester", "email": "cloud.tester@example.com",
        "home_location": "Sydney", "travel_style": "mid-range"})
    assert created.status_code == 200

    traveler_id = max(t["traveler_id"] for t in db_api.get("/travelers").get_json())
    assert backend_client.post("/interests", data={
        "traveler_id": traveler_id, "interest_category": "Museums",
        "priority": 4}).status_code == 200
    assert "Museums" in backend_client.get(f"/profile/{traveler_id}").get_data(as_text=True)
    assert backend_client.post(f"/travelers/{traveler_id}/delete").status_code == 200
    assert db_api.get(f"/travelers/{traveler_id}").status_code == 404


def test_frontend_health_and_configurable_navigation(frontend_module, monkeypatch):
    monkeypatch.setattr(frontend_module, "SHARED_HOME_URL", "http://alb.example.com")
    client = frontend_module.app.test_client()

    assert client.get("/health").get_json()["status"] == "ok"
    page = client.get("/").get_data(as_text=True)
    assert 'href="http://alb.example.com/booking"' in page
    assert "127.0.0.1:8080" not in page
    assert "Preference review (multi-agent)" in page


def test_frontend_proxy_waits_longer_than_backend(frontend_module, backend_module):
    assert (frontend_module.PROXY_TIMEOUT_SECONDS
            > backend_module.MULTI_AGENT_TIMEOUT_SECONDS)
