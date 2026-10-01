import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from mcp_mode import list_mcp_tools, run_mcp_tool


HOST = "127.0.0.1"
PORT = 7004


class MCPRequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code, payload):
        body = json.dumps(payload).encode("utf-8")

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send_json(200, {"ok": True})

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"ok": True})
            return

        if self.path == "/mcp/tools":
            self._send_json(200, {
                "ok": True,
                "tools": list_mcp_tools()
            })
            return

        self._send_json(404, {
            "ok": False,
            "error": "Route not found"
        })

    def do_POST(self):
        if self.path != "/mcp/tool":
            self._send_json(404, {
                "ok": False,
                "error": "Route not found"
            })
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length).decode("utf-8")
            body = json.loads(raw_body or "{}")

            tool_name = body.get("tool_name")
            arguments = body.get("arguments") or {}

            if not tool_name:
                self._send_json(400, {
                    "ok": False,
                    "error": "tool_name is required"
                })
                return

            result = run_mcp_tool(tool_name, **arguments)

            self._send_json(200, {
                "ok": True,
                "tool_name": tool_name,
                "result": result
            })

        except Exception as error:
            self._send_json(500, {
                "ok": False,
                "error": str(error)
            })


def main():
    server = ThreadingHTTPServer((HOST, PORT), MCPRequestHandler)
    print(f"MCP HTTP server running on http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
