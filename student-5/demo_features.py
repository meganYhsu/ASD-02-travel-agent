"""Quick read-only demo of the student-5 travel preparation features.

Run from the repository root:
    python student-5/demo_features.py

Add --ai to call Ollama for compliance and checklist generation.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import requests


DEFAULT_API = "http://127.0.0.1:5505"
DEMO_TRIP = {
    "trip_id": "trip-001",
    "traveller_id": "traveller-001",
    "destination": "Japan",
    "nationality": "Australian",
    "departure_date": "2026-09-01",
    "return_date": "2026-09-10",
}
DEMO_GENERATION = {
    **DEMO_TRIP,
    "start_date": DEMO_TRIP["departure_date"],
    "end_date": DEMO_TRIP["return_date"],
    "climate": "mild",
    "planned_activities": ["hiking", "business meeting"],
}


def print_section(title: str, value: Any) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(value, indent=2, default=str))


def get_json(session: requests.Session, base_url: str, path: str, **kwargs: Any) -> Any:
    response = session.get(f"{base_url}{path}", timeout=15, **kwargs)
    response.raise_for_status()
    return response.json()


def post_json(session: requests.Session, base_url: str, path: str, payload: dict[str, Any]) -> Any:
    response = session.post(f"{base_url}{path}", json=payload, timeout=90)
    response.raise_for_status()
    return response.json()


def main() -> int:
    parser = argparse.ArgumentParser(description="Show the student-5 travel preparation features.")
    parser.add_argument("--api", default=DEFAULT_API, help=f"Backend API URL (default: {DEFAULT_API})")
    parser.add_argument("--ai", action="store_true", help="Also call Ollama-backed AI features")
    args = parser.parse_args()
    base_url = args.api.rstrip("/")

    session = requests.Session()
    try:
        health = get_json(session, base_url, "/health")
        print_section("Service health", health)

        documents = get_json(session, base_url, "/api/documents")
        print_section("Travel documents", documents)

        requirements = get_json(
            session,
            base_url,
            "/api/entry-requirements",
            params={"destination": "Japan", "nationality": "Australian"},
        )
        print_section("Entry requirements", requirements)

        alerts = post_json(session, base_url, "/api/alerts/compliance", DEMO_TRIP)
        print_section("Compliance alerts", alerts)

        packing = get_json(session, base_url, "/api/packing-lists", params={"trip_id": "trip-001"})
        print_section("Packing lists", packing)

        tasks = get_json(session, base_url, "/api/pre-trip-tasks", params={"trip_id": "trip-001"})
        progress = get_json(session, base_url, "/api/pre-trip-tasks/progress", params={"trip_id": "trip-001"})
        print_section("Pre-trip tasks", tasks)
        print_section("Task progress", progress)

        agentic = get_json(session, base_url, "/api/agentic/status", params=DEMO_TRIP)
        print_section("Plan -> Act -> Observe -> Adapt", agentic)

        if args.ai:
            compliance = post_json(session, base_url, "/api/ai/check-compliance", DEMO_TRIP)
            print_section("AI compliance check", compliance)
            generated = post_json(session, base_url, "/api/ai/generate-pretrip-checklist", DEMO_GENERATION)
            print_section("AI checklist suggestions (review before saving)", generated)
        else:
            print("\nAI features skipped. Run with --ai when Ollama is available.")
    except requests.RequestException as exc:
        print(f"Demo could not reach {base_url}: {exc}", file=sys.stderr)
        print("Start the stack with: python student-5/run_all.py", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
