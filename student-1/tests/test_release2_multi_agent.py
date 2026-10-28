"""Release 2 Multi-Agent integration tests for the Student 1 backend.

Frontend -> backend -> shared Multi-Agent server (stubbed here, see
conftest.py) -> Planner -> Worker -> Reviewer -> Human Review.
"""

import uuid

REVIEW = {
    "decision": "Partially Accept",
    "reason": "Budget is right but the brief left out the dietary need.",
    "evidence": "Accessibility needs table",
}


def start(backend_client, traveler_id=1, user_request=""):
    return backend_client.post("/multi-agent/workflow",
                               data={"traveler_id": traveler_id,
                                     "user_request": user_request})


def workflow_calls(calls):
    return [c for c in calls if c["url"].endswith("/workflow")]


# ------------------------------------------------------------- start workflow
def test_disabled_by_default_and_calls_nothing(backend_client, calls):
    resp = start(backend_client)

    assert resp.status_code == 503
    assert "disabled" in resp.get_data(as_text=True)
    assert calls == []


def test_sends_preference_set_as_evidence(backend_client, multi_agent, calls):
    resp = start(backend_client)

    assert resp.status_code == 200
    [sent] = workflow_calls(calls)
    body = sent["json"]
    assert body["service"] == "traveller"
    assert body["task"] == "review_preferences"
    assert "complete and consistent" in body["user_request"]  # default request
    context = body["context"]
    assert context["traveler"]["traveler_id"] == 1
    assert context["preferences"]["budget_min"] >= 0
    assert context["interests"] and context["accessibility_needs"]
    assert "score" in context["completeness"]
    assert "email" not in context["traveler"]  # only the evidence the task needs
    assert sent["timeout"] == 420


def test_custom_request_is_forwarded(backend_client, multi_agent, calls):
    start(backend_client, user_request="Is this traveller ready for a packed trip?")

    assert workflow_calls(calls)[0]["json"]["user_request"] == (
        "Is this traveller ready for a packed trip?")


def test_renders_all_agents_and_pending_human_review(backend_client, multi_agent):
    html = start(backend_client).get_data(as_text=True)

    for stage in ("1. Planner", "2. Worker", "3. Reviewer", "4. Human review"):
        assert stage in html
    assert "Check budget, interests and needs." in html
    assert "Matches the supplied evidence." in html
    assert "pending" in html
    workflow_id = next(iter(multi_agent))
    assert f"/api/multi-agent/workflows/{workflow_id}/review" in html
    for decision in ("Accept", "Partially Accept", "Reject"):
        assert f"value='{decision}'" in html


def test_requires_a_traveller(backend_client, multi_agent, calls):
    resp = backend_client.post("/multi-agent/workflow", data={})

    assert resp.status_code == 400
    assert calls == []


def test_rejects_overlong_request(backend_client, multi_agent, calls):
    resp = start(backend_client, user_request="x" * 501)

    assert resp.status_code == 400
    assert calls == []


def test_unknown_traveller_returns_404_without_calling_agents(
        backend_client, multi_agent, calls):
    resp = start(backend_client, traveler_id=9999)

    assert resp.status_code == 404
    assert workflow_calls(calls) == []


def test_server_down_returns_503(backend_client, backend_module, monkeypatch, calls):
    monkeypatch.setattr(backend_module, "MULTI_AGENT_ENABLED", True)

    resp = start(backend_client)

    assert resp.status_code == 503
    assert "Multi-Agent server is unavailable" in resp.get_data(as_text=True)


def test_agent_failure_is_shown_for_human_review(backend_client, multi_agent, services,
                                                 backend_module):
    stub = services[backend_module.MULTI_AGENT_SERVICE_URL].application
    original = stub.view_functions["workflow"]

    def failing_worker():
        resp = original()
        data = resp.get_json()
        data["status"] = "partial_failure"
        data["worker_result"] = {"status": "timeout", "agent": "worker_agent",
                                 "output": "Worker could not generate an answer.",
                                 "error": "APITimeoutError: timed out"}
        multi_agent[data["workflow_id"]] = data
        return data

    stub.view_functions["workflow"] = failing_worker
    try:
        html = start(backend_client).get_data(as_text=True)
    finally:
        stub.view_functions["workflow"] = original

    assert "partial_failure" in html
    assert "APITimeoutError" in html
    assert "4. Human review" in html


