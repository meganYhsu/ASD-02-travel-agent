"""Pytest fixtures for the Student 3 Release 2 tests.

No server has to be running. The real backend and the real database API are
loaded as Flask apps, and every HTTP call the backend makes is routed
in-process:

    DB_API_URL               -> database API test client (fresh SQLite file
                                per test)
    MULTI_AGENT_SERVICE_URL  -> stub of the shared Multi-Agent server (only
                                when the multi_agent fixture is used)
    anything else            -> ConnectionError, like a service that is not
                                running

Fixture  = shared set-up (fresh database, test clients).
Stub     = canned replacement (the Multi-Agent server stub, "database down").
Mock     = records calls so a test can check what the backend sent (`calls`).
"""

import importlib.util
import os
import uuid
from pathlib import Path

import pytest
import requests
from flask import Flask, jsonify, request

STUDENT_DIR = Path(__file__).resolve().parents[1]
HTTP_METHODS = ("get", "post", "put", "patch", "delete")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def backend_module():
    return load("student3_backend", STUDENT_DIR / "backend" / "app.py")


@pytest.fixture(scope="session")
def db_module():
    return load("student3_db_api", STUDENT_DIR / "database" / "db_api.py")


@pytest.fixture()
def db_api(db_module, tmp_path, monkeypatch):
    """Fixture: the real database API on a fresh, seeded SQLite file."""
    monkeypatch.setattr(db_module, "DB_PATH", tmp_path / "budget.db")
    db_module.init_db()
    db_module.app.config["TESTING"] = True
    return db_module.app.test_client()


class RoutedResponse:
    """A Flask test response that behaves like requests.Response."""

    def __init__(self, resp):
        self._resp = resp
        self.status_code = resp.status_code
        self.ok = resp.status_code < 400
        self.text = resp.get_data(as_text=True)

    def json(self):
        data = self._resp.get_json(silent=True)
        if data is None:
            raise ValueError("response is not JSON")
        return data

    def raise_for_status(self):
        if not self.ok:
            raise requests.HTTPError(f"HTTP {self.status_code}")


@pytest.fixture()
def calls():
    """Mock record: every outbound call the backend makes during a test."""
    return []


@pytest.fixture()
def services(backend_module, db_api):
    """Base URL -> in-process test client. Tests may add more services."""
    return {backend_module.DB_API_URL: db_api}


@pytest.fixture()
def backend_client(backend_module, services, monkeypatch, calls):
    def route(method):
        def fake(url, params=None, json=None, timeout=None, **kwargs):
            calls.append({"method": method, "url": url, "params": params,
                          "json": json, "timeout": timeout})
            for base, client in services.items():
                if url.startswith(base):
                    resp = client.open(url[len(base):], method=method,
                                       query_string=params, json=json)
                    return RoutedResponse(resp)
            raise requests.ConnectionError(f"{url} is not running in this test")
        return fake

    for method in HTTP_METHODS:
        monkeypatch.setattr(backend_module.requests, method, route(method.upper()))
    backend_module.app.config["TESTING"] = True
    return backend_module.app.test_client()


@pytest.fixture()
def db_down(backend_module, monkeypatch, calls):
    """Stub: the database API container is stopped."""
    def fail(url, **kwargs):
        calls.append({"url": url, **kwargs})
        raise requests.ConnectionError("database API is down")

    for method in HTTP_METHODS:
        monkeypatch.setattr(backend_module.requests, method, fail)
    return backend_module.app.test_client()


