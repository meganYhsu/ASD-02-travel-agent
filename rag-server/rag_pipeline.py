import json
import os
import re
import sqlite3
import time
import uuid
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chromadb
import requests

BASE_DIR = Path(__file__).resolve().parent
APP_DIR = BASE_DIR.parent
REPORTS_DIR = APP_DIR / "reports"
CORPUS_PATH = BASE_DIR / "corpus" / "corpus.jsonl"
AUDIT_PATH = BASE_DIR / "rag-audit.jsonl"
CHROMA_PATH = BASE_DIR / "chroma"


#URL#
TRAVEL_PLAN_SERVICE_URL = os.getenv(
    "TRAVEL_PLAN_SERVICE_URL",
    "http://127.0.0.1:6004"
)

BOOKING_SERVICE_URL = os.getenv(
    # "BOOKING_SERVICE_URL", "http://localhost:5000"
    "BOOKING_SERVICE_URL", "http://127.0.0.1:5002"

)

TRAVELLER_SERVICE_URL = os.getenv(
    "TRAVELLER_SERVICE_URL",
    "http://127.0.0.1:6001"
)

BUDGET_SERVICE_URL = os.getenv(
    "BUDGET_SERVICE_URL",
    "http://127.0.0.1:6003"
)

PRETRIP_SERVICE_URL = os.getenv(
    "PRETRIP_SERVICE_URL",
    "http://127.0.0.1:5405"
)



DB_PATH_CANDIDATES = [
    APP_DIR / "database-service" / "data" / "enrolment.db",
    APP_DIR / "database-service" / "enrolment.db",
    APP_DIR / "enrolment.db",
    ]

REPORT_FILES = [
    "report.json",
    "run-report.md",
    "integration-report.md",
    "tool-review.md",
    "boundary-analysis.md",
]

COLLECTION_NAME = "student_enrolment_enterprise_context"
EMBED_VECTOR_SIZE = 256

_collection = None
_last_corpus_chunks: list[dict[str, Any]] = []


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def chroma_metadata_for_chunk(chunk: dict[str, Any]) -> dict[str, Any]:
    metadata = {
        "source_id": chunk["source_id"],
        "authority_tier": chunk["authority_tier"],
        "indexed_at": chunk["indexed_at"],
    }

    for key, value in (chunk.get("metadata") or {}).items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            metadata[key] = value
        else:
            metadata[key] = json.dumps(value, default=str)

    return metadata


def resolve_db_path() -> Path:
    for path in DB_PATH_CANDIDATES:
        if path.exists():
            return path
    return DB_PATH_CANDIDATES[0]


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    ollama_embed_url = os.getenv(
        "OLLAMA_EMBED_URL",
        "http://127.0.0.1:11434/api/embed"
    )

    model_name = os.getenv(
        "OLLAMA_EMBED_MODEL",
        "nomic-embed-text"
    )

    batch_size = int(os.getenv("OLLAMA_EMBED_BATCH_SIZE", "64"))
    all_embeddings: list[list[float]] = []

    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        response = requests.post(
            ollama_embed_url,
            json={
                "model": model_name,
                "input": batch
            },
            timeout=300
        )

        response.raise_for_status()

        data = response.json()
        embeddings = data.get("embeddings", [])

        if len(embeddings) != len(batch):
            raise RuntimeError(
                f"Expected {len(batch)} embeddings, "
                f"received {len(embeddings)}"
            )

        all_embeddings.extend(embeddings)

    return all_embeddings


def get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        _collection = client.get_or_create_collection(name=COLLECTION_NAME)
    return _collection


def reset_collection() -> None:
    global _collection
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    try:
        client.delete_collection(name=COLLECTION_NAME)
    except Exception:
        pass
    _collection = client.get_or_create_collection(name=COLLECTION_NAME)


