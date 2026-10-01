from __future__ import annotations

from typing import Any

import requests

from config import MCP_BASE_URL, MCP_TIMEOUT_SECONDS


class McpError(Exception):
    def __init__(self, message: str, status: int = 503):
        super().__init__(message)
        self.message = message
        self.status = status


class McpClient:
    """HTTP client for the shared MCP server (student backend -> shared MCP HTTP server)."""

    def __init__(self, base_url: str | None = None, timeout: int | None = None):
        self.base_url = (base_url or MCP_BASE_URL).rstrip("/")
        self.timeout = timeout or MCP_TIMEOUT_SECONDS

    def _call(self, method: str, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            response = requests.request(method, f"{self.base_url}{path}", json=json, timeout=self.timeout)
        except requests.Timeout as exc:
            raise McpError("Shared MCP server timed out") from exc
        except requests.RequestException as exc:
            raise McpError("Shared MCP server is unavailable") from exc
        try:
            body = response.json()
        except ValueError as exc:
            raise McpError("Invalid response from shared MCP server", 502) from exc
        if not response.ok or not body.get("success"):
            raise McpError(body.get("error") or "Shared MCP server request failed", response.status_code)
        return body

    def list_tools(self) -> list[dict[str, Any]]:
        data = self._call("GET", "/tools").get("data")
        if not isinstance(data, list):
            raise McpError("Invalid response from shared MCP server", 502)
        return data

    def run_tool(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        data = self._call("POST", "/run", json={"tool": tool, "arguments": arguments}).get("data")
        if not isinstance(data, dict):
            raise McpError("Invalid response from shared MCP server", 502)
        return data
