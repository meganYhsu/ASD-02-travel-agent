def test_sql_injection_is_treated_as_value(client):
    payload = "traveller-001' OR '1'='1"
    response = client.get("/api/documents", query_string={"traveller_id": payload})
    assert response.status_code == 200
    assert response.get_json()["data"] == []


def test_invalid_payloads_are_rejected(client):
    assert client.post("/api/documents", json=["not", "an", "object"]).status_code == 400
    assert client.get("/api/documents/not-a-number").status_code == 400
    assert client.post("/api/packing-lists", json={"trip_id": "x"}).status_code == 400


def test_document_numbers_are_masked(client):
    created = client.post(
        "/api/documents",
        json={
            "traveller_id": "traveller-mask",
            "document_type": "Passport",
            "document_number": "SECRET99",
            "issuing_country": "Australia",
            "nationality": "Australian",
            "issue_date": "2020-01-01",
            "expiry_date": "2030-01-01",
        },
    )
    number = created.get_json()["data"]["document_number"]
    assert "SECRET" not in number
    assert number.endswith("ET99")