def append_audit(
        tool_name: str,
        tool_input: dict[str, Any],
        tool_output: dict[str, Any],
        validation_status: str,
        outcome: str,
        start_time: float,
) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    duration_ms = int((time.time() - start_time) * 1000)
    record = {
        "request_id": str(uuid.uuid4()),
        "trace_id": str(uuid.uuid4()),
        "tool_name": tool_name,
        "tool_input": tool_input,
        "tool_output": tool_output,
        "timestamp": now_iso(),
        "duration_ms": duration_ms,
        "validation_status": validation_status,
        "outcome": outcome,
    }
    with AUDIT_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def chunk_text(text: str, max_words: int = 80) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks = []
    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i : i + max_words]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def load_database_chunks() -> list[dict[str, Any]]:
    db_path = resolve_db_path()
    if not db_path.exists():
        # In containers, rag-server may not have direct filesystem access to SQLite.
        # Fallback to database-service HTTP API so tier_1 facts remain available.
        try:
            response = requests.get(f"{DATABASE_SERVICE_URL}/students", timeout=10)
            response.raise_for_status()
            students = response.json()

            chunks: list[dict[str, Any]] = [
                {
                    "chunk_id": "db_service_student_count",
                    "source_id": "database-service:/students",
                    "authority_tier": "tier_1",
                    "text": f"Student count is {len(students)}.",
                    "metadata": {"source_type": "database_service", "metric": "count"},
                    "indexed_at": now_iso(),
                }
            ]

            for row in students[:500]:
                sid = row.get("student_id", "unknown")
                sname = row.get("student_name", "unknown")
                subject = row.get("subject_code", "unknown")
                chunks.append({
                    "chunk_id": f"student2-{source_name}-{index + 1}",
                    "source_id": f"student2-{source_name}",
                    "authority_tier": "tier_1",
                    "text": text,
                    "metadata": {"student": "student2","source_type": source_name},
                    "indexed_at": now_iso()
                })

            return chunks
        except Exception as exc:
            return [
                {
                    "chunk_id": "db_missing",
                    "source_id": str(db_path.relative_to(APP_DIR)) if db_path.is_absolute() else str(db_path),
                    "authority_tier": "tier_1",
                    "text": (
                        f"Database file not found: {db_path}. "
                        f"database-service fallback failed: {exc}"
                    ),
                    "metadata": {"source_type": "database", "exists": False},
                    "indexed_at": now_iso(),
                }
            ]

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    chunks: list[dict[str, Any]] = []
    try:
        tables = [
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        ]
        chunks.append(
            {
                "chunk_id": "db_schema",
                "source_id": str(db_path.relative_to(APP_DIR)),
                "authority_tier": "tier_1",
                "text": f"Database tables: {', '.join(tables)}",
                "metadata": {"source_type": "database", "tables": tables},
                "indexed_at": now_iso(),
            }
        )

        if "students" in tables:
            row = conn.execute("SELECT COUNT(*) AS count FROM students").fetchone()
            count = row["count"] if row else 0
            chunks.append(
                {
                    "chunk_id": "db_student_count",
                    "source_id": str(db_path.relative_to(APP_DIR)),
                    "authority_tier": "tier_1",
                    "text": f"Student count is {count}.",
                    "metadata": {"source_type": "database", "table": "students", "metric": "count"},
                    "indexed_at": now_iso(),
                }
            )

            for row in conn.execute(
                    "SELECT student_id, student_name, subject_code FROM students ORDER BY student_id LIMIT 500"
            ).fetchall():
                r = dict(row)
                chunks.append(
                    {
                        "chunk_id": f"db_student_{r['student_id']}",
                        "source_id": str(db_path.relative_to(APP_DIR)),
                        "authority_tier": "tier_1",
                        "text": (
                            f"Student record: student_id={r['student_id']}, "
                            f"student_name={r['student_name']}, subject_code={r['subject_code']}."
                        ),
                        "metadata": {"source_type": "database", "table": "students"},
                        "indexed_at": now_iso(),
                    }
                )
    finally:
        conn.close()

    return chunks


#############################################################################################################################################

#student 1
TRAVELLER_SERVICE_URL = os.getenv(
    "TRAVELLER_SERVICE_URL",
    "http://127.0.0.1:6001"
)

def describe_traveller(profile):
    """One readable paragraph per traveller, so a question that names the
    traveller also finds their budget, interests and needs."""
    t = profile["traveler"]
    pref = profile.get("preferences")
    interests = profile.get("interests") or []
    needs = profile.get("accessibility_needs") or []

    parts = [
        f"{t['name']} (traveler id {t['traveler_id']}) is a traveller who lives in "
        f"{t['home_location']} and prefers {t['travel_style']} travel."
    ]
    if pref:
        parts.append(
            f"Their budget is {pref['budget_min']:.0f} to {pref['budget_max']:.0f} "
            f"{pref['currency']} with a {pref['pace']} pace."
        )
    else:
        parts.append("They have not saved a budget range or pace yet.")
    if interests:
        parts.append("Their interests, highest priority first: " + "; ".join(
            f"{i['interest_category']} (priority {i['priority']})" for i in interests
        ) + ".")
    else:
        parts.append("They have not recorded any interests.")
    if needs:
        parts.append("Their accessibility and dietary needs: " + "; ".join(
            n["requirement"] + (f", dietary restriction {n['dietary_restriction']}"
                                if n.get("dietary_restriction") else "")
            for n in needs
        ) + ".")
    else:
        parts.append("They have no accessibility or dietary needs recorded.")
    return " ".join(parts)


