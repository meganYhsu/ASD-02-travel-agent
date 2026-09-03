"""HTMX frontend for student-2 traveller preferences."""

from __future__ import annotations

import html
import logging
import os
from typing import Any

import requests
from flask import Flask, render_template, request

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:5502").rstrip("/")

TRAVEL_STYLES = ("Budget", "Mid-range", "Luxury")
PACES = ("relaxed", "balanced", "packed")
PRIORITIES = ("low", "medium", "high")
CURRENCIES = ("AUD", "NZD", "USD", "EUR", "GBP", "JPY")
INTEREST_CATEGORIES = (
    "Food & Dining", "History & Culture", "Nature & Outdoors", "Art & Museums",
    "Nightlife", "Shopping", "Adventure Sports", "Beaches", "Architecture",
    "Local Experiences", "Wellness & Spa", "Photography",
)
ACCESSIBILITY_REQUIREMENTS = (
    "None", "Step-free access", "Wheelchair accessible", "Limited walking",
    "Visual assistance", "Hearing assistance", "Service animal",
    "Accessible bathroom", "Elevator required", "Other",
)
DIETARY_RESTRICTIONS = (
    "None", "Vegetarian", "Vegan", "Halal", "Kosher", "Gluten-free",
    "Nut allergy", "Dairy-free", "Shellfish allergy", "Other",
)