@pytest.fixture()
def multi_agent(backend_module, services, monkeypatch):
    """Stub of the shared Multi-Agent server (ai-services/multi-agent-server).

    It follows the server's HTTP contract - POST /workflow, GET /workflow/<id>
    and POST /workflow/<id>/review with the same validation rules - so these
    tests need neither Ollama nor the real server. The returned dict records
    every request the backend sent and lets a test switch the worker result.
    """
    stub = Flask("multi_agent_stub")
    store = {"workflows": {}, "requests": [], "reviews": [], "worker_status": "success"}

    @stub.post("/workflow")
    def start_workflow():
        body = request.get_json(silent=True) or {}
        store["requests"].append(body)
        for field in ("service", "task", "user_request"):
            if not isinstance(body.get(field), str) or not body[field].strip():
                return jsonify({"status": "error", "error": f"{field} must be a non-empty string"}), 400
        if not isinstance(body.get("context"), dict):
            return jsonify({"status": "error", "error": "context must be a JSON object"}), 400
        status = store["worker_status"]
        workflow = {
            "status": "success" if status == "success" else "partial_failure",
            "workflow_id": str(uuid.uuid4()), "duration_ms": 61000,
            "service": body["service"], "task": body["task"],
            "user_request": body["user_request"], "context": body["context"],
            "planner_result": {"status": "success", "agent": "planner_agent", "model": "qwen2.5:3b",
                               "plan": "Compare spending with the budget, then recommend one change.",
                               "steps": [{"step": 1, "agent": "planner_agent",
                                          "action": "Identify the supplied facts"}]},
            "worker_result": {"status": status, "agent": "worker_agent", "model": "qwen2.5:3b",
                              "output": "Cap food at 60 AUD per day for the rest of the trip."},
            "reviewer_result": {"status": "success", "agent": "reviewer_agent", "model": "qwen2.5:3b",
                                "review": "Supported by the spending figures."},
            "human_decision": {"required": True, "status": "pending",
                               "allowed_values": ["Accept", "Partially Accept", "Reject"]},
        }
        store["workflows"][workflow["workflow_id"]] = workflow
        return jsonify(workflow)

    @stub.get("/workflow/<workflow_id>")
    def get_workflow(workflow_id):
        workflow = store["workflows"].get(workflow_id)
        if workflow is None:
            return jsonify({"status": "error", "error": "Workflow not found"}), 404
        return jsonify(workflow)

    @stub.post("/workflow/<workflow_id>/review")
    def review(workflow_id):
        body = request.get_json(silent=True) or {}
        store["reviews"].append(body)
        workflow = store["workflows"].get(workflow_id)
        if workflow is None:
            return jsonify({"status": "error", "error": "Workflow not found"}), 404
        if body.get("decision") not in ("Accept", "Partially Accept", "Reject"):
            return jsonify({"status": "error",
                            "error": "decision must be Accept, Partially Accept, or Reject"}), 400
        if len(str(body.get("reason", "")).strip()) < 20:
            return jsonify({"status": "error",
                            "error": "reason must contain at least 20 characters"}), 400
        workflow["human_decision"] = {**workflow["human_decision"], "status": "recorded",
                                      "decision": body["decision"], "reason": body["reason"],
                                      "evidence": body.get("evidence", "")}
        return jsonify(workflow)

    monkeypatch.setattr(backend_module, "MULTI_AGENT_ENABLED", True)
    services[backend_module.MULTI_AGENT_SERVICE_URL] = stub.test_client()
    return store


def pytest_terminal_summary(terminalreporter):
    """In GitHub Actions, add a results table to the run's summary page."""
    summary_file = os.getenv("GITHUB_STEP_SUMMARY")
    if not summary_file:
        return
    rows = []
    for outcome in ("passed", "failed", "error", "skipped"):
        for report in terminalreporter.stats.get(outcome, []):
            if not hasattr(report, "nodeid"):
                continue
            if outcome == "passed" and report.when != "call":
                continue
            file_name, _, test_name = report.nodeid.partition("::")
            rows.append(f"| {Path(file_name).name} | {test_name} | "
                        f"{outcome.upper()} | {report.duration:.3f} s |")
    if not rows:
        return
    with open(summary_file, "a", encoding="utf-8") as fh:
        fh.write("| File | Test | Result | Duration |\n|---|---|---|---|\n")
        fh.write("\n".join(rows) + "\n\n")
