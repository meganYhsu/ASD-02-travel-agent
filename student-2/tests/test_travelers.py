"""CRUD coverage for the Travelers table."""


def test_seed_data_has_at_least_ten_records(client):
    response = client.get("/api/travelers")
    assert response.status_code == 200
    assert len(response.get_json()["data"]) >= 10


def test_create_read_update_delete(client):
    created = client.post(
        "/api/travelers",
        json={
            "full_name": "Nina Patel",
            "username": "nina.p",
            "email": "nina.patel@example.com",
            "home_location": "Melbourne, Australia",
            "travel_style": "Luxury",
        },
    )
    assert created.status_code == 201
    record = created.get_json()["data"]
    record_id = record["id"]
    assert record["travel_style"] == "Luxury"

    read = client.get(f"/api/travelers/{record_id}")
    assert read.status_code == 200
    assert read.get_json()["data"]["username"] == "nina.p"

    updated = client.put(f"/api/travelers/{record_id}", json={"travel_style": "Budget"})
    assert updated.status_code == 200
    assert updated.get_json()["data"]["travel_style"] == "Budget"

    assert client.delete(f"/api/travelers/{record_id}").status_code == 204
    assert client.get(f"/api/travelers/{record_id}").status_code == 404


def test_email_is_normalised_to_lowercase(client):
    response = client.post(
        "/api/travelers",
        json={
            "full_name": "Case Test",
            "username": "case.test",
            "email": "Case.Test@Example.COM",
            "home_location": "Perth",
            "travel_style": "Budget",
        },
    )
    assert response.get_json()["data"]["email"] == "case.test@example.com"


def test_duplicate_email_is_rejected(client):
    payload = {
        "full_name": "Duplicate",
        "username": "dup.one",
        "email": "aiko.tanaka@example.com",
        "home_location": "Sydney",
        "travel_style": "Budget",
    }
    assert client.post("/api/travelers", json=payload).status_code == 409


def test_invalid_travel_style_is_rejected(client):
    response = client.post(
        "/api/travelers",
        json={
            "full_name": "Bad Style",
            "username": "bad.style",
            "email": "bad.style@example.com",
            "home_location": "Sydney",
            "travel_style": "Backpacker",
        },
    )
    assert response.status_code == 400
    assert "travel_style" in response.get_json()["error"]


def test_invalid_email_is_rejected(client):
    response = client.post(
        "/api/travelers",
        json={
            "full_name": "Bad Email",
            "username": "bad.email",
            "email": "not-an-email",
            "home_location": "Sydney",
            "travel_style": "Budget",
        },
    )
    assert response.status_code == 400


def test_filter_by_travel_style(client):
    response = client.get("/api/travelers?travel_style=Luxury")
    assert response.status_code == 200
    assert all(item["travel_style"] == "Luxury" for item in response.get_json()["data"])
