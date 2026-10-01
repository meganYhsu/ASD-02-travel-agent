# Shared MCP Server

Shared Model Context Protocol-style tool server used by student microservices. It exposes deterministic tools (no LLM calls) through a small HTTP contract: list available tools, then run one by name with arguments.

## Flow

```
Student frontend
  -> Student backend (/api/mcp/tools, /api/mcp/run)
  -> Shared MCP HTTP server (this service: /tools, /run)
  -> mcp_mode.py (selects the tool)
  -> tools.py (runs the tool, returns the result)
  -> MCP result
  -> Student backend
  -> Student frontend
```

## API

- `GET /health` — service status and the list of available tool names.
- `GET /tools` — tool metadata: `name`, `description`, `arguments`.
- `POST /run` — body `{ "tool": "<name>", "arguments": { ... } }`. Returns `{ "success": true, "data": { "tool", "result" } }`, or `404` for an unknown tool / `400` for a missing or invalid argument.

## Tools (`tools.py`)

- `days_until_departure(departure_date)`
- `passport_validity_check(expiry_date, return_date, minimum_validity_days)`
- `packing_climate_tip(climate)`

## Run on the host

This server is intended to run directly on the host machine (not inside Docker), so that a containerised student backend reaches it via the host rather than its own container localhost:

```powershell
cd ai-services/mcp-server
pip install -r requirements.txt
python app.py
```

It listens on port `7100` by default (`PORT` env var).

## Confirm it is running

```powershell
curl.exe http://localhost:7100/health
curl.exe http://localhost:7100/tools
curl.exe -X POST http://localhost:7100/run -H "Content-Type: application/json" -d '{"tool":"packing_climate_tip","arguments":{"climate":"rainy"}}'
```

## Tests

```powershell
python -m pytest ai-services/mcp-server -q
```

## Connecting a containerised student backend

Set the backend's `MCP_BASE_URL` to the host, not `127.0.0.1` (which inside a container means the container itself):

- Docker Desktop (Windows/Mac): `http://host.docker.internal:7100`
- Docker on Linux: add `extra_hosts: ["host.docker.internal:host-gateway"]` to the backend service, then use the same URL.
