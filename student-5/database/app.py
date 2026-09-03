"""Database microservice for travel documents, packing lists and pre-trip tasks."""

from __future__ import annotations

import logging
import os
from typing import Any

from flask import Flask, jsonify, request

import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

TABLES = {
    "documents": ("Documents", db.DOCUMENT_FIELDS),
    "entry-requirements": ("EntryRequirements", db.ENTRY_FIELDS),
    "packing-lists": ("PackingLists", db.PACKING_FIELDS),
    "checklist-items": ("ChecklistItems", db.CHECKLIST_FIELDS),
    "pre-trip-tasks": ("PreTripTasks", db.TASK_FIELDS),
}

FILTERS = {
    "documents": ("traveller_id", "status", "document_type", "nationality"),
    "entry-requirements": (
        "destination_country",
        "traveller_nationality",
        "document_type",
        "is_required",
    ),
    "packing-lists": ("trip_id", "traveller_id", "destination"),
    "checklist-items": ("packing_list_id", "category", "is_completed"),
    "pre-trip-tasks": ("trip_id", "traveller_id", "priority", "is_completed"),
}


def json_ok(data: Any, status: int = 200):
    return jsonify({"success": True, "data": data}), status


def json_error(message: str, status: int):
    return jsonify({"success": False, "error": message}), status


def create_app(db_path: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or db.default_db_path()
    db.init_db(app.config["DB_PATH"], seed=True)

    def path() -> str:
        return app.config["DB_PATH"]

    @app.get("/health")
    def health():
        return json_ok({"status": "ok", "service": "student5-database"})

    @app.get("/<resource>")
    def list_resource(resource: str):
        if resource not in TABLES:
            return json_error("Not found", 404)
        table, _ = TABLES[resource]
        allowed = FILTERS[resource]
        filters: dict[str, Any] = {}
        for key in allowed:
            if key in request.args:
                value: Any = request.args.get(key)
                if key in {"is_required", "is_completed"}:
                    value = 1 if str(value).lower() in {"1", "true"} else 0
                filters[key] = value
        alias_destination = request.args.get("destination")
        if resource == "entry-requirements" and alias_destination:
            filters["destination_country"] = alias_destination
        alias_nationality = request.args.get("nationality")
        if resource == "entry-requirements" and alias_nationality:
            filters["traveller_nationality"] = alias_nationality
        return json_ok(db.fetch_all(table, filters, path()))

    @app.get("/<resource>/<int:record_id>")
    def get_resource(resource: str, record_id: int):
        if resource not in TABLES:
            return json_error("Not found", 404)
        table, _ = TABLES[resource]
        row = db.fetch_one(table, record_id, path())
        if row is None:
            return json_error("Record not found", 404)
        return json_ok(row)

    @app.post("/<resource>")
    def create_resource(resource: str):
        if resource not in TABLES:
            return json_error("Not found", 404)
        payload = request.get_json(silent=True)
        if payload is None:
            return json_error("Malformed JSON", 400)
        table, fields = TABLES[resource]
        try:
            created = db.insert_row(table, fields, payload, path())
        except db.IntegrityConflict as exc:
            logger.warning("Integrity conflict creating %s", resource)
            return json_error(f"Conflict: {exc}", 409)
        except db.ForeignKeyError:
            return json_error("Related record does not exist", 400)
        return json_ok(created, 201)

    @app.put("/<resource>/<int:record_id>")
    def update_resource(resource: str, record_id: int):
        if resource not in TABLES:
            return json_error("Not found", 404)
        payload = request.get_json(silent=True)
        if payload is None:
            return json_error("Malformed JSON", 400)
        table, fields = TABLES[resource]
        try:
            updated = db.update_row(table, record_id, fields, payload, path())
        except db.IntegrityConflict as exc:
            return json_error(f"Conflict: {exc}", 409)
        except db.ForeignKeyError:
            return json_error("Related record does not exist", 400)
        if updated is None:
            return json_error("Record not found", 404)
        return json_ok(updated)

    @app.delete("/<resource>/<int:record_id>")
    def delete_resource(resource: str, record_id: int):
        if resource not in TABLES:
            return json_error("Not found", 404)
        table, _ = TABLES[resource]
        deleted = db.delete_row(table, record_id, path())
        if not deleted:
            return json_error("Record not found", 404)
        return "", 204

    @app.patch("/checklist-items/<int:record_id>/complete")
    def complete_item(record_id: int):
        payload = request.get_json(silent=True) or {}
        is_completed = bool(payload.get("is_completed", True))
        updated = db.set_completion("ChecklistItems", record_id, is_completed, path())
        if updated is None:
            return json_error("Record not found", 404)
        return json_ok(updated)

    @app.patch("/pre-trip-tasks/<int:record_id>/complete")
    def complete_task(record_id: int):
        payload = request.get_json(silent=True) or {}
        is_completed = bool(payload.get("is_completed", True))
        updated = db.set_completion("PreTripTasks", record_id, is_completed, path())
        if updated is None:
            return json_error("Record not found", 404)
        return json_ok(updated)

    @app.get("/packing-lists/<int:record_id>/progress")
    def packing_progress(record_id: int):
        items = db.fetch_all("ChecklistItems", {"packing_list_id": record_id}, path())
        total = len(items)
        completed = sum(1 for item in items if item.get("is_completed"))
        return json_ok({"completed": completed, "total": total})

    @app.get("/pre-trip-tasks/progress")
    def task_progress():
        filters: dict[str, Any] = {}
        if request.args.get("trip_id"):
            filters["trip_id"] = request.args.get("trip_id")
        if request.args.get("traveller_id"):
            filters["traveller_id"] = request.args.get("traveller_id")
        items = db.fetch_all("PreTripTasks", filters, path())
        total = len(items)
        completed = sum(1 for item in items if item.get("is_completed"))
        return json_ok({"completed": completed, "total": total})

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5405"))
    app.run(host="0.0.0.0", port=port)
