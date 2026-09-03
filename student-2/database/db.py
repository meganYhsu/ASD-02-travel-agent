"""Parameterised SQLite data-access helpers for the traveler-preferences service."""

from __future__ import annotations

import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = BASE_DIR / "schema.sql"
SEED_PATH = BASE_DIR / "seed.sql"

TRAVELER_FIELDS = (
    "full_name",
    "username",
    "email",
    "home_location",
    "travel_style",
)
PREFERENCE_FIELDS = (
    "traveler_id",
    "budget_min",
    "budget_max",
    "currency",
    "pace",
    "preferred_trip_length_days",
)
INTEREST_FIELDS = (
    "traveler_id",
    "interest_category",
    "priority",
)
ACCESSIBILITY_FIELDS = (
    "traveler_id",
    "requirement",
    "dietary_restriction",
    "notes",
)

ALLOWED_TABLES = {"Travelers", "Preferences", "Interests", "AccessibilityNeeds"}

ALLOWED_FILTER_COLUMNS = {
    "Travelers": {"email", "username", "travel_style", "home_location"},
    "Preferences": {"traveler_id", "pace", "currency"},
    "Interests": {"traveler_id", "interest_category", "priority"},
    "AccessibilityNeeds": {"traveler_id", "requirement", "dietary_restriction"},
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_db_path() -> str:
    return os.environ.get("DATABASE_PATH", str(BASE_DIR / "data" / "traveler_preferences.db"))


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or default_db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


def init_db(db_path: str | None = None, seed: bool = True) -> None:
    path = db_path or default_db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn = get_connection(path)
    try:
        conn.executescript(schema_sql)
        if seed:
            count = conn.execute("SELECT COUNT(*) AS c FROM Travelers").fetchone()["c"]
            if count == 0:
                conn.executescript(SEED_PATH.read_text(encoding="utf-8"))
                logger.info("Seeded demonstration data into %s", path)
        conn.commit()
    finally:
        conn.close()


class IntegrityConflict(Exception):
    pass


class ForeignKeyError(Exception):
    pass


def _execute_write(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...]) -> sqlite3.Cursor:
    try:
        return conn.execute(sql, params)
    except sqlite3.IntegrityError as exc:
        message = str(exc).lower()
        if "foreign key" in message:
            raise ForeignKeyError(str(exc)) from exc
        raise IntegrityConflict(str(exc)) from exc


def _guard_table(table: str) -> None:
    if table not in ALLOWED_TABLES:
        raise ValueError("Unknown table")


def fetch_all(
    table: str,
    filters: dict[str, Any] | None = None,
    db_path: str | None = None,
) -> list[dict[str, Any]]:
    _guard_table(table)
    allowed_columns = ALLOWED_FILTER_COLUMNS[table]
    clauses: list[str] = []
    params: list[Any] = []
    for key, value in (filters or {}).items():
        if value is None or value == "":
            continue
        if key not in allowed_columns:
            continue
        clauses.append(f"{key} = ?")
        params.append(value)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"SELECT * FROM {table} {where} ORDER BY id ASC"
    conn = get_connection(db_path)
    try:
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [row_to_dict(r) for r in rows]  # type: ignore[misc]
    finally:
        conn.close()


def fetch_one(table: str, record_id: int, db_path: str | None = None) -> dict[str, Any] | None:
    _guard_table(table)
    conn = get_connection(db_path)
    try:
        row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (record_id,)).fetchone()
        return row_to_dict(row)
    finally:
        conn.close()


def insert_row(
    table: str,
    fields: tuple[str, ...],
    payload: dict[str, Any],
    db_path: str | None = None,
) -> dict[str, Any]:
    _guard_table(table)
    now = utc_now()
    columns = list(fields) + ["created_at", "updated_at"]
    values = [payload.get(field) for field in fields] + [now, now]
    placeholders = ", ".join(["?"] * len(columns))
    column_sql = ", ".join(columns)
    sql = f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders})"
    conn = get_connection(db_path)
    try:
        cursor = _execute_write(conn, sql, tuple(values))
        conn.commit()
        record_id = cursor.lastrowid
    finally:
        conn.close()
    created = fetch_one(table, int(record_id), db_path)  # type: ignore[arg-type]
    assert created is not None
    return created


def update_row(
    table: str,
    record_id: int,
    fields: tuple[str, ...],
    payload: dict[str, Any],
    db_path: str | None = None,
) -> dict[str, Any] | None:
    _guard_table(table)
    existing = fetch_one(table, record_id, db_path)
    if existing is None:
        return None
    assignments = []
    values: list[Any] = []
    for field in fields:
        if field in payload:
            assignments.append(f"{field} = ?")
            values.append(payload[field])
    if not assignments:
        return existing
    assignments.append("updated_at = ?")
    values.append(utc_now())
    values.append(record_id)
    sql = f"UPDATE {table} SET {', '.join(assignments)} WHERE id = ?"
    conn = get_connection(db_path)
    try:
        _execute_write(conn, sql, tuple(values))
        conn.commit()
    finally:
        conn.close()
    return fetch_one(table, record_id, db_path)


def delete_row(table: str, record_id: int, db_path: str | None = None) -> bool:
    _guard_table(table)
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(f"DELETE FROM {table} WHERE id = ?", (record_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def fetch_profile(traveler_id: int, db_path: str | None = None) -> dict[str, Any] | None:
    """Aggregate a traveller and every related preference record in one call."""
    traveler = fetch_one("Travelers", traveler_id, db_path)
    if traveler is None:
        return None
    preferences = fetch_all("Preferences", {"traveler_id": traveler_id}, db_path)
    return {
        "traveler": traveler,
        "preferences": preferences[0] if preferences else None,
        "interests": fetch_all("Interests", {"traveler_id": traveler_id}, db_path),
        "accessibility_needs": fetch_all("AccessibilityNeeds", {"traveler_id": traveler_id}, db_path),
    }
