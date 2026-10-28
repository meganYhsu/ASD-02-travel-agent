import importlib.util
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

# Locate Student 2 backend
BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
BACKEND_APP = BACKEND_DIR / "app.py"

# Allow Python to import backend modules such as llm_client
sys.path.insert(0, str(BACKEND_DIR))

# Import the actual Flask backend
spec = importlib.util.spec_from_file_location(
    "student2_backend_app",
    BACKEND_APP
)

backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)



@pytest.fixture
def client():
    backend.app.config["TESTING"] = True
    with backend.app.test_client() as client:
        yield client


# Test 1: GET /bookings
def test_get_bookings(client, monkeypatch):
    bookings = [
        {"id": 1, "trip_id": 10},
        {"id": 2, "trip_id": 20}
    ]

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = bookings

    mock_get = Mock(return_value=mock_response)

    monkeypatch.setattr(
        backend.requests,
        "get",
        mock_get
    )

    response = client.get("/bookings")

    assert response.status_code == 200
    assert response.get_json() == bookings

    mock_get.assert_called_once_with(
        f"{backend.DATABASE_URL}/bookings",
        timeout=15
    )


# Test 2: POST /itineraries - valid data
def test_create_itinerary_success(client, monkeypatch):
    itinerary = {
        "trip_id": 10,
        "date": "2026-11-10",
        "time": "10:00",
        "activity": "Museum Visit",
        "location": "Melbourne"
    }

    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "id": 1,
        **itinerary
    }

    mock_post = Mock(return_value=mock_response)

    monkeypatch.setattr(
        backend.requests,
        "post",
        mock_post
    )

    response = client.post(
        "/itineraries",
        json=itinerary
    )

    assert response.status_code == 201
    assert response.get_json()["activity"] == "Museum Visit"

    mock_post.assert_called_once_with(
        f"{backend.DATABASE_URL}/itineraries",
        json=itinerary,
        timeout=15
    )


# Test 3: POST /itineraries - missing field
def test_create_itinerary_missing_field(client, monkeypatch):
    mock_post = Mock()

    monkeypatch.setattr(
        backend.requests,
        "post",
        mock_post
    )

    invalid_itinerary = {
        "trip_id": 10,
        "date": "2026-11-10",
        "time": "10:00",
        "location": "Melbourne"
    }

    response = client.post(
        "/itineraries",
        json=invalid_itinerary
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Missing required field: activity"
    }

    mock_post.assert_not_called()
