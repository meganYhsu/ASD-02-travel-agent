
"""Collect recorded evidence for the Multi-Agent Workflow Review."""

import json
from pathlib import Path


MAX_RECORDS = 3
MAX_FILE_BYTES = 2_000_000
MAX_EVIDENCE_CHARS = 24000


def read_recent_jsonl(path: Path) -> list[dict]:
    """Read recent JSONL records without executing their contents."""
    if not path.is_file():
        return []

    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError(f"Evidence file exceeds size limit: {path.name}")

    records = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue

            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError(f"Invalid record in {path.name}")

            records.append(record)

    return records[-MAX_RECORDS:]


def collect(app_dir: Path, repo_root: Path) -> tuple[bool, str]:
    """Return evidence for the shared agentic loop."""
    server_dir = repo_root / "ai-services" / "multi-agent-server"

    paths = {
        "workflow_history": server_dir / "workflow_history.jsonl",
        "coordination_audit": server_dir / "coordination_audit.jsonl",
        "human_reviews": server_dir / "human_reviews.jsonl",
    }

    if not paths["workflow_history"].is_file():
        return False, "Missing workflow_history.jsonl. Run the Multi-Agent Server first."

    try:
        history = read_recent_jsonl(paths["workflow_history"])
        if not history:
            return False, "Workflow history is empty."

        latest = history[-1]
        workflow_id = latest.get("workflow_id")
        if not isinstance(workflow_id, str) or not workflow_id:
            return False, "Latest workflow has no valid workflow_id."

        audit = [
            record
            for record in read_recent_jsonl(paths["coordination_audit"])
            if record.get("workflow_id") == workflow_id
        ]

        human_reviews = [
            record
            for record in read_recent_jsonl(paths["human_reviews"])
            if record.get("workflow_id") == workflow_id
        ]

        evidence = {
            "workflow": {
                "workflow_id": workflow_id,
                "status": latest.get("status"),
                "timestamp": latest.get("timestamp"),
                "duration_ms": latest.get("duration_ms"),
                "user_request": latest.get("user_request"),
                "service": latest.get("service"),
                "task": latest.get("task"),
                "participating_agents": latest.get("participating_agents"),
                "planner_result": latest.get("planner_result"),
                "worker_result": latest.get("worker_result"),
                "reviewer_result": latest.get("reviewer_result"),
                "human_decision": latest.get("human_decision"),
            },
            "coordination_audit": audit,
            "human_reviews": human_reviews,
            "missing_files": [
                name
                for name, path in paths.items()
                if not path.is_file()
            ],
        }


        text = json.dumps(evidence, ensure_ascii=False, indent=2)

        if len(text) > MAX_EVIDENCE_CHARS:
            return False, (
                "Workflow evidence exceeds the review input limit. "
                "Reduce the evidence size before review."
            )

        return True, text

    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return False, f"Evidence collection failed: {exc}"
