"""Run a travel-project assessment from the terminal and print its JSON report."""

import argparse
import json

from coordinator import run_workflow


DEFAULT_REQUEST = (
    "Review student-4's Plan Itinerary feature in the ASD-02 Travel Agent project. "
    "Assess frontend, backend, database, saved-itinerary RAG, and MCP travel-tool "
    "integration using available evidence. Identify gaps and recommended checks; "
    "do not claim tests passed without results. Keep release approval pending "
    "explicit human review."
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the ASD-02 Travel Agent Planner, Worker, and Reviewer workflow."
    )
    parser.add_argument(
        "--request",
        default=DEFAULT_REQUEST,
        help="Travel feature or task to assess (default: student-4 Plan Itinerary)."
    )
    args = parser.parse_args()
    user_request = args.request.strip()
    if not user_request:
        parser.error("--request must not be empty")

    result = run_workflow(
        user_request
    )

    print(
        json.dumps(
            result,
            indent=2
        )
    )


if __name__ == "__main__":
    main()
