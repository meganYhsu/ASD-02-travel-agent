"""Release 2 - AI services off by default, and the Multi-Agent integration.

The cloud baseline needs AI-Mode, MCP, RAG and Multi-Agent disabled by
default: with no environment variables set, each route answers 503 with a
clear message while the CRUD endpoints keep working.

The shared Multi-Agent server (ai-services/multi-agent-server) is replaced by
a stub that follows its HTTP contract (conftest.multi_agent), so the Student 3
side of the workflow is tested without Ollama:
UI form -> backend -> POST /workflow -> Planner / Worker / Reviewer results
-> human decision -> POST /workflow/<id>/review -> recommendation saved.
"""

import re

import pytest

WF_ID = "0f0e0d0c-0b0a-4908-8706-050403020100"
REASON = "Food is the biggest cost, so a daily cap makes sense."

AI_ROUTES = [
    ("post", "/analyse/1", "AI_MODE_ENABLED=false"),
    ("get", "/mcp/tools", "MCP_ENABLED=false"),
    ("post", "/rag/query", "RAG_ENABLED=false"),
    ("post", "/multi-agent/budget-review/1", "MULTI_AGENT_ENABLED=false"),
    ("get", f"/multi-agent/workflow/{WF_ID}", "MULTI_AGENT_ENABLED=false"),
]


def workflow_id(html):
    return re.search(r"<code>([0-9a-f-]{36})</code>", html).group(1)


def saved_for(db_api, wid):
    recs = db_api.get("/recommendations?trip_id=1").get_json()
    return [r for r in recs if f"[Multi-agent {wid[:8]}]" in r["recommendation"]]


def start_review(backend_client, focus=""):
    resp = backend_client.post("/multi-agent/budget-review/1", data={"focus": focus})
    return resp, resp.get_data(as_text=True)


# ------------------------------------------------------- AI services off by default
@pytest.mark.parametrize("name", ["AI_MODE_ENABLED", "MCP_ENABLED", "RAG_ENABLED",
                                  "MULTI_AGENT_ENABLED"])
def test_ai_flags_default_to_off(backend_module, monkeypatch, name):
    monkeypatch.delenv(name, raising=False)
    assert backend_module.flag(name) is False


@pytest.mark.parametrize("method,path,message", AI_ROUTES)
def test_disabled_ai_routes_return_503(backend_client, backend_module, monkeypatch,
                                       method, path, message):
    for name in ("AI_MODE_ENABLED", "MCP_ENABLED", "RAG_ENABLED", "MULTI_AGENT_ENABLED"):
        monkeypatch.setattr(backend_module, name, False)

    resp = getattr(backend_client, method)(path, data={"question": "budget?"})

    assert resp.status_code == 503
    assert message in resp.get_data(as_text=True)


def test_health_reports_release2_flags(backend_client):
    data = backend_client.get("/health").get_json()
    for key in ("ai_mode_enabled", "mcp_enabled", "rag_enabled",
                "multi_agent_enabled", "multi_agent_server"):
        assert key in data


# ------------------------------------------------------- Multi-Agent integration
def test_invalid_workflow_id_is_refused(backend_client, backend_module, monkeypatch):
    monkeypatch.setattr(backend_module, "MULTI_AGENT_ENABLED", True)
    assert backend_client.get("/multi-agent/workflow/not-a-workflow").status_code == 400


def test_multi_agent_server_down_returns_503(backend_client, backend_module, monkeypatch):
    monkeypatch.setattr(backend_module, "MULTI_AGENT_ENABLED", True)
    resp, html = start_review(backend_client)
    assert resp.status_code == 503
    assert "Multi-Agent server is unavailable" in html