def load_traveller_chunks():
    chunks = []

    try:
        response = requests.get(f"{TRAVELLER_SERVICE_URL}/travelers", timeout=5)
        response.raise_for_status()
        travellers = response.json()
    except Exception as exc:
        print(f"Could not load Student 1 travellers: {exc}")
        return chunks

    for traveller in travellers:
        traveler_id = traveller["traveler_id"]
        try:
            response = requests.get(
                f"{TRAVELLER_SERVICE_URL}/preference-set/{traveler_id}",
                timeout=5
            )
            response.raise_for_status()
            profile = response.json()
        except Exception as exc:
            print(f"Could not load Student 1 preference set {traveler_id}: {exc}")
            continue

        chunks.append({
            "chunk_id": f"student1-traveller-{traveler_id}",
            "source_id": "student1-preference-set",
            "authority_tier": "tier_1",
            "text": describe_traveller(profile),
            "metadata": {
                "student": "student1",
                "source_type": "preference_set"
            },
            "indexed_at": now_iso()
        })

    return chunks


#student 2  booking and itinerary chunks function
def load_booking_chunks():
    chunks = []

    endpoints = {
        "itineraries": "/itineraries",
        "providers": "/provider",
        "bookings": "/bookings",
        "booking_items": "/booking_items",
    }

    for source_name, endpoint in endpoints.items():
        try:
            response = requests.get(
                f"{BOOKING_SERVICE_URL}{endpoint}",
                timeout=5
            )
            response.raise_for_status()
            records = response.json()

            for index, record in enumerate(records):
                text = (
                        f"{source_name}: "
                        + ", ".join(
                    f"{key}={value}"
                    for key, value in record.items()
                )
                )

                chunks.append({
                    "chunk_id": f"student2-{source_name}-{index + 1}",
                    "source_id": f"student2-{source_name}",
                    "authority_tier": "tier_1",
                    "text": text,
                    "metadata": {"student": "student2","source_type": source_name},
                    "indexed_at": now_iso()
                })

        except Exception as exc:
            print(
                f"Could not load {source_name}: {exc}"
            )

    return chunks


#student 3
BUDGET_SERVICE_URL = os.getenv(
    "BUDGET_SERVICE_URL",
    "http://127.0.0.1:6003"
)

def load_budget_chunks():
    chunks = []

    endpoints = {
        "expenses": "/expenses",
        "categories": "/categories",
        "recommendations": "/recommendations",
    }

    for source_name, endpoint in endpoints.items():
        try:
            response = requests.get(
                f"{BUDGET_SERVICE_URL}{endpoint}",
                timeout=5
            )
            response.raise_for_status()
            records = response.json()

            for index, record in enumerate(records):
                text = (
                        f"{source_name}: "
                        + ", ".join(
                    f"{key}={value}"
                    for key, value in record.items()
                )
                )

                chunks.append({
                    "chunk_id": f"student3-{source_name}-{index + 1}",
                    "source_id": f"student3-{source_name}",
                    "authority_tier": "tier_1",
                    "text": text,
                    "metadata": {
                        "student": "student3",
                        "source_type": source_name
                    },
                    "indexed_at": now_iso()
                })

        except Exception as exc:
            print(f"Could not load Student 3 {source_name}: {exc}")

    return chunks


