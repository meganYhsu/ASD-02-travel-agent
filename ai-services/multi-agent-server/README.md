# Shared Multi-Agent Server

This is the shared non-containerised local Planner/Worker/Reviewer service. It calls the local Ollama OpenAI-compatible chat endpoint and is intentionally omitted from Docker Compose.

## Start

From the repository root, start Ollama with the configured models, then run:

```bash
node ai-services/multi-agent-server/server.js
```

The service listens on `127.0.0.1:7010` by default. Set `MULTI_AGENT_HOST=0.0.0.0` when a Docker-hosted backend needs to reach it, and set the backend's `MULTI_AGENT_SERVICE_URL` to the host address.

## API

- `GET /health` reports service and model configuration.
- `POST /workflows` accepts `student`, `task`, `evidence`, and `review_mode` (`workflow`, `testing_report`, or `cloud_deployment_report`). It runs Planner, Worker, then Reviewer and returns an `awaiting_human_review` workflow.
- `GET /workflows/<workflow_id>` retrieves the in-memory workflow.
- `POST /workflows/<workflow_id>/review` accepts a human decision (`Accept`, `Partially Accept`, or `Reject`) and an optional note.

Workflow state is held in memory and is removed when the process restarts. The shared CLI agentic loop separately records its review evidence to `ai-services/ai-mode/reviews/<student>`.

## Configuration

- `MULTI_AGENT_HOST`, default `127.0.0.1`
- `MULTI_AGENT_PORT`, default `7010`
- `OLLAMA_BASE_URL`, default `http://127.0.0.1:11434/v1`
- `PLANNER_MODEL`, default `OLLAMA_MODEL` or `qwen2.5:0.5b`
- `WORKER_MODEL`, default `IMPLEMENTATION_MODEL`, then `OLLAMA_MODEL`, then `qwen2.5:0.5b`
- `REVIEWER_MODEL`, default `REVIEW_MODEL` or `qwen2.5:0.5b`
- `MULTI_AGENT_TIMEOUT_MS`, per-agent model timeout, default `180000`