def test_request_follows_the_shared_server_contract(backend_client, db_api, multi_agent):
    start_review(backend_client, focus="food")
    sent = multi_agent["requests"][0]
    expenses = db_api.get("/expenses?trip_id=1").get_json()

    assert sent["service"] == "budget" and sent["task"] == "review_spending"
    assert "trip 1" in sent["user_request"] and "Focus on: food" in sent["user_request"]
    assert sent["context"]["budget"]["trip_id"] == 1
    assert sent["context"]["spending"]["expense_count"] == len(expenses)
    assert set(sent["context"]) >= {"budget", "spending", "spent_by_category",
                                    "recent_expenses", "trip"}


def test_agent_results_and_review_form_are_shown(backend_client, multi_agent):
    resp, html = start_review(backend_client)

    assert resp.status_code == 200
    for title in ("Planner", "Worker", "Reviewer"):
        assert f"{title} <span" in html
    assert "Cap food at 60 AUD per day" in html
    assert "<li>planner_agent: Identify the supplied facts</li>" in html   # plan steps as a list
    for decision in ("Accept", "Partially Accept", "Reject"):
        assert f"value='{decision}'" in html
    assert "2. Planner: <strong>success</strong>" in html
    assert "5. Human review: <strong>pending</strong>" in html


def test_accept_saves_the_recommendation(backend_client, db_api, multi_agent):
    wid = workflow_id(start_review(backend_client)[1])

    html = backend_client.post(f"/multi-agent/workflow/{wid}/decision",
                               data={"decision": "Accept", "reason": REASON}).get_data(as_text=True)
    saved = saved_for(db_api, wid)

    assert "Human decision: Accept" in html
    assert "5. Human review: <strong>Accept</strong>" in html
    assert multi_agent["reviews"][0] == {"decision": "Accept", "reason": REASON, "evidence": ""}
    assert len(saved) == 1 and saved[0]["status"] == "accepted"


def test_reject_saves_the_recommendation_as_dismissed(backend_client, db_api, multi_agent):
    wid = workflow_id(start_review(backend_client)[1])
    backend_client.post(f"/multi-agent/workflow/{wid}/decision",
                        data={"decision": "Reject", "reason": REASON})
    assert saved_for(db_api, wid)[0]["status"] == "dismissed"


def test_partial_acceptance_keeps_it_proposed_and_offers_a_rerun(backend_client, db_api,
                                                                 multi_agent):
    wid = workflow_id(start_review(backend_client)[1])

    html = backend_client.post(f"/multi-agent/workflow/{wid}/decision",
                               data={"decision": "Partially Accept", "reason": REASON}
                               ).get_data(as_text=True)
    saved = saved_for(db_api, wid)

    assert "Run the agents again with this correction" in html
    assert saved[0]["status"] == "proposed" and "Correction:" in saved[0]["recommendation"]


def test_short_reason_is_refused_and_the_form_stays(backend_client, db_api, multi_agent):
    wid = workflow_id(start_review(backend_client)[1])

    html = backend_client.post(f"/multi-agent/workflow/{wid}/decision",
                               data={"decision": "Accept", "reason": "too short"}
                               ).get_data(as_text=True)

    assert "Decision not recorded" in html
    assert "value='Accept'" in html                 # review form still on screen
    assert multi_agent["reviews"] == []             # never sent to the server
    assert saved_for(db_api, wid) == []


def test_agent_failure_is_visible_to_the_human(backend_client, multi_agent):
    multi_agent["worker_status"] = "timeout"
    html = start_review(backend_client)[1]
    assert "partial_failure" in html
    assert "<li class='ma-bad'>3. Worker: <strong>timeout</strong></li>" in html


def test_evidence_endpoint_returns_the_shared_server_request(backend_client, backend_module,
                                                             monkeypatch, db_api):
    monkeypatch.setattr(backend_module, "MULTI_AGENT_ENABLED", True)
    data = backend_client.get("/multi-agent/evidence/1").get_json()
    expenses = db_api.get("/expenses?trip_id=1").get_json()

    assert data["service"] == "budget" and data["task"] == "review_spending"
    assert data["context"]["spending"]["expense_count"] == len(expenses)
    assert data["context"]["trip"]["available"] is False   # Trip Planning not running