# --------------------------------------------------------------- human review
def test_records_human_decision(backend_client, multi_agent, calls):
    start(backend_client)
    workflow_id = next(iter(multi_agent))

    resp = backend_client.post(f"/multi-agent/workflows/{workflow_id}/review", data=REVIEW)

    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Decision recorded" in html
    assert "Partially Accept" in html
    assert REVIEW["reason"] in html
    sent = [c for c in calls if c["url"].endswith("/review")][0]["json"]
    assert sent == REVIEW
    assert multi_agent[workflow_id]["human_decision"]["status"] == "recorded"


def test_lookup_shows_recorded_decision(backend_client, multi_agent):
    start(backend_client)
    workflow_id = next(iter(multi_agent))
    backend_client.post(f"/multi-agent/workflows/{workflow_id}/review", data=REVIEW)

    html = backend_client.get(f"/multi-agent/workflows/{workflow_id}").get_data(as_text=True)

    assert "recorded" in html
    assert REVIEW["reason"] in html
    assert "<form" not in html  # no second decision form


def test_lookup_form_uses_query_parameter(backend_client, multi_agent):
    start(backend_client)
    workflow_id = next(iter(multi_agent))

    found = backend_client.get(f"/multi-agent/lookup?workflow_id={workflow_id}")
    empty = backend_client.get("/multi-agent/lookup?workflow_id=")

    assert found.status_code == 200
    assert workflow_id in found.get_data(as_text=True)
    assert empty.status_code == 400


def test_review_rejects_unknown_decision(backend_client, multi_agent):
    start(backend_client)
    workflow_id = next(iter(multi_agent))

    resp = backend_client.post(f"/multi-agent/workflows/{workflow_id}/review",
                               data={**REVIEW, "decision": "Approve"})

    assert resp.status_code == 400
    assert multi_agent[workflow_id]["human_decision"]["status"] == "pending"


def test_review_requires_a_reason(backend_client, multi_agent):
    start(backend_client)
    workflow_id = next(iter(multi_agent))

    resp = backend_client.post(f"/multi-agent/workflows/{workflow_id}/review",
                               data={**REVIEW, "reason": "too short"})

    assert resp.status_code == 400
    assert multi_agent[workflow_id]["human_decision"]["status"] == "pending"


def test_invalid_workflow_id_is_not_forwarded(backend_client, multi_agent, calls):
    resp = backend_client.post("/multi-agent/workflows/..%2Fstatus/review", data=REVIEW)
    lookup = backend_client.get("/multi-agent/workflows/not-a-uuid")

    assert resp.status_code in (400, 404)
    assert lookup.status_code == 400
    assert calls == []


def test_other_students_workflows_are_hidden(backend_client, multi_agent):
    foreign_id = str(uuid.uuid4())
    multi_agent[foreign_id] = {"workflow_id": foreign_id, "service": "budget",
                               "task": "review_spending",
                               "human_decision": {"status": "pending"}}

    lookup = backend_client.get(f"/multi-agent/workflows/{foreign_id}")
    review = backend_client.post(f"/multi-agent/workflows/{foreign_id}/review", data=REVIEW)

    assert lookup.status_code == 404
    assert review.status_code == 404
    assert multi_agent[foreign_id]["human_decision"]["status"] == "pending"


# --------------------------------------------------------- terminal evidence
def test_evidence_endpoint_returns_workflow_body(backend_client, multi_agent):
    resp = backend_client.get("/multi-agent/evidence/1")

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["service"] == "traveller"
    assert body["context"]["traveler"]["traveler_id"] == 1


def test_evidence_endpoint_disabled_by_default(backend_client):
    assert backend_client.get("/multi-agent/evidence/1").status_code == 503
