"""Public REST API for traveller profiles, preferences, interests and accessibility needs."""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from config import (
    COMPLETENESS_THRESHOLD,
    DATABASE_SERVICE_URL,
    INTEREST_CATEGORIES,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    PORT,
)
from db_client import DatabaseClient, DatabaseUnavailable
from ollama_client import OllamaClient, OllamaError
from preferences import score_profile, structured_preference_set
from validation import (
    ValidationError,
    parse_id,
    require_object,
    validate_accessibility_need,
    validate_interest,
    validate_preference,
    validate_traveler,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


def json_ok(data: Any, status: int = 200):
    return jsonify({"success": True, "data": data}), status


def json_error(message: str, status: int):
    return jsonify({"success": False, "error": message}), status


def create_app(
    db_client: DatabaseClient | None = None,
    ollama_client: OllamaClient | None = None,
) -> Flask:
    app = Flask(__name__)
    app.config["DB_CLIENT"] = db_client or DatabaseClient(DATABASE_SERVICE_URL)
    app.config["OLLAMA"] = ollama_client or OllamaClient()

    def db() -> DatabaseClient:
        return app.config["DB_CLIENT"]

    def ollama() -> OllamaClient:
        return app.config["OLLAMA"]

    def forward(status: int, body: Any):
        if status == 204:
            return "", 204
        if not body:
            return json_error("Unexpected database response", 500)
        if body.get("success"):
            return json_ok(body.get("data"), status)
        return json_error(body.get("error") or "Database error", status)

    def crud_list(resource: str, allowed_filters: tuple[str, ...]):
        params = {
            key: request.args.get(key)
            for key in allowed_filters
            if request.args.get(key) is not None
        }
        try:
            status, body = db().request("GET", f"/{resource}", params=params)
        except DatabaseUnavailable:
            return json_error("Database service unavailable", 503)
        return forward(status, body)

    def crud_get(resource: str, record_id: str):
        try:
            parsed = parse_id(record_id)
        except ValidationError as exc:
            return json_error(exc.message, exc.status)
        try:
            status, body = db().get(resource, parsed)
        except DatabaseUnavailable:
            return json_error("Database service unavailable", 503)
        return forward(status, body)

    def crud_create(resource: str, validator):
        try:
            payload = validator(require_object(request.get_json(silent=True)))
            status, body = db().create(resource, payload)
        except ValidationError as exc:
            return json_error(exc.message, exc.status)
        except DatabaseUnavailable:
            return json_error("Database service unavailable", 503)
        return forward(status, body)

    def crud_update(resource: str, record_id: str, validator):
        try:
            parsed = parse_id(record_id)
            payload = validator(require_object(request.get_json(silent=True)), partial=True)
            status, body = db().update(resource, parsed, payload)
        except ValidationError as exc:
            return json_error(exc.message, exc.status)
        except DatabaseUnavailable:
            return json_error("Database service unavailable", 503)
        return forward(status, body)

    def crud_delete(resource: str, record_id: str):
        try:
            parsed = parse_id(record_id)
            status, body = db().delete(resource, parsed)
        except ValidationError as exc:
            return json_error(exc.message, exc.status)
        except DatabaseUnavailable:
            return json_error("Database service unavailable", 503)
        return forward(status, body)

    def load_profile(traveler_id: int) -> dict[str, Any] | None:
        status, body = db().profile(traveler_id)
        if status != 200 or not body or not body.get("success"):
            return None
        return body.get("data")

    # ---------------------------------------------------------------- health

    @app.get("/health")
    def health():
        return json_ok(
            {
                "status": "ok",
                "service": "student2-backend",
                "ollama_url": OLLAMA_BASE_URL,
                "ollama_model": OLLAMA_MODEL,
            }
        )

    # ------------------------------------------------------------- travelers

    @app.get("/api/travelers")
    def list_travelers():
        return crud_list("travelers", ("email", "username", "travel_style", "home_location"))

    @app.get("/api/travelers/<record_id>")
    def get_traveler(record_id: str):
        return crud_get("travelers", record_id)

    @app.post("/api/travelers")
    def create_traveler():
        return crud_create("travelers", validate_traveler)

    @app.put("/api/travelers/<record_id>")
    def update_traveler(record_id: str):
        return crud_update("travelers", record_id, validate_traveler)

    @app.delete("/api/travelers/<record_id>")
    def delete_traveler(record_id: str):
        return crud_delete("travelers", record_id)

    # ----------------------------------------------------------- preferences

    @app.get("/api/preferences")
    def list_preferences():
        return crud_list("preferences", ("traveler_id", "pace", "currency"))

    @app.get("/api/preferences/<record_id>")
    def get_preference(record_id: str):
        return crud_get("preferences", record_id)

    @app.post("/api/preferences")
    def create_preference():
        return crud_create("preferences", validate_preference)

    @app.put("/api/preferences/<record_id>")
    def update_preference(record_id: str):
        return crud_update("preferences", record_id, validate_preference)

    @app.delete("/api/preferences/<record_id>")
    def delete_preference(record_id: str):
        return crud_delete("preferences", record_id)

    # ------------------------------------------------------------- interests

    @app.get("/api/interests")
    def list_interests():
        return crud_list("interests", ("traveler_id", "interest_category", "priority"))

    @app.get("/api/interests/<record_id>")
    def get_interest(record_id: str):
        return crud_get("interests", record_id)

    @app.post("/api/interests")
    def create_interest():
        return crud_create("interests", validate_interest)

    @app.put("/api/interests/<record_id>")
    def update_interest(record_id: str):
        return crud_update("interests", record_id, validate_interest)

    @app.delete("/api/interests/<record_id>")
    def delete_interest(record_id: str):
        return crud_delete("interests", record_id)

    # --------------------------------------------------- accessibility needs

    @app.get("/api/accessibility-needs")
    def list_accessibility():
        return crud_list(
            "accessibility-needs", ("traveler_id", "requirement", "dietary_restriction")
        )

    @app.get("/api/accessibility-needs/<record_id>")
    def get_accessibility(record_id: str):
        return crud_get("accessibility-needs", record_id)

    @app.post("/api/accessibility-needs")
    def create_accessibility():
        return crud_create("accessibility-needs", validate_accessibility_need)

    @app.put("/api/accessibility-needs/<record_id>")
    def update_accessibility(record_id: str):
        return crud_update("accessibility-needs", record_id, validate_accessibility_need)

    @app.delete("/api/accessibility-needs/<record_id>")
    def delete_accessibility(record_id: str):
        return crud_delete("accessibility-needs", record_id)

    # --------------------------------------------------------------- profile

    @app.get("/api/travelers/<record_id>/profile")
    def traveler_profile(record_id: str):
        """Aggregated profile. This is the endpoint other microservices consume."""
        try:
            parsed = parse_id(record_id)
        except ValidationError as exc:
            return json_error(exc.message, exc.status)
        try:
            profile = load_profile(parsed)
        except DatabaseUnavailable:
            return json_error("Database service unavailable", 503)
        if profile is None:
            return json_error("Record not found", 404)
        return json_ok(
            {
                **profile,
                "preference_set": structured_preference_set(profile),
                "completeness": score_profile(profile, COMPLETENESS_THRESHOLD),
            }
        )

    @app.get("/api/travelers/<record_id>/completeness")
    def profile_completeness(record_id: str):
        """Deterministic completeness gate -- no LLM involved, always reproducible."""
        try:
            parsed = parse_id(record_id)
        except ValidationError as exc:
            return json_error(exc.message, exc.status)
        try:
            profile = load_profile(parsed)
        except DatabaseUnavailable:
            return json_error("Database service unavailable", 503)
        if profile is None:
            return json_error("Record not found", 404)
        return json_ok(score_profile(profile, COMPLETENESS_THRESHOLD))

    # ------------------------------------------------------------ AI (Ollama)

    @app.post("/api/ai/summarise-profile")
    def summarise_profile():
        """Summarise a traveller profile into a structured preference set.

        The deterministic preference set is computed first and always returned;
        the LLM adds a natural-language summary and planning hints on top of it.
        """
        try:
            payload = require_object(request.get_json(silent=True))
            traveler_id = parse_id(payload.get("traveler_id"))
            profile = load_profile(traveler_id)
        except ValidationError as exc:
            return json_error(exc.message, exc.status)
        except DatabaseUnavailable:
            return json_error("Database service unavailable", 503)
        if profile is None:
            return json_error("Record not found", 404)

        deterministic = structured_preference_set(profile)
        completeness = score_profile(profile, COMPLETENESS_THRESHOLD)
        prompt = (
            "You are a travel-preference assistant for a trip planning system.\n"
            "Summarise the traveller's stored preferences into a structured set that "
            "another microservice can use to personalise an itinerary.\n"
            "Only use the supplied records. Do not invent preferences, budgets, "
            "interests, dietary requirements or accessibility needs.\n"
            "Return JSON only with keys: summary, planning_hints, suggested_interests, reasoning.\n"
            "summary: one short paragraph describing this traveller.\n"
            "planning_hints: array of short strings an itinerary planner should honour.\n"
            "suggested_interests: array of categories from the allowed list that this "
            "traveller has NOT selected but may enjoy, each with a reason.\n"
            f"Allowed interest categories: {', '.join(INTEREST_CATEGORIES)}.\n"
            "reasoning: explain WHY the hints were derived, referencing the stored data.\n"
            f"Context: {json.dumps({'profile': profile, 'preference_set': deterministic, 'completeness': completeness})}"
        )
        try:
            ai_data = ollama().generate_json(prompt)
        except OllamaError as exc:
            return json_error(exc.message, exc.status)

        merged: dict[str, Any] = {
            "preference_set": deterministic,
            "completeness": completeness,
            "phase": "PLAN",
            "review_required": True,
            "persisted": False,
        }
        if isinstance(ai_data.get("summary"), str) and ai_data["summary"].strip():
            merged["summary"] = ai_data["summary"].strip()
        if isinstance(ai_data.get("reasoning"), str):
            merged["reasoning"] = ai_data["reasoning"].strip()
        if isinstance(ai_data.get("planning_hints"), list):
            merged["planning_hints"] = [str(item) for item in ai_data["planning_hints"]]
        if isinstance(ai_data.get("suggested_interests"), list):
            # Never let the model invent a category outside the schema's CHECK list.
            merged["suggested_interests"] = [
                item
                for item in ai_data["suggested_interests"]
                if isinstance(item, dict)
                and item.get("interest_category") in INTEREST_CATEGORIES
                and item.get("interest_category") not in deterministic["interests"]
            ]
        return json_ok(merged)

    @app.post("/api/ai/check-completeness")
    def ai_check_completeness():
        """AI-assisted explanation of the deterministic completeness result."""
        try:
            payload = require_object(request.get_json(silent=True))
            traveler_id = parse_id(payload.get("traveler_id"))
            profile = load_profile(traveler_id)
        except ValidationError as exc:
            return json_error(exc.message, exc.status)
        except DatabaseUnavailable:
            return json_error("Database service unavailable", 503)
        if profile is None:
            return json_error("Record not found", 404)

        deterministic = score_profile(profile, COMPLETENESS_THRESHOLD)
        prompt = (
            "You are validating whether a traveller profile is complete enough to "
            "begin trip planning.\n"
            "The deterministic score has already been computed -- do not change it.\n"
            "Explain what is missing and what the traveller should do next.\n"
            "Return JSON only with keys: summary, next_steps, reasoning.\n"
            "next_steps: array of short, actionable strings.\n"
            "Do not invent profile fields that are not in the supplied data.\n"
            f"Context: {json.dumps({'profile': profile, 'completeness': deterministic})}"
        )
        try:
            ai_data = ollama().generate_json(prompt)
        except OllamaError as exc:
            return json_error(exc.message, exc.status)

        merged = dict(deterministic)
        merged["phase"] = "OBSERVE"
        if isinstance(ai_data.get("summary"), str) and ai_data["summary"].strip():
            merged["summary"] = ai_data["summary"].strip()
        if isinstance(ai_data.get("reasoning"), str):
            merged["reasoning"] = ai_data["reasoning"].strip()
        if isinstance(ai_data.get("next_steps"), list):
            merged["recommendations"] = list(
                dict.fromkeys(
                    merged["recommendations"] + [str(item) for item in ai_data["next_steps"]]
                )
            )
        return json_ok(merged)

    @app.post("/api/ai/apply-suggested-interests")
    def apply_suggested_interests():
        """Human-reviewed ACT step: persist only the interests the user accepted."""
        try:
            payload = require_object(request.get_json(silent=True))
            traveler_id = parse_id(payload.get("traveler_id"))
            accepted = payload.get("interests") or []
            if not isinstance(accepted, list) or not accepted:
                raise ValidationError("interests must be a non-empty list")
            saved = []
            skipped = []
            for item in accepted:
                category = item.get("interest_category") if isinstance(item, dict) else item
                if category not in INTEREST_CATEGORIES:
                    skipped.append({"interest_category": category, "reason": "not an allowed category"})
                    continue
                priority = item.get("priority", "medium") if isinstance(item, dict) else "medium"
                interest_payload = validate_interest(
                    {
                        "traveler_id": traveler_id,
                        "interest_category": category,
                        "priority": priority,
                    }
                )
                status, body = db().create("interests", interest_payload)
                if status == 201 and body and body.get("success"):
                    saved.append(body["data"])
                else:
                    reason = (body or {}).get("error", "rejected by database")
                    skipped.append({"interest_category": category, "reason": reason})
        except ValidationError as exc:
            return json_error(exc.message, exc.status)
        except DatabaseUnavailable:
            return json_error("Database service unavailable", 503)
        return json_ok({"saved": saved, "skipped": skipped, "phase": "ACT"}, 201)

    # --------------------------------------------- Plan -> Act -> Observe -> Adapt

    @app.get("/api/agentic/status")
    def agentic_status():
        """Expose the shared agentic loop for this microservice."""
        traveler_id_raw = request.args.get("traveler_id", "1")
        try:
            traveler_id = parse_id(traveler_id_raw)
            profile = load_profile(traveler_id)
        except ValidationError as exc:
            return json_error(exc.message, exc.status)
        except DatabaseUnavailable:
            return json_error("Database service unavailable", 503)
        if profile is None:
            return json_error("Record not found", 404)

        completeness = score_profile(profile, COMPLETENESS_THRESHOLD)
        preference_set = structured_preference_set(profile)

        adapt_actions: list[str] = []
        if not completeness["ready_for_trip_planning"]:
            adapt_actions.append(
                "Profile is below the trip-planning threshold. "
                "Collect the missing fields, then re-run the completeness check."
            )
        if completeness["counts"]["interests"] < 3:
            adapt_actions.append(
                "Ask the traveller to add more interests, or run "
                "/api/ai/summarise-profile for AI-suggested categories."
            )
        if not completeness["counts"]["has_preferences"]:
            adapt_actions.append("Capture a budget range and pace before planning a trip.")
        if not adapt_actions:
            adapt_actions.append(
                "Profile is complete. Trip Planning may consume the preference set."
            )

        return json_ok(
            {
                "plan": {
                    "goal": "Produce a complete, structured preference set for trip planning.",
                    "threshold": COMPLETENESS_THRESHOLD,
                    "recommended_actions": completeness["recommendations"],
                },
                "act": {
                    "records_captured": {
                        "interests": completeness["counts"]["interests"],
                        "accessibility_needs": completeness["counts"]["accessibility_needs"],
                        "has_preferences": completeness["counts"]["has_preferences"],
                    },
                    "preference_set": preference_set,
                },
                "observe": {
                    "completeness_score": completeness["score"],
                    "missing": completeness["missing"],
                    "ready_for_trip_planning": completeness["ready_for_trip_planning"],
                },
                "adapt": {"recommended_next_steps": adapt_actions},
            }
        )

    @app.errorhandler(404)
    def not_found(_exc):
        return json_error("Not found", 404)

    @app.errorhandler(500)
    def server_error(_exc):
        logger.exception("Unexpected server error")
        return json_error("Internal server error", 500)

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", str(PORT)))
    app.run(host="0.0.0.0", port=port)