#student 4#
def safe_chunk_value(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    return str(value)


def build_itinerary_summary_chunk(itinerary: dict[str, Any]) -> dict[str, Any]:
    itinerary_id = itinerary.get("itinerary_id")
    destination = itinerary.get("destination")

    text = (
        f"Itinerary {itinerary_id} summary and requirements for {safe_chunk_value(destination)}. "
        f"This chunk answers overview questions about itinerary {itinerary_id}, destination, dates, budget, "
        f"travel group, travel style, and requirements. "
        f"itinerary_summary: itinerary_id={itinerary_id}, "
        f"destination={safe_chunk_value(destination)}, "
        f"start_date={safe_chunk_value(itinerary.get('start_date'))}, "
        f"end_date={safe_chunk_value(itinerary.get('end_date'))}, "
        f"budget={safe_chunk_value(itinerary.get('budget'))}, "
        f"travel_group={safe_chunk_value(itinerary.get('travel_group'))}, "
        f"travel_style={safe_chunk_value(itinerary.get('travel_style'))}, "
        f"requirements={safe_chunk_value(itinerary.get('requirements'))}, "
        f"created_at={safe_chunk_value(itinerary.get('created_at'))}"
    )

    return {
        "chunk_id": f"student4-itinerary-summary-{itinerary_id}",
        "source_id": "student4-itinerary-summary",
        "authority_tier": "tier_1",
        "text": text,
        "metadata": {
            "student": "student4",
            "source_type": "itinerary_summary",
            "itinerary_id": itinerary_id,
            "destination": destination,
        },
        "indexed_at": now_iso(),
    }


def build_activity_detail_chunk(activity: dict[str, Any]) -> dict[str, Any]:
    activity_id = activity.get("activity_id")
    itinerary_id = activity.get("itinerary_id")

    text = (
        f"Single activity detail for itinerary {itinerary_id}. "
        f"This chunk answers questions about activity {activity_id}, which happens on day "
        f"{safe_chunk_value(activity.get('day_no'))} of itinerary {itinerary_id}. "
        f"activity_detail: activity_id={activity_id}, "
        f"itinerary_id={itinerary_id}, "
        f"day_no={safe_chunk_value(activity.get('day_no'))}, "
        f"date={safe_chunk_value(activity.get('date'))}, "
        f"location={safe_chunk_value(activity.get('location'))}, "
        f"time={safe_chunk_value(activity.get('time'))}, "
        f"cost={safe_chunk_value(activity.get('cost'))}, "
        f"description={safe_chunk_value(activity.get('note'))}"
    )

    return {
        "chunk_id": f"student4-activity-{activity_id}",
        "source_id": "student4-activity-detail",
        "authority_tier": "tier_1",
        "text": text,
        "metadata": {
            "student": "student4",
            "source_type": "activity_detail",
            "itinerary_id": itinerary_id,
            "activity_id": activity_id,
        },
        "indexed_at": now_iso(),
    }


def build_itinerary_activity_index_chunk(
        itinerary: dict[str, Any],
        activities: list[dict[str, Any]]
) -> dict[str, Any]:
    itinerary_id = itinerary.get("itinerary_id")
    destination = itinerary.get("destination")
    activity_lines = "; ".join(
        f"activity_id={activity.get('activity_id')}, "
        f"day_no={safe_chunk_value(activity.get('day_no'))}, "
        f"time={safe_chunk_value(activity.get('time'))}, "
        f"location={safe_chunk_value(activity.get('location'))}, "
        f"description={safe_chunk_value(activity.get('note'))}"
        for activity in activities
    )

    text = (
        f"All activities for itinerary {itinerary_id}. "
        f"This chunk lists every activity ID in itinerary {itinerary_id}, including each activity's day, "
        f"time, location, and description. "
        f"itinerary_activity_index: itinerary_id={itinerary_id}, "
        f"destination={safe_chunk_value(destination)}, "
        f"activities=[{activity_lines}]"
    )

    return {
        "chunk_id": f"student4-itinerary-activities-{itinerary_id}",
        "source_id": "student4-itinerary-activity-index",
        "authority_tier": "tier_1",
        "text": text,
        "metadata": {
            "student": "student4",
            "source_type": "itinerary_activity_index",
            "itinerary_id": itinerary_id,
            "destination": destination,
        },
        "indexed_at": now_iso(),
    }


def build_day_schedule_chunks(
        itinerary: dict[str, Any],
        activities: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    itinerary_id = itinerary.get("itinerary_id")
    activities_by_day: dict[Any, list[dict[str, Any]]] = {}

    for activity in activities:
        if not isinstance(activity, dict):
            continue
        day_no = activity.get("day_no")
        activities_by_day.setdefault(day_no, []).append(activity)

    chunks = []

    for day_no, day_activities in activities_by_day.items():
        sorted_activities = sorted(
            day_activities,
            key=lambda item: str(item.get("time") or "")
        )

        date = (
            safe_chunk_value(sorted_activities[0].get("date"))
            if sorted_activities else ""
        )
        locations = sorted({
            safe_chunk_value(activity.get("location"))
            for activity in sorted_activities
            if activity.get("location")
        })

        activity_lines = "; ".join(
            f"activity_id={activity.get('activity_id')}, "
            f"time={safe_chunk_value(activity.get('time'))}, "
            f"location={safe_chunk_value(activity.get('location'))}, "
            f"description={safe_chunk_value(activity.get('note'))}"
            for activity in sorted_activities
        )

        text = (
            f"Day {day_no} activities for itinerary {itinerary_id}. "
            f"This chunk answers questions about what the user is doing on day {day_no} "
            f"of itinerary {itinerary_id}. "
            f"day_schedule: itinerary_id={itinerary_id}, "
            f"day_no={day_no}, "
            f"date={date}, "
            f"locations={', '.join(locations)}, "
            f"activities=[{activity_lines}]"
        )

        chunks.append({
            "chunk_id": f"student4-itinerary-{itinerary_id}-day-{day_no}",
            "source_id": "student4-day-schedule",
            "authority_tier": "tier_1",
            "text": text,
            "metadata": {
                "student": "student4",
                "source_type": "day_schedule",
                "itinerary_id": itinerary_id,
                "day_no": day_no,
            },
            "indexed_at": now_iso(),
        })

    return chunks


def load_travel_plan_chunks():
    chunks = []

    try:
        response = requests.get(
            f"{TRAVEL_PLAN_SERVICE_URL}/api/itineraries",
            timeout=5
        )
        response.raise_for_status()

        plans = response.json()
        if isinstance(plans, dict):
            plans = plans.get("itineraries", [])
        if not isinstance(plans, list):
            plans = []

        for index, plan in enumerate(plans):
            if not isinstance(plan, dict):
                continue

            if "itinerary" in plan:
                itinerary = plan.get("itinerary") or {}
                activities = plan.get("activities") or []
            else:
                itinerary = plan
                activities = []

            itinerary_id = itinerary.get(
                "itinerary_id",
                index + 1
            )

            if not activities and itinerary_id:
                try:
                    detail_response = requests.get(
                        f"{TRAVEL_PLAN_SERVICE_URL}/api/itineraries/{itinerary_id}",
                        timeout=5
                    )
                    detail_response.raise_for_status()
                    detail = detail_response.json()
                    if isinstance(detail, dict):
                        itinerary = detail.get("itinerary") or itinerary
                        activities = detail.get("activities") or []
                except Exception as exc:
                    print(
                        f"Could not load Student 4 itinerary "
                        f"{itinerary_id} activities: {exc}"
                    )

            chunks.append(build_itinerary_summary_chunk(itinerary))

            valid_activities = [
                activity for activity in activities
                if isinstance(activity, dict)
            ]
            if valid_activities:
                chunks.append(
                    build_itinerary_activity_index_chunk(
                        itinerary,
                        valid_activities
                    )
                )

            for activity in valid_activities:
                chunks.append(build_activity_detail_chunk(activity))

            chunks.extend(
                build_day_schedule_chunks(
                    itinerary,
                    valid_activities
                )
            )

    except Exception as exc:
        print(
            f"Could not load Student 4 travel plans: {exc}"
        )

    return chunks


#student 5#
PRETRIP_SERVICE_URL = os.getenv(
    "PRETRIP_SERVICE_URL",
    "http://127.0.0.1:5405"
)

def load_pretrip_chunks() -> list[dict[str, Any]]:
    chunks = []

    endpoints = {
        "documents": "/documents",
        "entry_requirements": "/entry-requirements",
        "packing_lists": "/packing-lists",
        "checklist_items": "/checklist-items",
        "pre_trip_tasks": "/pre-trip-tasks",
    }

    for source_name, endpoint in endpoints.items():
        try:
            response = requests.get(
                f"{PRETRIP_SERVICE_URL}{endpoint}",
                timeout=5
            )
            response.raise_for_status()

            payload = response.json()

            # Student 5 API returns:
            # {"data": [...], "success": true}
            if isinstance(payload, dict):
                records = payload.get("data", [])
            elif isinstance(payload, list):
                records = payload
            else:
                records = []

            for index, record in enumerate(records):
                if not isinstance(record, dict):
                    continue

                record_id = record.get("id", index + 1)

                text = (
                        f"{source_name}: "
                        + ", ".join(
                    f"{key}={value}"
                    for key, value in record.items()
                )
                )

                chunks.append({
                    "chunk_id": f"student5-{source_name}-{record_id}",
                    "source_id": f"student5-{source_name}",
                    "authority_tier": "tier_1",
                    "text": text,
                    "metadata": {
                        "student": "student5",
                        "source_type": source_name,
                    },
                    "indexed_at": now_iso(),
                })

        except Exception as exc:
            print(
                f"Could not load Student 5 "
                f"{source_name}: {exc}"
            )

    return chunks


#############################################################################################################################################



def load_report_chunks() -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for name in REPORT_FILES:
        path = REPORTS_DIR / name
        if not path.exists():
            continue

        text = ""
        try:
            if path.suffix == ".json":
                text = json.dumps(json.loads(path.read_text(encoding="utf-8")), indent=2)
            else:
                text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            text = path.read_text(encoding="utf-8", errors="ignore")

        for i, chunk in enumerate(chunk_text(text), start=1):
            chunks.append(
                {
                    "chunk_id": f"{path.stem}_{i}",
                    "source_id": f"reports/{name}",
                    "authority_tier": "tier_2",
                    "text": chunk,
                    "metadata": {"source_type": "report", "file": name},
                    "indexed_at": now_iso(),
                }
            )

    return chunks


def load_repository_chunks() -> list[dict[str, Any]]:
    ignored = {".git", ".venv", "__pycache__", "node_modules", "chroma"}
    files: list[str] = []

    for root, dirs, filenames in os.walk(APP_DIR, topdown=True, followlinks=False, onerror=lambda e: None):
        # Prune ignored and symlinked directories to avoid scanning protected mounts.
        pruned_dirs: list[str] = []
        for directory_name in dirs:
            if directory_name in ignored:
                continue
            directory_path = Path(root) / directory_name
            try:
                if directory_path.is_symlink():
                    continue
            except OSError:
                continue
            pruned_dirs.append(directory_name)
        dirs[:] = pruned_dirs

        for filename in filenames:
            file_path = Path(root) / filename
            try:
                if file_path.is_symlink():
                    continue
                rel = file_path.relative_to(APP_DIR)
                files.append(str(rel).replace("\\", "/"))
            except (OSError, ValueError):
                continue

    text = "Repository files include: " + ", ".join(sorted(files[:400]))
    return [
        {
            "chunk_id": "repo_index",
            "source_id": "repository",
            "authority_tier": "tier_3",
            "text": text,
            "metadata": {"source_type": "repository", "file_count": len(files)},
            "indexed_at": now_iso(),
        }
    ]


def build_corpus():
    chunks = []
    chunks.extend(load_traveller_chunks())   # Student 1
    chunks.extend(load_booking_chunks())     # Student 2
    chunks.extend(load_budget_chunks())      # Student 3
    chunks.extend(load_travel_plan_chunks()) # Student 4
    chunks.extend(load_pretrip_chunks())     # Student 5

    return chunks


def write_corpus(chunks: list[dict[str, Any]]) -> None:
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CORPUS_PATH.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk) + "\n")


