"""Pytest fixtures for the Student 1 Release 2 tests.

No server has to be running. The real backend and the real database API are
loaded as Flask apps, and every HTTP call the backend makes is routed
in-process:

    DB_API_URL               -> database API test client (fresh, seeded
                                SQLite file per test)
    MULTI_AGENT_SERVICE_URL  -> stub of the shared Multi-Agent server (only
                                when the multi_agent fixture is used)
    anything else            -> ConnectionError, like a service that is down

Fixture = shared set-up (fresh database, test clients).
Stub    = canned replacement (the Multi-Agent server, "database down").
Mock    = records what the backend sent (`calls`) so a test can check it.
"""

import importlib.util
import sys
import uuid
from pathlib import Path

import pytest
import requests
from flask import Flask, jsonify, request

STUDENT_DIR = Path(__file__).resolve().parents[1]
HTTP_METHODS = ("get", "post", "put", "patch", "delete")
AI_FLAGS = ("AI_MODE_ENABLED", "MCP_ENABLED", "RAG_ENABLED", "MULTI_AGENT_ENABLED")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # lets Flask find templates/ next to the file
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def backend_module():
    return load("student1_backend", STUDENT_DIR / "backend" / "app.py")


@pytest.fixture(scope="session")
def db_module():
    return load("student1_db_api", STUDENT_DIR / "database" / "db_api.py")


@pytest.fixture(scope="session")
def frontend_module():
    return load("student1_frontend", STUDENT_DIR / "frontend" / "app.py")


@pytest.fixture()
def db_api(db_module, tmp_path, monkeypatch):
    """Fixture: the real database API on a fresh, seeded SQLite file."""
    monkeypatch.setattr(db_module, "DB_PATH", tmp_path / "preferences.db")
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


@pytest.fixture()
def calls():
    """Mock record: every outbound call the backend makes during a test."""
    return []


@pytest.fixture()
def services(backend_module, db_api):
    """Base URL -> in-process test client. Fixtures may add more services."""
    return {backend_module.DB_API_URL: db_api}


@pytest.fixture()
def backend_client(backend_module, services, monkeypatch, calls):
    def route(method):
        def fake(url, params=None, json=None, timeout=None, **kwargs):
            calls.append({"method": method, "url": url, "json": json,
                          "timeout": timeout})
            for base, client in services.items():
                if url.startswith(base):
                    resp = client.open(url[len(base):], method=method,
                                       query_string=params, json=json)
                    return RoutedResponse(resp)
            raise requests.ConnectionError(f"{url} is not running in this test")
        return fake

    for method in HTTP_METHODS:
        monkeypatch.setattr(backend_module.requests, method, route(method.upper()))
    # Cloud baseline whatever the local .env says; tests switch flags on as needed.
    for name in AI_FLAGS:
        monkeypatch.setattr(backend_module, name, False)
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
    backend_module.app.config["TESTING"] = True
    return backend_module.app.test_client()


def make_multi_agent_stub(store):
    """Stub of the shared Multi-Agent server with the same routes, validation
    and response shape as ai-services/multi-agent-server/app.py, but with
    canned agent output instead of model calls."""
    stub = Flask("multi_agent_stub")

    @stub.post("/workflow")
    def workflow():
        data = request.get_json(silent=True) or {}
        if not str(data.get("user_request", "")).strip():
            return jsonify({"status": "error", "error": "user_request is required"}), 400
        workflow_id = str(uuid.uuid4())
        record = {
            "status": "success",
            "workflow_id": workflow_id,
            "timestamp": "2026-10-22T00:00:00+00:00",
            "duration_ms": 1234,
            "user_request": data["user_request"],
            "service": data.get("service"),
            "task": data.get("task"),
            "context": data.get("context"),
            "participating_agents": ["planner_agent", "worker_agent", "reviewer_agent"],
            "planner_result": {"status": "success", "agent": "planner_agent",
                               "model": "stub", "plan": "1. Check budget, interests and needs."},
            "worker_result": {"status": "success", "agent": "worker_agent",
                              "model": "stub", "output": "BUDGET: 2000-4000 AUD"},
            "reviewer_result": {"status": "success", "agent": "reviewer_agent",
                                "model": "stub", "review": "Matches the supplied evidence."},
            "human_decision": {"required": True, "status": "pending",
                               "allowed_values": ["Accept", "Partially Accept", "Reject"]},
        }
        store[workflow_id] = record
        return jsonify(record)

    @stub.get("/workflow/<workflow_id>")
    def lookup(workflow_id):
        if workflow_id not in store:
            return jsonify({"status": "error", "error": "Workflow not found"}), 404
        return jsonify(store[workflow_id])

    @stub.post("/workflow/<workflow_id>/review")
    def review(workflow_id):
        if workflow_id not in store:
            return jsonify({"status": "error", "error": "Workflow not found"}), 404
        data = request.get_json(silent=True) or {}
        store[workflow_id]["human_decision"] = {
            "status": "recorded", "timestamp": "2026-10-22T00:05:00+00:00",
            "decision": data["decision"], "reason": data["reason"],
            "evidence": data.get("evidence", ""),
        }
        return jsonify(store[workflow_id])

    return stub


@pytest.fixture()
def workflow_store():
    """The stub server's saved workflows, so tests can add foreign ones."""
    return {}


@pytest.fixture()
def multi_agent(backend_module, backend_client, services, workflow_store, monkeypatch):
    """Multi-Agent mode switched on and routed to the stub server."""
    monkeypatch.setattr(backend_module, "MULTI_AGENT_ENABLED", True)
    services[backend_module.MULTI_AGENT_SERVICE_URL] = (
        make_multi_agent_stub(workflow_store).test_client())
    return workflow_store
