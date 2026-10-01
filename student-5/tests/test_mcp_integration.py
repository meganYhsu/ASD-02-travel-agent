from mcp_client import McpError


class FakeMcp:
    def __init__(self, tools=None, result=None, error=None):
        self.tools = tools if tools is not None else [
            {"name": "days_until_departure", "description": "desc", "arguments": ["departure_date"]}
        ]
        self.result = result or {"tool": "days_until_departure", "result": {"days_until_departure": 5}}
        self.error = error
        self.calls = []

    def list_tools(self):
        if self.error:
            raise self.error
        return self.tools

    def run_tool(self, tool, arguments):
        self.calls.append((tool, arguments))
        if self.error:
            raise self.error
        return self.result


def test_mcp_tools_lists_available_tools(api_app):
    api_app.config["MCP"] = FakeMcp()
    response = api_app.test_client().get("/api/mcp/tools")
    data = response.get_json()["data"]
    assert response.status_code == 200
    assert data[0]["name"] == "days_until_departure"


def test_mcp_tools_reports_shared_service_failure(api_app):
    api_app.config["MCP"] = FakeMcp(error=McpError("Shared MCP server is unavailable"))
    response = api_app.test_client().get("/api/mcp/tools")
    assert response.status_code == 503
    assert response.get_json()["error"] == "Shared MCP server is unavailable"


def test_mcp_run_forwards_tool_and_arguments(api_app):
    fake_mcp = FakeMcp()
    api_app.config["MCP"] = fake_mcp
    response = api_app.test_client().post(
        "/api/mcp/run",
        json={"tool": "days_until_departure", "arguments": {"departure_date": "2026-09-01"}},
    )
    data = response.get_json()["data"]
    assert response.status_code == 200
    assert fake_mcp.calls == [("days_until_departure", {"departure_date": "2026-09-01"})]
    assert data["result"]["days_until_departure"] == 5


def test_mcp_run_requires_tool_name(client):
    response = client.post("/api/mcp/run", json={"arguments": {}})
    assert response.status_code == 400
    assert response.get_json()["error"] == "tool is required"


def test_mcp_run_rejects_non_object_arguments(client):
    response = client.post("/api/mcp/run", json={"tool": "days_until_departure", "arguments": "nope"})
    assert response.status_code == 400
    assert response.get_json()["error"] == "arguments must be an object"


def test_mcp_run_reports_shared_service_failure(api_app):
    api_app.config["MCP"] = FakeMcp(error=McpError("Unknown tool: nonsense", 404))
    response = api_app.test_client().post(
        "/api/mcp/run", json={"tool": "nonsense", "arguments": {}}
    )
    assert response.status_code == 404
    assert response.get_json()["error"] == "Unknown tool: nonsense"