def api(method: str, path: str, json: dict | None = None, params: dict | None = None) -> tuple[int, Any]:
    try:
        response = requests.request(
            method, f"{BACKEND_URL}{path}", json=json, params=params, timeout=90
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


def data_or_error(status: int, body: Any) -> tuple[Any, str]:
    """Return (data, banner_html). Banner is empty when the call succeeded."""
    if status >= 400 or not body or not body.get("success"):
        message = (body or {}).get("error", "Request failed")
        return None, error_banner(message)
    return body.get("data"), ""


def traveler_id_from_request() -> str:
    return (request.values.get("traveler_id") or "1").strip()


# ------------------------------------------------------------------ fragments


def travelers_table(message: str = "") -> str:
    status, body = api("GET", "/api/travelers")
    rows_data, banner = data_or_error(status, body)
    if rows_data is None:
        return message + banner
    rows = []
    for item in rows_data:
        rows.append(
            "<tr><td>{id}</td><td>{name}</td><td>{user}</td><td>{email}</td>"
            "<td>{home}</td><td>{style}</td>"
            "<td><button class='link' hx-get='/panel?traveler_id={id}' hx-target='#workspace'>Open</button>"
            "<button class='danger' hx-delete='/travelers/{id}' hx-target='#travelers-table' "
            "hx-confirm='Delete this traveller and all their preferences?'>Delete</button></td></tr>".format(
                id=esc(item.get("id")), name=esc(item.get("full_name")),
                user=esc(item.get("username")), email=esc(item.get("email")),
                home=esc(item.get("home_location")), style=esc(item.get("travel_style")),
            )
        )
    body_html = "".join(rows) or "<tr><td colspan='7'>No travellers yet.</td></tr>"
    return (
        f"{message}<table><thead><tr><th>ID</th><th>Name</th><th>Username</th>"
        f"<th>Email</th><th>Home</th><th>Style</th><th></th></tr></thead>"
        f"<tbody>{body_html}</tbody></table>"
    )


def profile_panel(traveler_id: str, message: str = "") -> str:
    status, body = api("GET", f"/api/travelers/{traveler_id}/profile")
    profile, banner = data_or_error(status, body)
    if profile is None:
        return message + banner

    traveler = profile.get("traveler") or {}
    prefs = profile.get("preferences")
    interests = profile.get("interests") or []
    needs = profile.get("accessibility_needs") or []
    pset = profile.get("preference_set") or {}
    comp = profile.get("completeness") or {}

    # --- profile header (email + username, per the feature spec)
    head = (
        f"<div class='profile-head'><h3>{esc(traveler.get('full_name'))}</h3>"
        f"<p class='muted'>{esc(traveler.get('username'))} &middot; {esc(traveler.get('email'))}<br>"
        f"{esc(traveler.get('home_location'))} &middot; {esc(traveler.get('travel_style'))}</p></div>"
    )

    # --- completeness meter
    score = comp.get("score", 0)
    ready = comp.get("ready_for_trip_planning")
    state = "ok" if ready else "warn"
    missing = ", ".join(comp.get("missing") or []) or "nothing"
    meter = (
        f"<div class='meter'><div class='meter-bar'><span style='width:{score}%'></span></div>"
        f"<p><strong>{score}%</strong> complete &middot; "
        f"<span class='pill {state}'>{'ready for trip planning' if ready else 'not ready'}</span></p>"
        f"<p class='muted'>Missing: {esc(missing)}</p></div>"
    )

    # --- budget / pace form
    if prefs:
        pref_form = (
            "<form hx-put='/preferences/{pid}' hx-target='#workspace'>"
            "<input type='hidden' name='traveler_id' value='{tid}'>"
            "<div class='grid'>"
            "<label>Budget min<input type='number' step='0.01' min='0' name='budget_min' value='{bmin}' required></label>"
            "<label>Budget max<input type='number' step='0.01' min='0' name='budget_max' value='{bmax}' required></label>"
            "<label>Currency<select name='currency'>{cur}</select></label>"
            "<label>Pace<select name='pace'>{pace}</select></label>"
            "<label>Trip length (days)<input type='number' min='1' name='preferred_trip_length_days' value='{days}'></label>"
            "</div><button type='submit'>Save preferences</button></form>"
        ).format(
            pid=esc(prefs.get("id")), tid=esc(traveler_id),
            bmin=esc(prefs.get("budget_min")), bmax=esc(prefs.get("budget_max")),
            days=esc(prefs.get("preferred_trip_length_days") or ""),
            cur=options(CURRENCIES, prefs.get("currency")),
            pace=options(PACES, prefs.get("pace")),
        )
    else:
        pref_form = (
            "<p class='muted'>No budget or pace saved yet.</p>"
            "<form hx-post='/preferences' hx-target='#workspace'>"
            "<input type='hidden' name='traveler_id' value='{tid}'>"
            "<div class='grid'>"
            "<label>Budget min<input type='number' step='0.01' min='0' name='budget_min' required></label>"
            "<label>Budget max<input type='number' step='0.01' min='0' name='budget_max' required></label>"
            "<label>Currency<select name='currency'>{cur}</select></label>"
            "<label>Pace<select name='pace'>{pace}</select></label>"
            "<label>Trip length (days)<input type='number' min='1' name='preferred_trip_length_days'></label>"
            "</div><button type='submit'>Save preferences</button></form>"
        ).format(tid=esc(traveler_id), cur=options(CURRENCIES), pace=options(PACES))

    # --- interests
    chips = "".join(
        "<li class='chip prio-{p}'>{c}<button class='x' hx-delete='/interests/{id}?traveler_id={tid}' "
        "hx-target='#workspace' title='Remove'>&times;</button></li>".format(
            p=esc(item.get("priority")), c=esc(item.get("interest_category")),
            id=esc(item.get("id")), tid=esc(traveler_id),
        )
        for item in interests
    ) or "<li class='muted'>No interests selected.</li>"
    interest_form = (
        "<form hx-post='/interests' hx-target='#workspace' class='inline'>"
        "<input type='hidden' name='traveler_id' value='{tid}'>"
        "<select name='interest_category' required>{cats}</select>"
        "<select name='priority'>{prios}</select>"
        "<button type='submit'>Add interest</button></form>"
    ).format(tid=esc(traveler_id), cats=options(INTEREST_CATEGORIES), prios=options(PRIORITIES, "medium"))

    # --- accessibility + dietary
    need_rows = "".join(
        "<tr><td>{req}</td><td>{diet}</td><td>{notes}</td>"
        "<td><button class='danger' hx-delete='/needs/{id}?traveler_id={tid}' "
        "hx-target='#workspace'>Delete</button></td></tr>".format(
            req=esc(item.get("requirement")), diet=esc(item.get("dietary_restriction")),
            notes=esc(item.get("notes") or ""), id=esc(item.get("id")), tid=esc(traveler_id),
        )
        for item in needs
    ) or "<tr><td colspan='4' class='muted'>No accessibility or dietary needs recorded.</td></tr>"
    need_form = (
        "<form hx-post='/needs' hx-target='#workspace' class='inline'>"
        "<input type='hidden' name='traveler_id' value='{tid}'>"
        "<select name='requirement'>{reqs}</select>"
        "<select name='dietary_restriction'>{diets}</select>"
        "<input type='text' name='notes' placeholder='Notes (optional)'>"
        "<button type='submit'>Add need</button></form>"
    ).format(
        tid=esc(traveler_id),
        reqs=options(ACCESSIBILITY_REQUIREMENTS, "None"),
        diets=options(DIETARY_RESTRICTIONS, "None"),
    )

    # --- saved preference summary (the structured set other services consume)
    summary = (
        "<dl class='summary'>"
        f"<dt>Travel style</dt><dd>{esc(pset.get('travel_style'))}</dd>"
        f"<dt>Budget</dt><dd>{budget_text(pset.get('budget'))}</dd>"
        f"<dt>Pace</dt><dd>{esc(pset.get('pace') or 'not set')}</dd>"
        f"<dt>Interests</dt><dd>{esc(', '.join(pset.get('interests') or []) or 'none')}</dd>"
        f"<dt>Top interests</dt><dd>{esc(', '.join(pset.get('top_interests') or []) or 'none')}</dd>"
        f"<dt>Accessibility</dt><dd>{esc(', '.join(pset.get('accessibility_requirements') or []) or 'none')}</dd>"
        f"<dt>Dietary</dt><dd>{esc(', '.join(pset.get('dietary_restrictions') or []) or 'none')}</dd>"
        "</dl>"
    )

    ai_buttons = (
        "<div class='inline'>"
        f"<button hx-post='/ai/completeness' hx-vals='{{\"traveler_id\": \"{esc(traveler_id)}\"}}' "
        "hx-target='#ai-output' hx-indicator='#ai-spin'>Run AI completeness check</button>"
        f"<button hx-post='/ai/summarise' hx-vals='{{\"traveler_id\": \"{esc(traveler_id)}\"}}' "
        "hx-target='#ai-output' hx-indicator='#ai-spin'>Summarise profile with AI</button>"
        f"<button hx-get='/agentic?traveler_id={esc(traveler_id)}' "
        "hx-target='#ai-output' hx-indicator='#ai-spin'>Show agentic loop</button>"
        "<span id='ai-spin' class='htmx-indicator'>contacting Ollama&hellip;</span></div>"
    )

    return f"""{message}
<input type='hidden' id='current-traveler' value='{esc(traveler_id)}'>
<section class='panel'>{head}{meter}</section>
<section class='panel'><h4>Budget &amp; pace</h4>{pref_form}</section>
<section class='panel'><h4>Interests</h4><ul class='chips'>{chips}</ul>{interest_form}</section>
<section class='panel'><h4>Accessibility &amp; dietary needs</h4>
<table><thead><tr><th>Requirement</th><th>Dietary</th><th>Notes</th><th></th></tr></thead>
<tbody>{need_rows}</tbody></table>{need_form}</section>
<section class='panel'><h4>Saved preference summary</h4>{summary}</section>
<section class='panel'><h4>AI assistance</h4>{ai_buttons}<div id='ai-output'></div></section>
"""


def options(values: tuple[str, ...], selected: Any = None) -> str:
    return "".join(
        f"<option value='{esc(v)}'{' selected' if str(v) == str(selected) else ''}>{esc(v)}</option>"
        for v in values
    )


def budget_text(budget: Any) -> str:
    if not budget or budget.get("min") is None:
        return "not set"
    return esc(f"{budget.get('currency','')} {budget.get('min')} - {budget.get('max')}")


def ai_block(title: str, data: dict[str, Any]) -> str:
    parts = [f"<h5>{esc(title)}</h5>"]
    if data.get("phase"):
        parts.append(f"<p><span class='pill'>phase: {esc(data['phase'])}</span></p>")
    if data.get("summary"):
        parts.append(f"<p>{esc(data['summary'])}</p>")
    for key, label in (
        ("recommendations", "Recommendations"),
        ("planning_hints", "Planning hints"),
        ("next_steps", "Next steps"),
    ):
        items = data.get(key)
        if isinstance(items, list) and items:
            lis = "".join(f"<li>{esc(i)}</li>" for i in items)
            parts.append(f"<p><strong>{label}</strong></p><ul>{lis}</ul>")
    suggested = data.get("suggested_interests")
    if isinstance(suggested, list) and suggested:
        rows = "".join(
            "<li>{c} <span class='muted'>{r}</span> "
            "<button hx-post='/ai/apply' hx-target='#workspace' "
            "hx-vals='{{\"traveler_id\": \"{tid}\", \"interest_category\": \"{c}\"}}'>Accept</button></li>".format(
                c=esc(i.get("interest_category")), r=esc(i.get("reason") or ""),
                tid=esc(data.get("traveler_id") or ""),
            )
            for i in suggested
        )
        parts.append(f"<p><strong>Suggested interests</strong> (human review required)</p><ul>{rows}</ul>")
    if data.get("reasoning"):
        parts.append(f"<details><summary>Model reasoning</summary><p>{esc(data['reasoning'])}</p></details>")
    return f"<div class='ai-card'>{''.join(parts)}</div>"


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/health")
    def health():
        return {"success": True, "data": {"status": "ok", "service": "student2-frontend"}}

    @app.get("/")
    def index():
        return render_template(
            "dashboard.html",
            travel_styles=TRAVEL_STYLES,
            backend_url=BACKEND_URL,
        )

    @app.get("/travelers")
    def travelers():
        return travelers_table()

    @app.post("/travelers")
    def create_traveler():
        payload = {k: request.form.get(k, "").strip() for k in
                   ("full_name", "username", "email", "home_location", "travel_style")}
        status, body = api("POST", "/api/travelers", json=payload)
        if status >= 400:
            return travelers_table(error_banner((body or {}).get("error", "Could not create traveller")))
        return travelers_table(success_banner("Traveller created."))

    @app.delete("/travelers/<record_id>")
    def delete_traveler(record_id: str):
        status, body = api("DELETE", f"/api/travelers/{record_id}")
        if status >= 400:
            return travelers_table(error_banner((body or {}).get("error", "Could not delete traveller")))
        return travelers_table(success_banner("Traveller deleted."))

    @app.get("/panel")
    def panel():
        return profile_panel(traveler_id_from_request())

    @app.post("/preferences")
    def create_preference():
        tid = traveler_id_from_request()
        payload = form_preferences(tid)
        status, body = api("POST", "/api/preferences", json=payload)
        if status >= 400:
            return profile_panel(tid, error_banner((body or {}).get("error", "Could not save preferences")))
        return profile_panel(tid, success_banner("Preferences saved."))

    @app.put("/preferences/<record_id>")
    def update_preference(record_id: str):
        tid = traveler_id_from_request()
        payload = form_preferences(tid)
        payload.pop("traveler_id", None)
        status, body = api("PUT", f"/api/preferences/{record_id}", json=payload)
        if status >= 400:
            return profile_panel(tid, error_banner((body or {}).get("error", "Could not update preferences")))
        return profile_panel(tid, success_banner("Preferences updated."))

    @app.post("/interests")
    def add_interest():
        tid = traveler_id_from_request()
        payload = {
            "traveler_id": int(tid),
            "interest_category": request.form.get("interest_category"),
            "priority": request.form.get("priority", "medium"),
        }
        status, body = api("POST", "/api/interests", json=payload)
        if status >= 400:
            return profile_panel(tid, error_banner((body or {}).get("error", "Could not add interest")))
        return profile_panel(tid, success_banner("Interest added."))

    @app.delete("/interests/<record_id>")
    def remove_interest(record_id: str):
        tid = traveler_id_from_request()
        api("DELETE", f"/api/interests/{record_id}")
        return profile_panel(tid, success_banner("Interest removed."))

    @app.post("/needs")
    def add_need():
        tid = traveler_id_from_request()
        payload = {
            "traveler_id": int(tid),
            "requirement": request.form.get("requirement"),
            "dietary_restriction": request.form.get("dietary_restriction"),
            "notes": request.form.get("notes") or None,
        }
        status, body = api("POST", "/api/accessibility-needs", json=payload)
        if status >= 400:
            return profile_panel(tid, error_banner((body or {}).get("error", "Could not add need")))
        return profile_panel(tid, success_banner("Accessibility need added."))

    @app.delete("/needs/<record_id>")
    def remove_need(record_id: str):
        tid = traveler_id_from_request()
        api("DELETE", f"/api/accessibility-needs/{record_id}")
        return profile_panel(tid, success_banner("Accessibility need removed."))

    @app.post("/ai/completeness")
    def ai_completeness():
        tid = traveler_id_from_request()
        status, body = api("POST", "/api/ai/check-completeness", json={"traveler_id": int(tid)})
        data, banner = data_or_error(status, body)
        if data is None:
            return banner
        return ai_block("AI profile completeness check", data)

    @app.post("/ai/summarise")
    def ai_summarise():
        tid = traveler_id_from_request()
        status, body = api("POST", "/api/ai/summarise-profile", json={"traveler_id": int(tid)})
        data, banner = data_or_error(status, body)
        if data is None:
            return banner
        data["traveler_id"] = tid
        return ai_block("AI preference summary", data)

    @app.post("/ai/apply")
    def ai_apply():
        tid = traveler_id_from_request()
        category = request.values.get("interest_category")
        status, body = api(
            "POST",
            "/api/ai/apply-suggested-interests",
            json={"traveler_id": int(tid), "interests": [{"interest_category": category}]},
        )
        if status >= 400:
            return profile_panel(tid, error_banner((body or {}).get("error", "Could not apply suggestion")))
        return profile_panel(tid, success_banner(f"Accepted AI suggestion: {category}."))

    @app.get("/agentic")
    def agentic():
        tid = traveler_id_from_request()
        status, body = api("GET", "/api/agentic/status", params={"traveler_id": tid})
        data, banner = data_or_error(status, body)
        if data is None:
            return banner
        blocks = []
        for phase in ("plan", "act", "observe", "adapt"):
            section = data.get(phase) or {}
            items = []
            for key, value in section.items():
                if isinstance(value, list):
                    value = ", ".join(str(v) for v in value) or "none"
                elif isinstance(value, dict):
                    value = ", ".join(f"{k}={v}" for k, v in value.items())
                items.append(f"<li><strong>{esc(key)}</strong>: {esc(value)}</li>")
            blocks.append(
                f"<div class='phase'><h5>{phase.upper()}</h5><ul>{''.join(items)}</ul></div>"
            )
        return f"<div class='ai-card agentic'>{''.join(blocks)}</div>"

    return app


def form_preferences(traveler_id: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "traveler_id": int(traveler_id),
        "budget_min": request.form.get("budget_min"),
        "budget_max": request.form.get("budget_max"),
        "currency": request.form.get("currency", "AUD"),
        "pace": request.form.get("pace"),
    }
    days = request.form.get("preferred_trip_length_days")
    payload["preferred_trip_length_days"] = int(days) if days and days.strip() else None
    return payload


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8502"))
    app.run(host="0.0.0.0", port=port)
