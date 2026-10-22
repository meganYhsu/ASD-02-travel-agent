import json
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from agents.planner_agent import plan_workflow
from agents.worker_agent import generate_output
from agents.reviewer_agent import review_output


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parents[1]
HISTORY_PATH = BASE_DIR / "workflow_history.jsonl"
AUDIT_PATH = BASE_DIR / "coordination_audit.jsonl"
HUMAN_REVIEW_PATH = BASE_DIR / "human_reviews.jsonl"
AGENT_STEP_TIMEOUT_SECONDS = float(
    os.getenv("AGENT_STEP_TIMEOUT_SECONDS", "130")
)

PROJECT_NAME = "ASD-02 Travel Agent"
PROJECT_FILES = [
    "docker-compose.yml",
    "ai-services/rag-server/app.py",
    "ai-services/mcp-server/http_server.py",
    "ai-services/multi-agent-server/app.py",
    "ai-services/multi-agent-server/coordinator.py",
    "ai-services/multi-agent-server/agents/planner_agent.py",
    "ai-services/multi-agent-server/agents/worker_agent.py",
    "ai-services/multi-agent-server/agents/reviewer_agent.py",
    "ai-services/multi-agent-server/prompts/planner_prompt.txt",
    "ai-services/multi-agent-server/prompts/worker_prompt.txt",
    "ai-services/multi-agent-server/prompts/reviewer_prompt.txt"
]


def now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def append_jsonl(
        path: Path,
        record: Dict[str, Any]
) -> None:
    with path.open(
            "a",
            encoding="utf-8"
    ) as file:
        file.write(
            json.dumps(record) + "\n"
        )


def read_jsonl(
        path: Path
) -> list[Dict[str, Any]]:
    if not path.exists():
        return []

    records = []

    with path.open(
            "r",
            encoding="utf-8"
    ) as file:
        for line in file:
            if line.strip():
                records.append(
                    json.loads(line)
                )

    return records


def project_evidence() -> Dict[str, Any]:
    files = []

    for relative_path in PROJECT_FILES:
        file_path = PROJECT_ROOT / relative_path
        files.append(
            {
                "path": relative_path,
                "exists": file_path.exists(),
                "size_bytes": file_path.stat().st_size if file_path.exists() else 0
            }
        )

    students = sorted(
        item.name
        for item in PROJECT_ROOT.glob("student-*")
        if item.is_dir()
    )

    return {
        "project_name": PROJECT_NAME,
        "project_root": str(PROJECT_ROOT),
        "students_detected": students,
        "shared_services": {
            "rag_server": {
                "port": 7005,
                "endpoint": "/query"
            },
            "mcp_server": {
                "port": 7004,
                "endpoint": "/mcp/tools"
            },
            "multi_agent_server": {
                "history_file": HISTORY_PATH.name,
                "audit_file": AUDIT_PATH.name
            }
        },
        "files": files
    }


def build_project_request(
        user_request: str,
        evidence: Dict[str, Any]
) -> str:
    present_files = [
        item["path"]
        for item in evidence["files"]
        if item["exists"]
    ]
    missing_files = [
        item["path"]
        for item in evidence["files"]
        if not item["exists"]
    ]

    return (
        f"Project: {evidence['project_name']}\n"
        f"User request: {user_request}\n\n"
        "Use this project context when planning, working, and reviewing:\n"
        f"- Students detected: {', '.join(evidence['students_detected']) or 'none'}\n"
        "- Shared RAG service: port 7005, endpoint /query\n"
        "- Shared MCP service: port 7004, endpoint /mcp/tools\n"
        f"- Present project files: {', '.join(present_files) or 'none'}\n"
        f"- Missing project files: {', '.join(missing_files) or 'none'}\n\n"
        "Keep the response grounded in the ASD-02 travel-agent project. "
        "Do not invent test results or claim release approval without human review."
    )


