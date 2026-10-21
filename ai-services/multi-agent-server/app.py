"""Expose the ASD-02 Travel Agent multi-agent workflow through HTTP.

POST /workflow accepts a user_request describing a travel feature to assess.
The coordinator runs the agents and records their results for human review.
GET /workflow/status returns saved history information, not live job progress.
"""

import logging
import os

from flask import Flask, jsonify, request
from flask_cors import CORS

from coordinator import PROJECT_NAME, get_workflow, record_human_review, run_workflow, workflow_status


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)

app = Flask(__name__)
CORS(app)


@app.get("/")
def health():
    return jsonify(
        {
            "service": "multi-agent-server",
            "project": PROJECT_NAME,
            "status": "running"
        }
    )


@app.post("/workflow")
def workflow():
    data = request.get_json(
        silent=True
    )

    if not isinstance(data, dict):
        return jsonify(
            {
                "status": "error",
                "error": "Request body must be a JSON object with a user_request string"
            }
        ), 400

    user_request = data.get(
        "user_request",
        ""
    )

    if not isinstance(user_request, str):
        return jsonify(
            {
                "status": "error",
                "error": "user_request must be a string"
            }
        ), 400

    user_request = user_request.strip()

    if not user_request:
        return jsonify(
            {
                "status": "error",
                "error": "user_request is required"
            }
        ), 400

    general_request = any(key in data for key in ("service", "task", "context"))
    if general_request:
        if "itinerary_context" in data:
            return jsonify({"status": "error", "error": "Use context or itinerary_context, not both"}), 400
        for field in ("service", "task"):
            if not isinstance(data.get(field), str) or not data[field].strip():
                return jsonify({"status": "error", "error": f"{field} must be a non-empty string"}), 400
        if not isinstance(data.get("context"), dict):
            return jsonify({"status": "error", "error": "context must be a JSON object"}), 400

    itinerary_context = data.get("itinerary_context")
    if itinerary_context is not None:
        itinerary = itinerary_context.get("itinerary") if isinstance(itinerary_context, dict) else None
        itinerary_id = itinerary.get("itinerary_id") if isinstance(itinerary, dict) else None
        if (
                type(itinerary_id) is not int or itinerary_id <= 0
                or not isinstance(itinerary_context.get("activities"), list)
                or any(not isinstance(activity, dict) for activity in itinerary_context["activities"])
        ):
            return jsonify({"status": "error", "error": "itinerary_context must contain an itinerary with a positive integer itinerary_id and an activities list"}), 400

    try:
        result = run_workflow(
            user_request,
            itinerary_context,
            service=data["service"].strip() if general_request else None,
            task=data["task"].strip() if general_request else None,
            context=data["context"] if general_request else None
        )
    except Exception:
        app.logger.exception("Multi-agent workflow failed")
        return jsonify({"status": "error", "error": "Multi-agent workflow failed"}), 500

    return jsonify(
        result
    ), 200


@app.get("/workflow/status")
def status():
    return jsonify(
        workflow_status()
    ), 200


@app.get("/workflow/<workflow_id>")
def workflow_by_id(workflow_id):
    result = get_workflow(workflow_id)
    if result is None:
        return jsonify({"status": "error", "error": "Workflow not found"}), 404
    return jsonify(result), 200


@app.post("/workflow/<workflow_id>/review")
def human_review(workflow_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"status": "error", "error": "Request body must be a JSON object"}), 400

    decision = data.get("decision")
    reason = data.get("reason")
    evidence = data.get("evidence", "")
    if not isinstance(decision, str) or decision not in ("Accept", "Partially Accept", "Reject"):
        return jsonify({"status": "error", "error": "decision must be Accept, Partially Accept, or Reject"}), 400
    if not isinstance(reason, str) or len(reason.strip()) < 20:
        return jsonify({"status": "error", "error": "reason must contain at least 20 characters"}), 400
    if not isinstance(evidence, str):
        return jsonify({"status": "error", "error": "evidence must be a string"}), 400

    result = record_human_review(workflow_id, decision, reason.strip(), evidence.strip())
    if result is None:
        return jsonify({"status": "error", "error": "Workflow not found"}), 404
    return jsonify(result), 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "6767")),
        debug=True
    )