def read_corpus() -> list[dict[str, Any]]:
    if not CORPUS_PATH.exists():
        return []

    chunks: list[dict[str, Any]] = []
    with CORPUS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                chunks.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return chunks


def lexical_fallback_retrieve(query: str, k: int) -> list[dict[str, Any]]:
    corpus = _last_corpus_chunks or read_corpus()
    query_tokens = set((query or "").lower().split())
    tier_weight = {"tier_1": 3, "tier_2": 2, "tier_3": 1}

    scored = []
    for chunk in corpus:
        text = chunk.get("text", "")
        text_tokens = set(text.lower().split())
        overlap = len(query_tokens.intersection(text_tokens))
        scored.append(
            {
                "rank": 0,
                "chunk_id": chunk.get("chunk_id"),
                "source_id": chunk.get("source_id"),
                "authority_tier": chunk.get("authority_tier"),
                "distance": None,
                "text": text,
                "_score": overlap,
            }
        )

    scored.sort(
        key=lambda r: (
            tier_weight.get(r.get("authority_tier"), 0),
            r.get("_score", 0),
        ),
        reverse=True,
    )

    top = scored[: max(k, 1)]
    for i, row in enumerate(top, start=1):
        row["rank"] = i
        row.pop("_score", None)
    return top


def extract_itinerary_id(query: str) -> int | None:
    patterns = [
        r"itinerary[_\s-]*id\s*[=:]?\s*(\d+)",
        r"itinerary\s+(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, query or "", re.IGNORECASE)
        if match:
            return int(match.group(1))

    return None


def refresh_corpus(caller: str = "student") -> dict[str, Any]:
    global _last_corpus_chunks
    start = time.time()
    try:
        chunks = build_corpus()
        _last_corpus_chunks = chunks
        write_corpus(chunks)
        vector_store_status = "ready"
        vector_store_error = None

        try:
            reset_collection()
            collection = get_collection()

            if chunks:
                ids = [c["chunk_id"] for c in chunks]
                docs = [c["text"] for c in chunks]
                metas = [chroma_metadata_for_chunk(c) for c in chunks]
                embeddings = embed_texts(docs)
                collection.add(ids=ids, documents=docs, metadatas=metas, embeddings=embeddings)
        except Exception as exc:
            vector_store_status = "degraded"
            vector_store_error = str(exc)

        output = {
            "status": "success",
            "caller": caller,
            "chunk_count": len(chunks),
            "collection": COLLECTION_NAME,
            "corpus_path": str(CORPUS_PATH),
            "vector_store_status": vector_store_status,
        }
        if vector_store_error:
            output["vector_store_error"] = vector_store_error
        append_audit("refresh_corpus", {"caller": caller}, output, "pass", "corpus_refreshed", start)
        return output
    except Exception as exc:
        output = {"status": "error", "error": str(exc)}
        append_audit("refresh_corpus", {"caller": caller}, output, "fail", "error", start)
        return output


def retrieve_context(query: str, k: int = 5, caller: str = "student") -> dict[str, Any]:
    start = time.time()
    try:
        retrieval_mode = "vector"
        ranked = []

        try:
            collection = get_collection()
            if collection.count() == 0:
                refreshed = refresh_corpus(caller="auto_refresh")
                if refreshed.get("status") != "success":
                    raise RuntimeError("empty_collection")

            query_embedding = embed_texts([query])
            # Filtering disabled for testing: allow RAG retrieval to search
            # the full collection even when the query mentions an itinerary ID.
            # itinerary_id = extract_itinerary_id(query)
            query_args = {
                "query_embeddings": query_embedding,
                "n_results": k,
            }
            # if itinerary_id is not None:
            #     query_args["where"] = {"itinerary_id": itinerary_id}

            results = collection.query(**query_args)

            ids = (results.get("ids") or [[]])[0]
            docs = (results.get("documents") or [[]])[0]
            metas = (results.get("metadatas") or [[]])[0]
            distances = (results.get("distances") or [[]])[0]

            for i, chunk_id in enumerate(ids):
                row_meta = metas[i] if i < len(metas) and isinstance(metas[i], dict) else {}
                ranked.append(
                    {
                        "rank": i + 1,
                        "chunk_id": chunk_id,
                        "source_id": row_meta.get("source_id"),
                        "authority_tier": row_meta.get("authority_tier"),
                        "distance": distances[i] if i < len(distances) else None,
                        "text": docs[i] if i < len(docs) else "",
                    }
                )

            tier_weight = {"tier_1": 3, "tier_2": 2, "tier_3": 1}
            ranked.sort(
                key=lambda x: (
                    tier_weight.get(x.get("authority_tier"), 0),
                    -(x.get("distance") if isinstance(x.get("distance"), (int, float)) else 1e9),
                ),
                reverse=True,
            )
        except Exception as exc:
            print(f"Vector retrieval failed: {exc}")
            retrieval_mode = "lexical_fallback"
            if not _last_corpus_chunks and not CORPUS_PATH.exists():
                refreshed = refresh_corpus(caller="auto_refresh")
                if refreshed.get("status") != "success":
                    return {"status": "error", "error": "corpus_unavailable"}
            ranked = lexical_fallback_retrieve(query, k)

        output = {
            "status": "success",
            "query": query,
            "caller": caller,
            "k": k,
            "retrieval_mode": retrieval_mode,
            "results": ranked,
        }

        append_audit(
            "retrieve_context",
            {"query": query, "k": k, "caller": caller},
            {"result_count": len(ranked), "chunk_ids": [r["chunk_id"] for r in ranked]},
            "pass",
            "context_retrieved",
            start,
        )
        return output
    except Exception as exc:
        output = {"status": "error", "error": str(exc), "query": query}
        append_audit(
            "retrieve_context",
            {"query": query, "k": k, "caller": caller},
            output,
            "fail",
            "error",
            start,
        )
        return output


def confidence_from_results(results: list[dict[str, Any]]) -> str:
    if not results:
        return "Unknown"
    tier_1 = sum(1 for r in results if r.get("authority_tier") == "tier_1")
    tier_2 = sum(1 for r in results if r.get("authority_tier") == "tier_2")
    if tier_1 >= 2 and len(results) >= 3:
        return "High"
    if tier_1 >= 1 or tier_2 >= 2:
        return "Medium"
    return "Low"





def generate_with_ollama(query: str, context: str) -> dict[str, Any]:
    model_name = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    ollama_generate_url = os.getenv(
        "OLLAMA_GENERATE_URL",
        "http://127.0.0.1:11434/api/generate"
    )

    prompt = f"""
    
    You are a grounded travel assistant.
    Answer the question using ONLY the retrieved context.
    
    Rules:
    1. Do not use outside knowledge.
    2. If the context does not contain enough evidence, answer "Insufficient evidence."
    3. Only include chunk IDs that directly support the answer.
    4. Do not include retrieved chunks that were not actually used.
    5. Return ONLY valid JSON. Do not use Markdown.
    
    Return:{{
        "answer": "your grounded answer",
        "used_chunk_ids": ["chunk-id-1", "chunk-id-2"]
    }}
    
    If evidence is insufficient:{{
        "answer": "Insufficient evidence.",
        "used_chunk_ids": []
    }}
    
    QUESTION:
    {query}
    
    CONTEXT:
    {context}
"""

    try:
        resp = requests.post(
            ollama_generate_url,
            json={
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "keep_alive": "30m"
            },
            timeout=300,
        )

        resp.raise_for_status()

        raw_response = resp.json().get("response", "").strip()

        # Some models may wrap JSON in markdown fences.
        if raw_response.startswith("```"):
            raw_response = raw_response.replace("```json", "")
            raw_response = raw_response.replace("```", "")
            raw_response = raw_response.strip()

        try:
            parsed = json.loads(raw_response)

            return {
                "answer": parsed.get(
                    "answer",
                    "Insufficient evidence."
                ),
                "used_chunk_ids": parsed.get(
                    "used_chunk_ids",
                    []
                )
            }

        except json.JSONDecodeError:
            return {
                "answer": raw_response or "Insufficient evidence.",
                "used_chunk_ids": []
            }

    except Exception as exc:
        return {
            "answer": "",
            "used_chunk_ids": [],
            "error": f"Ollama unavailable: {exc}"
        }


def answer_question(
        query: str,
        k: int = 5,
        caller: str = "student"
) -> dict[str, Any]:

    start = time.time()

    retrieval = retrieve_context(
        query=query,
        k=k,
        caller=caller
    )

    if retrieval.get("status") != "success":
        output = {
            "status": "error",
            "query": query,
            "error": retrieval.get(
                "error",
                "retrieval_failed"
            )
        }

        append_audit(
            "answer_question",
            {"query": query, "k": k, "caller": caller},
            output,
            "fail",
            "retrieval_failed",
            start,
        )

        return output

    results = retrieval.get("results", [])

    # Give Ollama both the chunk ID and the chunk text.
    context = "\n\n".join(
        f"[chunk_id: {r.get('chunk_id')}]\n"
        f"{r.get('text', '')}"
        for r in results
    )

    generation = generate_with_ollama(
        query,
        context
    )

    # Ollama failed.
    if generation.get("error"):
        output = {
            "status": "error",
            "query": query,
            "error": generation["error"],
            "citations": [],
            "confidence_category": "Unknown",
            "retrieval_summary": {
                "k": k,
                "retrieved_count": len(results),
                "top_chunk": (
                    results[0].get("chunk_id")
                    if results else None
                )
            }
        }

        append_audit(
            "answer_question",
            {"query": query, "k": k, "caller": caller},
            output,
            "fail",
            "generation_failed",
            start,
        )

        return output

    answer = generation.get(
        "answer",
        "Insufficient evidence."
    )

    used_chunk_ids = generation.get(
        "used_chunk_ids",
        []
    )

    # Security/consistency:
    # only accept IDs that actually came from retrieval.
    used_results = [
        r for r in results
        if r.get("chunk_id") in used_chunk_ids
    ]

    citations = [
        {
            "chunk_id": r.get("chunk_id"),
            "source_id": r.get("source_id"),
            "authority_tier": r.get(
                "authority_tier"
            ),
        }
        for r in used_results
    ]

    if answer.strip().lower() == "insufficient evidence.":
        confidence = "Unknown"
    else:
        confidence = (
            confidence_from_results(used_results)
            if used_results
            else "Unknown"
        )

    output = {
        "status": "success",
        "query": query,
        "answer": answer,
        "citations": citations,
        "confidence_category": confidence,
        "retrieval_summary": {
            "k": k,
            "retrieved_count": len(results),
            "top_chunk": (
                results[0].get("chunk_id")
                if results else None
            ),
        },
    }

    append_audit(
        "answer_question",
        {"query": query, "k": k, "caller": caller},
        {
            "confidence_category": confidence,
            "citation_count": len(citations)
        },
        "pass",
        "answer_generated",
        start,
    )

    return output


if __name__ == "__main__":
    result = refresh_corpus()
    print(json.dumps(result, indent=2))
