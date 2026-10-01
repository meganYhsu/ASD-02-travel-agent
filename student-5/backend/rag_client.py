from __future__ import annotations

from typing import Any

import requests

from config import RAG_SERVICE_URL, RAG_TIMEOUT_SECONDS


class RagError(Exception):
    def __init__(self, message: str, status: int = 503):
        super().__init__(message)
        self.message = message
        self.status = status


class RagClient:
    def __init__(self, base_url: str | None = None, timeout: int | None = None):
        self.base_url = (base_url or RAG_SERVICE_URL).rstrip("/")
        self.timeout = timeout or RAG_TIMEOUT_SECONDS

    def query(self, question: str) -> dict[str, Any]:
        try:
            response = requests.post(
                f"{self.base_url}/query",
                json={"question": question},
                timeout=self.timeout,
            )
        except requests.Timeout as exc:
            raise RagError("Shared travel assistant timed out") from exc
        except requests.RequestException as exc:
            raise RagError("Shared travel assistant is unavailable") from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise RagError("Invalid response from shared travel assistant", 502) from exc
        if not response.ok or not body.get("success"):
            raise RagError(body.get("error") or "Shared travel assistant request failed", response.status_code)
        data = body.get("data")
        if not isinstance(data, dict) or not isinstance(data.get("answer"), str):
            raise RagError("Invalid response from shared travel assistant", 502)
        return data