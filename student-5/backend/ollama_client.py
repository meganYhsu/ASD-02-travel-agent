from __future__ import annotations

import json
import logging
import re
from typing import Any

import requests

from config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    def __init__(self, message: str, status: int = 503):
        super().__init__(message)
        self.message = message
        self.status = status


def extract_json(text: str) -> dict[str, Any]:
    if not text or not text.strip():
        raise OllamaError("Malformed AI response", 502)
    raw = text.strip()
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise OllamaError("Malformed AI response", 502)
        return parsed
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not match:
            raise OllamaError("Malformed AI response", 502)
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise OllamaError("Malformed AI response", 502) from exc
        if not isinstance(parsed, dict):
            raise OllamaError("Malformed AI response", 502)
        return parsed


class OllamaClient:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
        generate_fn=None,
    ):
        self.base_url = (base_url or OLLAMA_BASE_URL).rstrip("/")
        self.model = model or OLLAMA_MODEL
        self.timeout = timeout or OLLAMA_TIMEOUT_SECONDS
        self.generate_fn = generate_fn

    def generate_json(self, prompt: str) -> dict[str, Any]:
        if self.generate_fn is not None:
            return extract_json(self.generate_fn(prompt))

        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }
        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
        except requests.Timeout as exc:
            logger.warning("Ollama request timed out")
            raise OllamaError("AI service timed out", 503) from exc
        except requests.RequestException as exc:
            logger.warning("Ollama is unavailable")
            raise OllamaError("AI service unavailable", 503) from exc

        if response.status_code >= 500:
            raise OllamaError("AI service unavailable", 503)
        if response.status_code >= 400:
            raise OllamaError("AI service rejected the request", 503)
        try:
            body = response.json()
        except ValueError as exc:
            raise OllamaError("Malformed AI response", 502) from exc
        return extract_json(body.get("response", ""))
