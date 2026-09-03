"""HTMX frontend for student-5 travel documents and pre-trip preparation."""

from __future__ import annotations

import html
import logging
import os
from typing import Any

import requests
from flask import Flask, render_template, request

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:5505").rstrip("/")


def api(method: str, path: str, json: dict | None = None, params: dict | None = None) -> tuple[int, Any]:
    try:
        response = requests.request(
            method,
            f"{BACKEND_URL}{path}",
            json=json,
            params=params,
            timeout=90,
        )
    except requests.RequestException as exc:
        logger.warning("Backend unavailable: %s", exc)
        return 503, {"success": False, "error": "Backend API unavailable"}
    if response.status_code == 204:
        return 204, None
    try:
        return response.status_code, response.json()
    except ValueError:
        return response.status_code, {"success": False, "error": "Invalid API response"}


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def error_banner(message: str) -> str:
    return f'<p class="flash error">{esc(message)}</p>'


def success_banner(message: str) -> str:
    return f'<p class="flash success">{esc(message)}</p>'


def documents_table(items: list[dict[str, Any]], message: str = "") -> str:
    rows = []
    for item in items:
        status = str(item.get("status") or "")
        css = "expired" if status == "expired" else "expiring" if status == "expiring" else ""
        rows.append(
            "<tr class='{css}'>"
            "<td>{id}</td><td>{traveller}</td><td>{type}</td><td>{number}</td>"
            "<td>{expiry}</td><td>{status}</td>"
            "<td><button hx-delete='/documents/{id}' hx-target='#documents-table' "
            "hx-confirm='Delete this document?'>Delete</button></td>"
            "</tr>".format(
                css=css,
                id=esc(item.get("id")),
                traveller=esc(item.get("traveller_id")),
                type=esc(item.get("document_type")),
                number=esc(item.get("document_number")),
                expiry=esc(item.get("expiry_date")),
                status=esc(status),
            )
        )
    body = "".join(rows) or "<tr><td colspan='7'>No documents saved yet.</td></tr>"
    banner = message
    return (
        f"{banner}<table><thead><tr><th>ID</th><th>Traveller</th><th>Type</th>"
        f"<th>Number</th><th>Expiry</th><th>Status</th><th></th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )


def requirements_table(items: list[dict[str, Any]], message: str = "") -> str:
    rows = []
    for item in items:
        rows.append(
            "<tr><td>{id}</td><td>{dest}</td><td>{nat}</td><td>{type}</td>"
            "<td>{doc}</td><td>{days}</td><td>{required}</td>"
            "<td><button hx-delete='/requirements/{id}' hx-target='#requirements-table' "
            "hx-confirm='Delete this requirement?'>Delete</button></td></tr>".format(
                id=esc(item.get("id")),
                dest=esc(item.get("destination_country")),
                nat=esc(item.get("traveller_nationality")),
                type=esc(item.get("requirement_type")),
                doc=esc(item.get("document_type")),
                days=esc(item.get("minimum_validity_days")),
                required="Yes" if item.get("is_required") else "No",
            )
        )
    body = "".join(rows) or "<tr><td colspan='8'>No matching demonstration requirements.</td></tr>"
    return (
        f"{message}<table><thead><tr><th>ID</th><th>Destination</th><th>Nationality</th>"
        f"<th>Requirement</th><th>Document</th><th>Min days</th><th>Required</th><th></th>"
        f"</tr></thead><tbody>{body}</tbody></table>"
    )


def packing_markup(lists: list[dict[str, Any]], items_by_list: dict[int, list[dict[str, Any]]]) -> str:
    if not lists:
        return "<p class='empty'>No saved packing lists yet.</p>"
    blocks = []
    for packing in lists:
        items = items_by_list.get(packing.get("id"), [])
        completed = sum(1 for item in items if item.get("is_completed"))
        rows = []
        for item in items:
            checked = "checked" if item.get("is_completed") else ""
            rows.append(
                "<tr><td>{name}</td><td>{cat}</td><td>{qty}</td><td>{ai}</td>"
                "<td><input type='checkbox' {checked} "
                "hx-patch='/checklist/{id}/complete' hx-target='#packing-table' "
                "hx-vals='{{\"is_completed\": %s}}'></td>"
                "<td><button hx-delete='/checklist/{id}' hx-target='#packing-table' "
                "hx-confirm='Delete this item?'>Delete</button></td></tr>" % (
                    "false" if item.get("is_completed") else "true",
                )
            )
            rows[-1] = rows[-1].format(
                name=esc(item.get("item_name")),
                cat=esc(item.get("category")),
                qty=esc(item.get("quantity")),
                ai="AI" if item.get("is_ai_generated") else "custom",
                id=esc(item.get("id")),
                checked=checked,
            )
        add_form = (
            "<form class='inline' hx-post='/checklist' hx-target='#packing-table'>"
            f"<input type='hidden' name='packing_list_id' value='{esc(packing.get('id'))}'>"
            "<input name='item_name' placeholder='Custom item' required>"
            "<select name='category'><option>Clothing</option><option>Toiletries</option>"
            "<option>Electronics</option><option>Documents</option>"
            "<option>Medication / Health</option><option>Activity Equipment</option>"
            "<option>Miscellaneous</option></select>"
            "<input type='number' name='quantity' value='1' min='1'>"
            "<button type='submit'>Add item</button></form>"
        )
        blocks.append(
            f"<article class='card'><h4>{esc(packing.get('destination'))} "
            f"({esc(packing.get('start_date'))} – {esc(packing.get('end_date'))})</h4>"
            f"<p>Progress: {completed}/{len(items)}</p>"
            f"<table><thead><tr><th>Item</th><th>Category</th><th>Qty</th><th>Source</th>"
            f"<th>Done</th><th></th></tr></thead><tbody>"
            f"{''.join(rows) or '<tr><td colspan=\"6\">No items yet.</td></tr>'}"
            f"</tbody></table>{add_form}</article>"
        )
    return "".join(blocks)


def tasks_markup(tasks: list[dict[str, Any]], progress: dict[str, Any], message: str = "") -> str:
    completed = progress.get("completed", 0)
    total = progress.get("total", 0)
    rows = []
    for task in tasks:
        checked = "checked" if task.get("is_completed") else ""
        next_state = "false" if task.get("is_completed") else "true"
        rows.append(
            "<tr><td>{name}</td><td>{due}</td><td>{priority}</td><td>{ai}</td>"
            "<td><input type='checkbox' {checked} hx-patch='/tasks/{id}/complete' "
            "hx-target='#tasks-table' hx-vals='{{\"is_completed\": %s}}'></td>"
            "<td><button hx-delete='/tasks/{id}' hx-target='#tasks-table' "
            "hx-confirm='Delete this task?'>Delete</button></td></tr>" % next_state
        )
        rows[-1] = rows[-1].format(
            name=esc(task.get("task_name")),
            due=esc(task.get("due_date")),
            priority=esc(task.get("priority")),
            ai="AI" if task.get("is_ai_generated") else "custom",
            id=esc(task.get("id")),
            checked=checked,
        )
    body = "".join(rows) or "<tr><td colspan='6'>No pre-trip tasks yet.</td></tr>"
    return (
        f"{message}<p>Progress: {completed}/{total}</p>"
        f"<table><thead><tr><th>Task</th><th>Due</th><th>Priority</th><th>Source</th>"
        f"<th>Done</th><th></th></tr></thead><tbody>{body}</tbody></table>"
    )


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def dashboard():
        return render_template("dashboard.html")

    @app.get("/partials/documents")
    def partial_documents():
        status, body = api("GET", "/api/documents", params=request.args)
        if status != 200:
            return error_banner((body or {}).get("error") or "Unable to load documents")
        return documents_table(body.get("data") or [])

    @app.post("/documents")
    def create_document():
        payload = {key: request.form.get(key) for key in request.form}
        status, body = api("POST", "/api/documents", json=payload)
        docs_status, docs = api("GET", "/api/documents")
        table = documents_table(docs.get("data") or [] if docs_status == 200 else [])
        if status != 201:
            return error_banner((body or {}).get("error") or "Could not create document") + table
        return success_banner("Document saved.") + table

    @app.delete("/documents/<int:record_id>")
    def delete_document(record_id: int):
        api("DELETE", f"/api/documents/{record_id}")
        _, docs = api("GET", "/api/documents")
        return success_banner("Document deleted.") + documents_table((docs or {}).get("data") or [])

    @app.get("/partials/requirements")
    def partial_requirements():
        params = {}
        if request.args.get("destination"):
            params["destination"] = request.args.get("destination")
        if request.args.get("nationality"):
            params["nationality"] = request.args.get("nationality")
        status, body = api("GET", "/api/entry-requirements", params=params)
        if status != 200:
            return error_banner((body or {}).get("error") or "Unable to load requirements")
        return requirements_table(body.get("data") or [])

    @app.post("/requirements")
    def create_requirement():
        payload = {
            "destination_country": request.form.get("destination_country"),
            "traveller_nationality": request.form.get("traveller_nationality"),
            "requirement_type": request.form.get("requirement_type"),
            "document_type": request.form.get("document_type"),
            "description": request.form.get("description"),
            "minimum_validity_days": int(request.form.get("minimum_validity_days") or 0),
            "is_required": request.form.get("is_required") == "true",
        }
        status, body = api("POST", "/api/entry-requirements", json=payload)
        _, items = api("GET", "/api/entry-requirements")
        table = requirements_table((items or {}).get("data") or [])
        if status != 201:
            return error_banner((body or {}).get("error") or "Could not create requirement") + table
        return success_banner("Requirement saved.") + table

    @app.delete("/requirements/<int:record_id>")
    def delete_requirement(record_id: int):
        api("DELETE", f"/api/entry-requirements/{record_id}")
        _, items = api("GET", "/api/entry-requirements")
        return success_banner("Requirement deleted.") + requirements_table((items or {}).get("data") or [])

    def load_packing_view() -> str:
        _, lists_body = api("GET", "/api/packing-lists")
        lists = (lists_body or {}).get("data") or []
        items_by_list: dict[int, list] = {}
        for packing in lists:
            _, items_body = api("GET", "/api/checklist-items", params={"packing_list_id": packing["id"]})
            items_by_list[packing["id"]] = (items_body or {}).get("data") or []
        return packing_markup(lists, items_by_list)

    @app.get("/partials/packing")
    def partial_packing():
        return load_packing_view()

    @app.post("/checklist")
    def add_checklist_item():
        payload = {
            "packing_list_id": int(request.form.get("packing_list_id") or 0),
            "item_name": request.form.get("item_name"),
            "category": request.form.get("category"),
            "quantity": int(request.form.get("quantity") or 1),
            "is_completed": False,
            "is_ai_generated": False,
        }
        status, body = api("POST", "/api/checklist-items", json=payload)
        view = load_packing_view()
        if status != 201:
            return error_banner((body or {}).get("error") or "Could not add item") + view
        return success_banner("Item added.") + view

    @app.patch("/checklist/<int:record_id>/complete")
    def complete_item(record_id: int):
        payload = request.get_json(silent=True) or {"is_completed": True}
        api("PATCH", f"/api/checklist-items/{record_id}/complete", json=payload)
        return load_packing_view()

    @app.delete("/checklist/<int:record_id>")
    def delete_item(record_id: int):
        api("DELETE", f"/api/checklist-items/{record_id}")
        return load_packing_view()

    @app.get("/partials/tasks")
    def partial_tasks():
        _, body = api("GET", "/api/pre-trip-tasks")
        _, progress = api("GET", "/api/pre-trip-tasks/progress")
        return tasks_markup((body or {}).get("data") or [], (progress or {}).get("data") or {})

    @app.post("/tasks")
    def create_task():
        payload = {key: request.form.get(key) for key in request.form}
        payload["is_completed"] = False
        payload["is_ai_generated"] = False
        status, body = api("POST", "/api/pre-trip-tasks", json=payload)
        _, tasks = api("GET", "/api/pre-trip-tasks")
        _, progress = api("GET", "/api/pre-trip-tasks/progress")
        markup = tasks_markup((tasks or {}).get("data") or [], (progress or {}).get("data") or {})
        if status != 201:
            return error_banner((body or {}).get("error") or "Could not create task") + markup
        return success_banner("Task saved.") + markup

    @app.patch("/tasks/<int:record_id>/complete")
    def complete_task(record_id: int):
        payload = request.get_json(silent=True) or {"is_completed": True}
        api("PATCH", f"/api/pre-trip-tasks/{record_id}/complete", json=payload)
        _, tasks = api("GET", "/api/pre-trip-tasks")
        _, progress = api("GET", "/api/pre-trip-tasks/progress")
        return tasks_markup((tasks or {}).get("data") or [], (progress or {}).get("data") or {})

    @app.delete("/tasks/<int:record_id>")
    def delete_task(record_id: int):
        api("DELETE", f"/api/pre-trip-tasks/{record_id}")
        _, tasks = api("GET", "/api/pre-trip-tasks")
        _, progress = api("GET", "/api/pre-trip-tasks/progress")
        return success_banner("Task deleted.") + tasks_markup(
            (tasks or {}).get("data") or [], (progress or {}).get("data") or {}
        )

    @app.post("/ai/compliance")
    def ai_compliance():
        payload = {key: request.form.get(key) for key in request.form}
        status, body = api("POST", "/api/ai/check-compliance", json=payload)
        if status != 200:
            return error_banner((body or {}).get("error") or "AI compliance check failed")
        data = body.get("data") or {}
        missing = "".join(f"<li>{esc(item)}</li>" for item in data.get("missing_documents") or []) or "<li>None</li>"
        expired = "".join(f"<li>{esc(item)}</li>" for item in data.get("expired_documents") or []) or "<li>None</li>"
        expiring = "".join(f"<li>{esc(item)}</li>" for item in data.get("expiring_documents") or []) or "<li>None</li>"
        warnings = "".join(f"<li>{esc(item)}</li>" for item in data.get("warnings") or []) or "<li>None</li>"
        actions = "".join(f"<li>{esc(item)}</li>" for item in data.get("recommended_actions") or []) or "<li>None</li>"
        badge = "compliant" if data.get("compliant") else "not-compliant"
        return (
            f"<article class='card {badge}'><h3>{'Compliant' if data.get('compliant') else 'Not compliant'}</h3>"
            f"<p>{esc(data.get('summary'))}</p>"
            f"<p><strong>Missing</strong></p><ul>{missing}</ul>"
            f"<p><strong>Expired</strong></p><ul>{expired}</ul>"
            f"<p><strong>Expiring</strong></p><ul>{expiring}</ul>"
            f"<p><strong>Warnings</strong></p><ul>{warnings}</ul>"
            f"<p><strong>Recommended actions</strong></p><ul>{actions}</ul>"
            f"<p><strong>AI explanation</strong></p><p>{esc(data.get('reasoning'))}</p>"
            f"<p class='disclaimer'>{esc(data.get('disclaimer'))}</p></article>"
        )

    @app.post("/ai/generate")
    def ai_generate():
        payload = {key: request.form.get(key) for key in request.form}
        payload["planned_activities"] = [
            part.strip() for part in (payload.get("planned_activities") or "").split(",") if part.strip()
        ]
        status, body = api("POST", "/api/ai/generate-pretrip-checklist", json=payload)
        if status != 200:
            return error_banner((body or {}).get("error") or "AI generation failed")
        data = body.get("data") or {}
        packing = data.get("packing_items") or []
        tasks = data.get("pre_trip_tasks") or []
        packing_rows = "".join(
            "<tr><td>{name}</td><td>{cat}</td><td>{qty}</td><td>{reason}</td></tr>".format(
                name=esc(item.get("item_name")),
                cat=esc(item.get("category")),
                qty=esc(item.get("quantity")),
                reason=esc(item.get("reason")),
            )
            for item in packing
        ) or "<tr><td colspan='4'>No packing suggestions.</td></tr>"
        task_rows = "".join(
            "<tr><td>{name}</td><td>{priority}</td><td>{due}</td><td>{reason}</td></tr>".format(
                name=esc(item.get("task_name")),
                priority=esc(item.get("priority")),
                due=esc(item.get("suggested_due_date")),
                reason=esc(item.get("reason")),
            )
            for item in tasks
        ) or "<tr><td colspan='4'>No task suggestions.</td></tr>"
        import json as json_lib

        save_payload = json_lib.dumps(
            {
                "trip": data.get("trip"),
                "packing_items": packing,
                "pre_trip_tasks": tasks,
            }
        )
        return (
            "<article class='card'><h3>Review AI suggestions before saving</h3>"
            "<p>These items are not stored until you accept them.</p>"
            f"<table><thead><tr><th>Item</th><th>Category</th><th>Qty</th><th>Why</th></tr></thead>"
            f"<tbody>{packing_rows}</tbody></table>"
            f"<table><thead><tr><th>Task</th><th>Priority</th><th>Due</th><th>Why</th></tr></thead>"
            f"<tbody>{task_rows}</tbody></table>"
            f"<button hx-post='/ai/save' hx-target='#generated' hx-vals='{html.escape(save_payload)}'>"
            "Save Generated Checklist</button></article>"
        )

    @app.post("/ai/save")
    def ai_save():
        payload = request.get_json(silent=True) or {}
        status, body = api("POST", "/api/ai/save-pretrip-checklist", json=payload)
        if status not in (200, 201):
            return error_banner((body or {}).get("error") or "Could not save suggestions")
        return success_banner("Accepted suggestions saved. AI-generated records are flagged.") + load_packing_view()

    @app.get("/partials/agentic")
    def partial_agentic():
        status, body = api("GET", "/api/agentic/status")
        if status != 200:
            return error_banner((body or {}).get("error") or "Unable to load agentic status")
        data = body.get("data") or {}
        plan = data.get("plan") or {}
        act = data.get("act") or {}
        observe = data.get("observe") or {}
        adapt = data.get("adapt") or {}
        alerts = "".join(f"<li>{esc(item.get('message'))}</li>" for item in observe.get("alerts") or []) or "<li>No alerts</li>"
        steps = "".join(f"<li>{esc(item)}</li>" for item in adapt.get("recommended_next_steps") or [])
        packing = observe.get("packing_progress") or {}
        tasks = observe.get("task_progress") or {}
        return (
            "<article class='card'><h3>PLAN</h3><p>AI analyses destination, dates, climate, activities, "
            f"documents and demonstration entry requirements.</p><p>{esc(plan.get('compliance_summary'))}</p></article>"
            "<article class='card'><h3>ACT</h3><p>Review suggestions, save approved items, complete packing "
            f"and tasks, and keep documents up to date.</p>"
            f"<p>Incomplete packing items: {esc(act.get('incomplete_packing_items'))}. "
            f"Incomplete tasks: {esc(act.get('incomplete_tasks'))}.</p></article>"
            "<article class='card'><h3>OBSERVE</h3><p>The app watches expiry, missing documents, "
            f"unchecked items and approaching travel dates ({esc(observe.get('days_until_departure'))} days).</p>"
            f"<p>Packing {esc(packing.get('completed'))}/{esc(packing.get('total'))} · "
            f"Tasks {esc(tasks.get('completed'))}/{esc(tasks.get('total'))}</p><ul>{alerts}</ul></article>"
            f"<article class='card'><h3>ADAPT</h3><p>Rerun compliance or regenerate checklists when inputs change.</p>"
            f"<ul>{steps}</ul></article>"
        )

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8505"))
    app.run(host="0.0.0.0", port=port)
