from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


class DatabaseUnavailable(Exception):
    pass


class DatabaseClient:
    """HTTP client for the student-2 database microservice.

    Other microservices must reach this data through the database API only --
    never by opening the SQLite file directly.
    """

    def __init__(self, base_url: str | None = None, test_client: Any | None = None):
        self.base_url = (base_url or "").rstrip("/")
        self.test_client = test_client

    def request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> tuple[int, Any]:
        if self.test_client is not None:
            response = self.test_client.open(
                path,
                method=method.upper(),
                json=json,
                query_string=params,
            )
            if response.status_code == 204:
                return 204, None
            return response.status_code, response.get_json()
        url = f"{self.base_url}{path}"
        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                json=json,
                params=params,
                timeout=10,
            )
        except requests.RequestException as exc:
            logger.error("Database service unavailable")
            raise DatabaseUnavailable("Database service unavailable") from exc
        if response.status_code == 204:
            return 204, None
        try:
            return response.status_code, response.json()
        except ValueError:
            return response.status_code, {"success": False, "error": "Invalid database response"}

    def list(self, resource: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        status, body = self.request("GET", f"/{resource}", params=params)
        if status != 200 or not body or not body.get("success"):
            return []
        return body.get("data") or []

    def get(self, resource: str, record_id: int) -> tuple[int, Any]:
        return self.request("GET", f"/{resource}/{record_id}")

    def create(self, resource: str, payload: dict[str, Any]) -> tuple[int, Any]:
        return self.request("POST", f"/{resource}", json=payload)

    def update(self, resource: str, record_id: int, payload: dict[str, Any]) -> tuple[int, Any]:
        return self.request("PUT", f"/{resource}/{record_id}", json=payload)

    def delete(self, resource: str, record_id: int) -> tuple[int, Any]:
        return self.request("DELETE", f"/{resource}/{record_id}")

    def profile(self, traveler_id: int) -> tuple[int, Any]:
        return self.request("GET", f"/travelers/{traveler_id}/profile")
