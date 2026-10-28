"""HTTP client for the shared local Planner/Worker/Reviewer service."""

from __future__ import annotations

from typing import Any

import requests

from config import MULTI_AGENT_SERVICE_URL, MULTI_AGENT_TIMEOUT_SECONDS


class MultiAgentError(Exception):
    def __init__(self, message: str, status: int = 503):
        super().__init__(message)
        self.message = message
        self.status = status


class MultiAgentClient:
    def __init__(self, base_url: str | None = None, timeout: int | None = None):
        self.base_url = (base_url or MULTI_AGENT_SERVICE_URL).rstrip("/")
        self.timeout = timeout or MULTI_AGENT_TIMEOUT_SECONDS

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            response = requests.request(
                method, f"{self.base_url}{path}", json=payload, timeout=self.timeout
            )
        except requests.Timeout as exc:
            raise MultiAgentError("Shared Multi-Agent Server timed out", 503) from exc
        except requests.RequestException as exc:
            raise MultiAgentError("Shared Multi-Agent Server is unavailable", 503) from exc
        try:
            body = response.json()
        except ValueError as exc:
            raise MultiAgentError("Invalid response from shared Multi-Agent Server", 502) from exc
        if not isinstance(body, dict) or not response.ok or not body.get("ok"):
            message = body.get("error", "Multi-Agent request failed") if isinstance(body, dict) else "Multi-Agent request failed"
            raise MultiAgentError(message, response.status_code if response.status_code >= 400 else 502)
        workflow = body.get("workflow")
        if not isinstance(workflow, dict):
            raise MultiAgentError("Multi-Agent Server returned an invalid workflow", 502)
        return workflow

    def create_workflow(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", "/workflows", payload)

    def submit_review(self, workflow_id: str, decision: str, note: str = "") -> dict[str, Any]:
        return self.request("POST", f"/workflows/{workflow_id}/review", {"decision": decision, "note": note})
