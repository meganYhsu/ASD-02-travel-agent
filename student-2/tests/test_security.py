"""Input-handling and injection resistance for the student-2 microservices."""


def test_sql_injection_in_filter_does_not_drop_tables(client):
    response = client.get("/api/travelers?email=' OR 1=1; DROP TABLE Travelers;--")
    assert response.status_code == 200
    # Parameterised query: the literal never matches, and the table survives.
    assert response.get_json()["data"] == []
    assert len(client.get("/api/travelers").get_json()["data"]) >= 10


def test_sql_injection_in_body_is_stored_as_plain_text(client):
    payload = {
        "full_name": "Robert'); DROP TABLE Travelers;--",
        "username": "bobby.tables",
        "email": "bobby.tables@example.com",
        "home_location": "Sydney",
        "travel_style": "Budget",
    }
    created = client.post("/api/travelers", json=payload)
    assert created.status_code == 201
    assert created.get_json()["data"]["full_name"] == payload["full_name"]
    assert len(client.get("/api/travelers").get_json()["data"]) >= 11


def test_unknown_filter_columns_are_ignored(client):
    response = client.get("/api/travelers?id=1&nonsense=x")
    assert response.status_code == 200
    # `id` is not an allowed filter, so the full list comes back unfiltered.
    assert len(response.get_json()["data"]) >= 10


def test_malformed_json_is_rejected(client):
    response = client.post(
        "/api/travelers", data="{not json", content_type="application/json"
    )
    assert response.status_code == 400


def test_non_object_body_is_rejected(client):
    response = client.post("/api/travelers", json=["not", "an", "object"])
    assert response.status_code == 400


def test_non_integer_ids_are_rejected(client):
    assert client.get("/api/travelers/abc").status_code == 400
    assert client.delete("/api/travelers/1;DROP").status_code == 400


def test_negative_and_zero_ids_are_rejected(client):
    assert client.get("/api/travelers/0").status_code == 400
    assert client.get("/api/travelers/-1").status_code == 400


def test_unknown_resource_returns_404(client):
    assert client.get("/api/not-a-resource").status_code == 404
