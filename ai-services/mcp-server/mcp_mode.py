"""Tool selection and execution for the shared MCP HTTP server."""

from __future__ import annotations

from typing import Any

from tools import TOOLS


class UnknownToolError(Exception):
    def __init__(self, tool_name: str):
        super().__init__(f"Unknown tool: {tool_name}")
        self.tool_name = tool_name


def list_tools() -> list[dict[str, Any]]:
    return [
        {"name": name, "description": spec["description"], "arguments": spec["arguments"]}
        for name, spec in sorted(TOOLS.items())
    ]


def run_tool(tool_name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
    spec = TOOLS.get(tool_name)
    if spec is None:
        raise UnknownToolError(tool_name)
    handler = spec["handler"]
    return handler(arguments or {})
