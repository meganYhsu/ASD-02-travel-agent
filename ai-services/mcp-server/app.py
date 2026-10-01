"""Shared MCP HTTP server. Dispatches tool-run requests to mcp_mode / tools."""

from __future__ import annotations

import os

from flask import Flask, jsonify, request

import mcp_mode
from tools import ToolError


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/health")
    def health():
        return jsonify(
            {
                "status": "ok",
                "service": "shared-mcp",
                "tools": [tool["name"] for tool in mcp_mode.list_tools()],
            }
        )

    @app.get("/tools")
    def tools():
        return jsonify({"success": True, "data": mcp_mode.list_tools()})

    @app.post("/run")
    def run():
        payload = request.get_json(silent=True)
        tool_name = payload.get("tool", "").strip() if isinstance(payload, dict) else ""
        arguments = payload.get("arguments") if isinstance(payload, dict) else None
        if not tool_name:
            return jsonify({"success": False, "error": "tool is required"}), 400
        if arguments is not None and not isinstance(arguments, dict):
            return jsonify({"success": False, "error": "arguments must be an object"}), 400

        try:
            result = mcp_mode.run_tool(tool_name, arguments)
        except mcp_mode.UnknownToolError:
            return jsonify({"success": False, "error": f"Unknown tool: {tool_name}"}), 404
        except ToolError as exc:
            return jsonify({"success": False, "error": exc.message}), 400

        return jsonify({"success": True, "data": {"tool": tool_name, "result": result}})

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "7100")))
