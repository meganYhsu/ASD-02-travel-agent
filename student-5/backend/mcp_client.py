from __future__ import annotations

from typing import Any

import requests

from config import MCP_ENABLED, MCP_SERVICE_URL, MCP_TIMEOUT_SECONDS


class McpError(Exception):
    def __init__(self, message: str, status: int = 503):
        super().__init__(message)
        self.message = message
        self.status = status


class McpClient:
    def __init__(self, base_url: str | None = None, timeout: int | None = None):
        self.base_url = (base_url or MCP_SERVICE_URL).rstrip("/")
        self.timeout = timeout or MCP_TIMEOUT_SECONDS

    def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        if not MCP_ENABLED:
            raise McpError("MCP is disabled", 503)
        try:
            response = requests.request(method, f"{self.base_url}{path}", timeout=self.timeout, **kwargs)
        except requests.Timeout as exc:
            raise McpError("Shared MCP server timed out") from exc
        except requests.RequestException as exc:
            raise McpError("Shared MCP server is unavailable") from exc
        try:
            body = response.json()
        except ValueError as exc:
            raise McpError("Invalid response from shared MCP server", 502) from exc
        if not isinstance(body, dict) or not response.ok or not body.get("ok"):
            message = body.get("error", "MCP request failed") if isinstance(body, dict) else "MCP request failed"
            raise McpError(message, response.status_code if response.status_code >= 400 else 502)
        return body

    def list_tools(self) -> list[str]:
        body = self._request("GET", "/mcp/tools")
        tools = body.get("tools")
        if not isinstance(tools, list) or not all(isinstance(tool, str) for tool in tools):
            raise McpError("Invalid tool list from shared MCP server", 502)
        return tools

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        tools = self.list_tools()
        if tool_name not in tools:
            raise McpError(f"Unknown MCP tool: {tool_name}", 400)
        body = self._request("POST", "/mcp/tool", json={"tool_name": tool_name, "arguments": arguments})
        if "result" not in body:
            raise McpError("Invalid tool result from shared MCP server", 502)
        return {"tool_name": tool_name, "result": body["result"]}
