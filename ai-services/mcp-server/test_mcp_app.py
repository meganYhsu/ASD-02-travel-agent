from app import create_app


def make_client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_health_lists_tool_names():
    client = make_client()
    response = client.get("/health")
    assert response.status_code == 200
    body = response.get_json()
    assert "passport_validity_check" in body["tools"]


def test_tools_endpoint_returns_metadata():
    client = make_client()
    response = client.get("/tools")
    data = response.get_json()["data"]
    names = {tool["name"] for tool in data}
    assert {"days_until_departure", "passport_validity_check", "packing_climate_tip"} <= names


def test_run_passport_validity_check_returns_result():
    client = make_client()
    response = client.post(
        "/run",
        json={
            "tool": "passport_validity_check",
            "arguments": {
                "expiry_date": "2027-01-01",
                "return_date": "2026-09-10",
                "minimum_validity_days": 90,
            },
        },
    )
    data = response.get_json()["data"]
    assert response.status_code == 200
    assert data["tool"] == "passport_validity_check"
    assert data["result"]["meets_minimum_validity"] is True


def test_run_unknown_tool_returns_404():
    client = make_client()
    response = client.post("/run", json={"tool": "not_a_real_tool", "arguments": {}})
    assert response.status_code == 404
    assert "Unknown tool" in response.get_json()["error"]


def test_run_requires_tool_name():
    client = make_client()
    response = client.post("/run", json={"arguments": {}})
    assert response.status_code == 400
    assert response.get_json()["error"] == "tool is required"


def test_run_missing_required_argument_returns_400():
    client = make_client()
    response = client.post("/run", json={"tool": "days_until_departure", "arguments": {}})
    assert response.status_code == 400
    assert "Missing required argument" in response.get_json()["error"]


def test_run_rejects_non_object_arguments():
    client = make_client()
    response = client.post("/run", json={"tool": "days_until_departure", "arguments": "nope"})
    assert response.status_code == 400
    assert response.get_json()["error"] == "arguments must be an object"
