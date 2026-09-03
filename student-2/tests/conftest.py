from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DB_DIR = ROOT / "database"
API_DIR = ROOT / "backend"


def load_module(name: str, file_path: Path, extra_path: Path):
    extra = str(extra_path)
    if extra not in sys.path:
        sys.path.insert(0, extra)
    spec = importlib.util.spec_from_file_location(name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


db_app_module = load_module("student2_db_app", DB_DIR / "app.py", DB_DIR)
api_app_module = load_module("student2_api_app", API_DIR / "app.py", API_DIR)


class FakeOllama:
    """Stand-in for Ollama so tests never need a running LLM."""

    def __init__(self, payload=None, error=None):
        self.payload = payload or {}
        self.error = error
        self.prompts = []

    def generate_json(self, prompt: str):
        self.prompts.append(prompt)
        if self.error:
            raise self.error
        return self.payload


@pytest.fixture
def db_app(tmp_path):
    db_path = tmp_path / "traveler_preferences.db"
    app = db_app_module.create_app(str(db_path))
    app.config["TESTING"] = True
    return app


@pytest.fixture
def db_client(db_app):
    return db_app.test_client()


@pytest.fixture
def fake_ollama():
    return FakeOllama(
        payload={
            "summary": "Mid-range traveller who prefers a balanced pace.",
            "planning_hints": ["Honour vegetarian dining requirements."],
            "suggested_interests": [
                {"interest_category": "Beaches", "reason": "Warm-climate destinations suit this profile."},
                {"interest_category": "Not A Real Category", "reason": "Should be filtered out."},
            ],
            "reasoning": "Derived only from the supplied traveller records.",
            "next_steps": ["Add at least three interests."],
        }
    )


@pytest.fixture
def api_app(db_client, fake_ollama):
    from db_client import DatabaseClient

    app = api_app_module.create_app(
        db_client=DatabaseClient(test_client=db_client),
        ollama_client=fake_ollama,
    )
    app.config["TESTING"] = True
    app.config["FAKE_OLLAMA"] = fake_ollama
    return app


@pytest.fixture
def client(api_app):
    return api_app.test_client()


@pytest.fixture
def new_traveler(client):
    """Create an empty traveller and return its id."""
    response = client.post(
        "/api/travelers",
        json={
            "full_name": "Test Traveller",
            "username": "test.traveller",
            "email": "test.traveller@example.com",
            "home_location": "Sydney, Australia",
            "travel_style": "Mid-range",
        },
    )
    assert response.status_code == 201
    return response.get_json()["data"]["id"]