def build_itinerary_request(
        user_request: str,
        itinerary_context: Dict[str, Any] | None
) -> str:
    payload = {"user_request": user_request}
    if itinerary_context is not None:
        itinerary = itinerary_context["itinerary"]
        payload["itinerary"] = {
            key: itinerary[key]
            for key in (
                "itinerary_id", "destination", "start_date", "end_date", "budget",
                "travel_group", "travel_style", "requirements"
            )
            if key in itinerary
        }
        activity_fields = ("day_no", "date", "location", "time", "cost", "note")
        payload["activity_columns"] = activity_fields
        payload["activities"] = [
            [activity.get(key) for key in activity_fields]
            for activity in itinerary_context.get("activities", [])
        ]
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def run_workflow(
        user_request: str,
        itinerary_context: Dict[str, Any] | None = None,
        *,
        service: str | None = None,
        task: str | None = None,
        context: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    start_time = time.time()
    workflow_id = str(
        uuid.uuid4()
    )
    evidence = project_evidence()
    if itinerary_context is not None:
        if any(value is not None for value in (service, task, context)):
            raise ValueError("Use context or itinerary_context, not both")
        context = json.loads(build_itinerary_request(user_request, itinerary_context))
        context.pop("user_request")
        service = "itinerary"
        task = "answer_question"
    service = service or "travel"
    task = task or "answer_question"
    context = context if context is not None else {}
    project_request = json.dumps(
        {"service": service, "task": task, "user_request": user_request, "context": context},
        ensure_ascii=False,
        separators=(",", ":")
    )

    executor = ThreadPoolExecutor(max_workers=1)
    planner_future = executor.submit(
        plan_workflow,
        project_request
    )
    try:
        try:
            planner_result = planner_future.result(
                timeout=AGENT_STEP_TIMEOUT_SECONDS
            )
        except FutureTimeoutError:
            planner_future.cancel()
            planner_result = {
                "status": "timeout",
                "agent": "planner_agent",
                "plan": "Planner timed out. Continue with worker evidence and human review.",
                "human_approval_required": True
            }

        worker_future = executor.submit(
            generate_output,
            project_request
        )
        try:
            worker_result = worker_future.result(
                timeout=AGENT_STEP_TIMEOUT_SECONDS
            )
        except FutureTimeoutError:
            worker_future.cancel()
            worker_result = {
                "status": "timeout",
                "agent": "worker_agent",
                "evidence_count": 0,
                "evidence": [],
                "output": "Worker timed out before generating output.",
                "human_approval_required": True
            }
        reviewer_future = executor.submit(
            review_output,
            project_request,
            worker_result
        )
        try:
            reviewer_result = reviewer_future.result(
                timeout=AGENT_STEP_TIMEOUT_SECONDS
            )
        except FutureTimeoutError:
            reviewer_future.cancel()
            reviewer_result = {
                "status": "timeout",
                "agent": "reviewer_agent",
                "review": "Reviewer timed out. Human must decide based on available evidence.",
                "human_approval_required": True
            }
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    duration_ms = int(
        (time.time() - start_time) * 1000
    )

    workflow_result = {
        "status": "success" if all(
            result.get("status") == "success"
            for result in (planner_result, worker_result, reviewer_result)
        ) else "partial_failure",
        "workflow_id": workflow_id,
        "timestamp": now_iso(),
        "duration_ms": duration_ms,
        "user_request": user_request,
        "service": service,
        "task": task,
        "context": context,
        "itinerary_id": itinerary_context["itinerary"]["itinerary_id"] if itinerary_context else None,
        "itinerary_context": itinerary_context,
        "project_evidence": evidence,
        "participating_agents": [
            "planner_agent",
            "worker_agent",
            "reviewer_agent"
        ],
        "planner_result": planner_result,
        "worker_result": worker_result,
        "reviewer_result": reviewer_result,
        "human_decision": {
            "required": True,
            "status": "pending",
            "allowed_values": [
                "Accept",
                "Partially Accept",
                "Reject"
            ]
        }
    }

    audit_record = {
        "workflow_id": workflow_id,
        "service": service,
        "task": task,
        "timestamp": workflow_result["timestamp"],
        "duration_ms": duration_ms,
        "status": workflow_result["status"],
        "participating_agents": workflow_result["participating_agents"],
        "human_approval_required": True,
        "planner_status": planner_result.get("status"),
        "worker_status": worker_result.get("status"),
        "reviewer_status": reviewer_result.get("status"),
        "evidence_count": worker_result.get("evidence_count", 0),
        "project_files_present": sum(
            1
            for item in evidence["files"]
            if item["exists"]
        ),
        "project_files_missing": sum(
            1
            for item in evidence["files"]
            if not item["exists"]
        )
    }

    append_jsonl(
        HISTORY_PATH,
        workflow_result
    )

    append_jsonl(
        AUDIT_PATH,
        audit_record
    )

    return workflow_result


def get_workflow(workflow_id: str) -> Dict[str, Any] | None:
    workflow = next(
        (record for record in reversed(read_jsonl(HISTORY_PATH))
         if record.get("workflow_id") == workflow_id),
        None
    )
    if workflow is None:
        return None

    review = next(
        (record for record in reversed(read_jsonl(HUMAN_REVIEW_PATH))
         if record.get("workflow_id") == workflow_id),
        None
    )
    if review:
        workflow["human_decision"] = {
            **workflow.get("human_decision", {}),
            **review,
            "status": "recorded"
        }
    return workflow


def record_human_review(
        workflow_id: str,
        decision: str,
        reason: str,
        evidence: str
) -> Dict[str, Any] | None:
    workflow = get_workflow(workflow_id)
    if workflow is None:
        return None

    review = {
        "workflow_id": workflow_id,
        "service": workflow.get("service", "itinerary" if workflow.get("itinerary_id") else "travel"),
        "task": workflow.get("task", "answer_question"),
        "itinerary_id": workflow.get("itinerary_id"),
        "timestamp": now_iso(),
        "decision": decision,
        "reason": reason,
        "evidence": evidence
    }
    append_jsonl(HUMAN_REVIEW_PATH, review)
    workflow["human_decision"] = {
        **workflow.get("human_decision", {}),
        **review,
        "status": "recorded"
    }
    return workflow


def workflow_status() -> Dict[str, Any]:
    history = read_jsonl(
        HISTORY_PATH
    )

    audit = read_jsonl(
        AUDIT_PATH
    )

    return {
        "status": "success",
        "workflow_history_count": len(history),
        "audit_record_count": len(audit),
        "latest_workflow": get_workflow(history[-1]["workflow_id"]) if history else None
    }


if __name__ == "__main__":
    result = run_workflow(
        "Validate the ASD-02 travel-agent multi-agent workflow before release."
    )

    print(
        json.dumps(
            result,
            indent=2
        )
    )
