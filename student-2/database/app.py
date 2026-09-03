"""Database microservice for travellers, preferences, interests and accessibility needs."""

from __future__ import annotations

import logging
import os
from typing import Any

from flask import Flask, jsonify, request

import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

TABLES = {
    "travelers": ("Travelers", db.TRAVELER_FIELDS),
    "preferences": ("Preferences", db.PREFERENCE_FIELDS),
    "interests": ("Interests", db.INTEREST_FIELDS),
    "accessibility-needs": ("AccessibilityNeeds", db.ACCESSIBILITY_FIELDS),
}

FILTERS = {
    "travelers": ("email", "username", "travel_style", "home_location"),
    "preferences": ("traveler_id", "pace", "currency"),
    "interests": ("traveler_id", "interest_category", "priority"),
    "accessibility-needs": ("traveler_id", "requirement", "dietary_restriction"),
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
        return json_ok({"status": "ok", "service": "student2-database"})

    @app.get("/travelers/<int:traveler_id>/profile")
    def traveler_profile(traveler_id: int):
        profile = db.fetch_profile(traveler_id, path())
        if profile is None:
            return json_error("Record not found", 404)
        return json_ok(profile)

    @app.get("/<resource>")
    def list_resource(resource: str):
        if resource not in TABLES:
            return json_error("Not found", 404)
        table, _ = TABLES[resource]
        filters: dict[str, Any] = {}
        for key in FILTERS[resource]:
            if key in request.args:
                filters[key] = request.args.get(key)
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

    @app.errorhandler(404)
    def not_found(_exc):
        return json_error("Not found", 404)

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5402"))
    app.run(host="0.0.0.0", port=port)
