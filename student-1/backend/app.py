"""Student 1 - Traveler Preferences Backend/API (port 5001)

Serves HTML fragments to the HTMX frontend and JSON to other backends.
All traveller data is read and written through the Student 1 database API -
this service never opens preferences.db itself.

The AI endpoints run the shared Plan -> Act -> Observe -> Adapt loop and
print each stage to the terminal so the loop can be demonstrated live.
"""

from flask import Flask, jsonify, request
from dotenv import load_dotenv
from openai import OpenAI
from markupsafe import escape
from pathlib import Path
import json
import os
import requests
import uuid

load_dotenv()


def flag(name):
    """AI feature switches. Off unless set to true, so CI and the cloud
    baseline run with every AI service disabled; docker-compose and .env turn
    them on for local runs."""
    return os.getenv(name, "false").strip().lower() in ("true", "1", "yes")


DB_API_URL = os.getenv("DB_API_URL", "http://127.0.0.1:6001")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")

# AI-Mode: the summarise and completeness-explanation calls to Ollama.
AI_MODE_ENABLED = flag("AI_MODE_ENABLED")

# Shared MCP server runs on the host, not in Docker, so in compose this is
# http://host.docker.internal:7004.
MCP_BASE_URL = os.getenv("MCP_BASE_URL", "http://127.0.0.1:7004").rstrip("/")
MCP_ENABLED = flag("MCP_ENABLED")

# The only shared MCP tools this feature may call - its own data, nothing else.
MCP_TOOLS = {
    "get_traveler_profile": "Traveller profile",
    "get_traveler_interests": "Ranked interests",
    "get_accessibility_needs": "Accessibility and dietary needs",
}

# Shared RAG server also runs on the host: http://host.docker.internal:7001 in
# compose.
RAG_BASE_URL = os.getenv("RAG_BASE_URL", "http://127.0.0.1:7001").rstrip("/")
RAG_ENABLED = flag("RAG_ENABLED")
RAG_MAX_QUESTION = 300

# Release 2 shared Multi-Agent server (ai-services/multi-agent-server, port
# 6767, not containerised). One workflow is three sequential model calls, so
# the wait is long; the frontend proxy waits longer still.
MULTI_AGENT_SERVICE_URL = os.getenv(
    "MULTI_AGENT_SERVICE_URL", "http://127.0.0.1:6767").rstrip("/")
MULTI_AGENT_ENABLED = flag("MULTI_AGENT_ENABLED")
MULTI_AGENT_TIMEOUT_SECONDS = int(os.getenv("MULTI_AGENT_TIMEOUT_SECONDS", "420"))
MULTI_AGENT_SERVICE = "traveller"
MULTI_AGENT_TASK = "review_preferences"
MULTI_AGENT_MAX_REQUEST = 500
DEFAULT_REVIEW_REQUEST = (
    "Check this traveller's saved preferences are complete and consistent, "
    "then summarise them as a brief for trip planning. Flag anything missing "
    "or contradictory."
)
REVIEW_DECISIONS = ("Accept", "Partially Accept", "Reject")
REVIEW_MIN_REASON = 20

PROMPT_DIR = Path(__file__).with_name("prompts")
PORT = int(os.getenv("PORT", "5001"))

REQUIRED_LABELS = ("BUDGET:", "STYLE:", "PRIORITIES:", "CONSTRAINTS:")

app = Flask(__name__)

client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")


def load_prompt(filename):
    return (PROMPT_DIR / filename).read_text(encoding="utf-8").strip()


def log_stage(stage, message):
    """Agentic loop evidence. Printed so it is visible in `docker compose logs`."""
    print(f"[AGENTIC LOOP][{stage}] {message}", flush=True)


def call_model(system_prompt, user_prompt, max_tokens=250):
    try:
        response = client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=0,
        )
        return response.choices[0].message.content.strip(), None
    except Exception as exc:
        return None, str(exc)


def get_preference_set(traveler_id):
    """Pull the traveller's whole profile from the database API in one call."""
    try:
        resp = requests.get(f"{DB_API_URL}/preference-set/{traveler_id}", timeout=5)
    except requests.RequestException:
        return None, "unavailable"
    if resp.status_code == 404:
        return None, "not found"
    if not resp.ok:
        return None, "unavailable"
    return resp.json(), None


def check_completeness(profile):
    """Deterministic validation that runs before trip planning is allowed.

    The AI explains this result - it never decides it.
    """
    traveler = profile["traveler"]
    gaps, present = [], []

    if traveler.get("home_location"):
        present.append("home location")
    else:
        gaps.append("a home location")

    if traveler.get("travel_style"):
        present.append("travel style")
    else:
        gaps.append("a travel style")

    if profile.get("preferences"):
        present.append("budget range and pace")
    else:
        gaps.append("a budget range and pace")

    if profile.get("interests"):
        present.append(f"{len(profile['interests'])} interests")
    else:
        gaps.append("at least one interest")

    if profile.get("accessibility_needs"):
        present.append("accessibility and dietary needs")
    else:
        gaps.append("accessibility and dietary needs (enter 'None' if not applicable)")

    score = round((5 - len(gaps)) / 5 * 100)
    return {
        "traveler_id": traveler["traveler_id"],
        "score": score,
        "ready_for_trip_planning": not gaps,
        "present": present,
        "gaps": gaps,
    }


def has_recorded_needs(profile):
    """A row saying "None" with no dietary restriction is not a real constraint."""
    for need in profile.get("accessibility_needs") or []:
        requirement = (need.get("requirement") or "").strip().lower()
        dietary = (need.get("dietary_restriction") or "").strip().lower()
        if (requirement and requirement != "none") or (dietary and dietary != "none"):
            return True
    return False


def review_summary(summary, profile):
    """OBSERVE stage: check the model's answer against the evidence it was given.

    Returns plain-language problems for the ADAPT re-prompt. Catching a dropped
    CONSTRAINTS line matters - a small model will happily answer "none recorded"
    for a traveller who has a real dietary or accessibility requirement.
    """
    issues = []
    upper = summary.upper()

    missing = [label for label in REQUIRED_LABELS if label not in upper]
    if missing:
        issues.append("it is missing these required lines: " + ", ".join(missing))

    lines = {}
    for line in summary.splitlines():
        for label in REQUIRED_LABELS:
            if line.strip().upper().startswith(label):
                lines[label] = line.split(":", 1)[1].strip()

    def says_nothing(text):
        lowered = (text or "").lower()
        return (not lowered) or "none" in lowered or "not recorded" in lowered

    if has_recorded_needs(profile) and says_nothing(lines.get("CONSTRAINTS:")):
        issues.append("CONSTRAINTS claims nothing is recorded, but this traveller "
                      "has accessibility or dietary needs that must be listed")
    if profile.get("interests") and says_nothing(lines.get("PRIORITIES:")):
        issues.append("PRIORITIES claims nothing is recorded, but this traveller "
                      "has interests that must be listed")
    if profile.get("preferences") and says_nothing(lines.get("BUDGET:")):
        issues.append("BUDGET does not state the stored budget range")

    return issues


def build_evidence(profile):
    traveler = profile["traveler"]
    preference = profile.get("preferences")
    interests = profile.get("interests") or []
    needs = profile.get("accessibility_needs") or []

    if preference:
        budget = (f"{preference['budget_min']:.0f}-{preference['budget_max']:.0f} "
                  f"{preference['currency']}")
        pace = preference["pace"]
    else:
        budget = "not set"
        pace = "not set"

    interest_text = ", ".join(
        f"{i['interest_category']} (priority {i['priority']})" for i in interests
    ) or "none recorded"

    need_text = ", ".join(
        f"{n['requirement']}"
        + (f" / dietary: {n['dietary_restriction']}" if n["dietary_restriction"] else "")
        for n in needs
    ) or "none recorded"

    return {
        "traveler": f"{traveler['name']} from {traveler['home_location']}",
        "style": traveler["travel_style"],
        "budget": budget,
        "pace": pace,
        "interests": interest_text,
        "needs": need_text,
    }


def resolve_traveler_id():
    """The frontend sends the picked traveller as a normal request parameter
    (hx-include on the picker), so read it from the query string or the form."""
    return (request.args.get("traveler_id", type=int)
            or request.form.get("traveler_id", type=int))


# ------------------------------------------------------------------ read views
def render_profile(traveler_id):
    """The profile panel HTMX swaps in. Also the response to every write, so
    one round trip both saves and refreshes the view."""
    profile, err = get_preference_set(traveler_id)
    if err == "not found":
        return f"<p class='error'>Traveler {traveler_id} not found.</p>", 404
    if err:
        return "<p class='error'>Preferences database service is unavailable.</p>", 503

    traveler = profile["traveler"]
    preference = profile.get("preferences")
    interests = profile.get("interests") or []
    needs = profile.get("accessibility_needs") or []

    if preference:
        budget_html = (
            f"<p>Budget: {preference['budget_min']:.0f} - {preference['budget_max']:.0f} "
            f"{escape(preference['currency'])} &middot; Pace: {escape(preference['pace'])}"
            f" <button hx-post='/api/preferences/{traveler_id}/delete' "
            "hx-target='#profile'>Clear</button></p>"
        )
    else:
        budget_html = "<p class='muted'>No budget range saved yet.</p>"

    interest_rows = ""
    for i in interests:
        interest_rows += (
            "<tr>"
            f"<td>{escape(i['interest_category'])}</td>"
            f"<td>{i['priority']}</td>"
            "<td>"
            f"<button hx-get='/api/interests/{i['interest_id']}/edit' "
            "hx-target='#edit-form'>Edit</button> "
            f"<form hx-post='/api/interests/{i['interest_id']}/delete' "
            "hx-target='#profile' style='display:inline'>"
            f"<input type='hidden' name='traveler_id' value='{traveler_id}'>"
            "<button type='submit'>Delete</button></form>"
            "</td></tr>"
        )
    if not interest_rows:
        interest_rows = "<tr><td colspan='3' class='muted'>No interests yet.</td></tr>"

    need_rows = ""
    for n in needs:
        dietary = n["dietary_restriction"] or "-"
        need_rows += (
            "<tr>"
            f"<td>{escape(n['requirement'])}</td>"
            f"<td>{escape(dietary)}</td>"
            "<td>"
            f"<button hx-get='/api/accessibility-needs/{n['need_id']}/edit' "
            "hx-target='#edit-form'>Edit</button> "
            f"<form hx-post='/api/accessibility-needs/{n['need_id']}/delete' "
            "hx-target='#profile' style='display:inline'>"
            f"<input type='hidden' name='traveler_id' value='{traveler_id}'>"
            "<button type='submit'>Delete</button></form>"
            "</td></tr>"
        )
    if not need_rows:
        need_rows = "<tr><td colspan='3' class='muted'>No needs recorded.</td></tr>"

    return f"""
    <h3>{escape(traveler['name'])}</h3>
    <p>{escape(traveler['email'])} &middot; {escape(traveler['home_location'])}
       &middot; {escape(traveler['travel_style'])} traveller</p>
    {budget_html}
    <h4>Interests</h4>
    <table>
      <tr><th>Category</th><th>Priority</th><th></th></tr>
      {interest_rows}
    </table>
    <h4>Accessibility and dietary needs</h4>
    <table>
      <tr><th>Requirement</th><th>Dietary</th><th></th></tr>
      {need_rows}
    </table>
    """


@app.route("/profile/<int:traveler_id>")
def profile(traveler_id):
    return render_profile(traveler_id)


@app.route("/profile")
def profile_for_picked_traveler():
    traveler_id = resolve_traveler_id()
    if not traveler_id:
        return "<p class='error'>Select a traveller first.</p>", 400
    return render_profile(traveler_id)


@app.route("/travelers")
def traveler_options():
    """Populates the traveller picker on the frontend."""
    try:
        travelers = requests.get(f"{DB_API_URL}/travelers", timeout=5).json()
    except requests.RequestException:
        return "<option>Database unavailable</option>", 503
    options = ""
    for t in travelers:
        options += f"<option value='{t['traveler_id']}'>{escape(t['name'])}</option>"
    return options


# --------------------------------------------------------------- traveler CRUD
@app.route("/travelers", methods=["POST"])
def add_traveler():
    form = request.form
    payload = {
        "name": form.get("name", "").strip(),
        "email": form.get("email", "").strip(),
        "home_location": form.get("home_location", "").strip(),
        "travel_style": form.get("travel_style", "mid-range"),
    }
    if not payload["name"] or not payload["email"] or not payload["home_location"]:
        return "<p class='error'>Name, email and home location are required.</p>", 400
    try:
        resp = requests.post(f"{DB_API_URL}/travelers", json=payload, timeout=5)
    except requests.RequestException:
        return "<p class='error'>Could not save the traveller.</p>", 503
    if not resp.ok:
        message = resp.json().get("error", "the traveller could not be saved")
        return f"<p class='error'>{escape(message)}</p>", resp.status_code
    return render_profile(resp.json()["traveler_id"])


@app.route("/travelers/edit")
def edit_picked_traveler_form():
    traveler_id = resolve_traveler_id()
    if not traveler_id:
        return "<p class='error'>Select a traveller first.</p>", 400
    return edit_traveler_form(traveler_id)


@app.route("/travelers/<int:traveler_id>/edit")
def edit_traveler_form(traveler_id):
    try:
        traveler = requests.get(f"{DB_API_URL}/travelers/{traveler_id}", timeout=5).json()
    except requests.RequestException:
        return "<p class='error'>Preferences database service is unavailable.</p>", 503
    if "error" in traveler:
        return "<p class='error'>Traveler not found.</p>", 404

    options = ""
    for style in ("budget", "mid-range", "luxury"):
        selected = " selected" if style == traveler["travel_style"] else ""
        options += f"<option value='{style}'{selected}>{style}</option>"

    return f"""
    <h4>Edit traveller {traveler_id}</h4>
    <form hx-post="/api/travelers/{traveler_id}/update" hx-target="#profile">
        <label>Name <input name="name" value="{escape(traveler['name'])}" required></label>
        <label>Email
            <input name="email" type="email" value="{escape(traveler['email'])}" required></label>
        <label>Home location
            <input name="home_location" value="{escape(traveler['home_location'])}" required></label>
        <label>Travel style <select name="travel_style">{options}</select></label>
        <button type="submit">Update traveller</button>
    </form>
    """


@app.route("/travelers/<int:traveler_id>/update", methods=["POST"])
def update_traveler(traveler_id):
    form = request.form
    payload = {
        "name": form.get("name", "").strip(),
        "email": form.get("email", "").strip(),
        "home_location": form.get("home_location", "").strip(),
        "travel_style": form.get("travel_style", "mid-range"),
    }
    if not payload["name"] or not payload["email"] or not payload["home_location"]:
        return "<p class='error'>Name, email and home location are required.</p>", 400
    try:
        resp = requests.put(
            f"{DB_API_URL}/travelers/{traveler_id}", json=payload, timeout=5
        )
    except requests.RequestException:
        return "<p class='error'>Could not update the traveller.</p>", 503
    if not resp.ok:
        message = resp.json().get("error", "the traveller could not be updated")
        return f"<p class='error'>{escape(message)}</p>", resp.status_code
    return render_profile(traveler_id)


@app.route("/travelers/<int:traveler_id>/delete", methods=["POST"])
def delete_traveler(traveler_id):
    try:
        requests.delete(f"{DB_API_URL}/travelers/{traveler_id}", timeout=5)
    except requests.RequestException:
        return "<p class='error'>Could not delete the traveller.</p>", 503
    return f"<p>Traveler {traveler_id} and their preferences were deleted.</p>"


# ------------------------------------------------------------- preference CRUD
@app.route("/preferences", methods=["POST"])
def save_preferences():
    form = request.form
    payload = {
        "traveler_id": form.get("traveler_id", type=int),
        "budget_min": form.get("budget_min", type=float),
        "budget_max": form.get("budget_max", type=float),
        "pace": form.get("pace", "balanced"),
        "currency": form.get("currency", "AUD"),
    }
    if payload["budget_min"] is None or payload["budget_max"] is None:
        return "<p class='error'>A minimum and maximum budget are required.</p>", 400
    if payload["budget_max"] < payload["budget_min"]:
        return "<p class='error'>Maximum budget must be at least the minimum.</p>", 400
    try:
        resp = requests.post(f"{DB_API_URL}/preferences", json=payload, timeout=5)
    except requests.RequestException:
        return "<p class='error'>Could not save the preferences.</p>", 503
    if not resp.ok:
        message = resp.json().get("error", "the preferences could not be saved")
        return f"<p class='error'>{escape(message)}</p>", resp.status_code
    return render_profile(payload["traveler_id"])


@app.route("/preferences/<int:traveler_id>/delete", methods=["POST"])
def clear_preferences(traveler_id):
    try:
        requests.delete(f"{DB_API_URL}/preferences/{traveler_id}", timeout=5)
    except requests.RequestException:
        return "<p class='error'>Could not clear the preferences.</p>", 503
    return render_profile(traveler_id)


# --------------------------------------------------------------- interest CRUD
@app.route("/interests", methods=["POST"])
def add_interest():
    form = request.form
    traveler_id = form.get("traveler_id", type=int)
    payload = {
        "traveler_id": traveler_id,
        "interest_category": form.get("interest_category", "").strip(),
        "priority": form.get("priority", type=int) or 3,
    }
    if not payload["interest_category"]:
        return "<p class='error'>An interest category is required.</p>", 400
    try:
        resp = requests.post(f"{DB_API_URL}/interests", json=payload, timeout=5)
    except requests.RequestException:
        return "<p class='error'>Could not save the interest.</p>", 503
    if not resp.ok:
        message = resp.json().get("error", "the interest could not be saved")
        return f"<p class='error'>{escape(message)}</p>", resp.status_code
    return render_profile(traveler_id)


@app.route("/interests/<int:interest_id>/edit")
def edit_interest_form(interest_id):
    try:
        interest = requests.get(f"{DB_API_URL}/interests/{interest_id}", timeout=5).json()
    except requests.RequestException:
        return "<p class='error'>Preferences database service is unavailable.</p>", 503
    if "error" in interest:
        return "<p class='error'>Interest not found.</p>", 404

    options = ""
    for value in (1, 2, 3, 4, 5):
        selected = " selected" if value == interest["priority"] else ""
        options += f"<option value='{value}'{selected}>{value}</option>"

    return f"""
    <h4>Edit interest {interest_id}</h4>
    <form hx-post="/api/interests/{interest_id}/update" hx-target="#profile">
        <input type="hidden" name="traveler_id" value="{interest['traveler_id']}">
        <label>Category
            <input name="interest_category"
                   value="{escape(interest['interest_category'])}" required></label>
        <label>Priority (5 = highest)
            <select name="priority">{options}</select></label>
        <button type="submit">Update interest</button>
    </form>
    """


@app.route("/interests/<int:interest_id>/update", methods=["POST"])
def update_interest(interest_id):
    form = request.form
    traveler_id = form.get("traveler_id", type=int)
    payload = {
        "interest_category": form.get("interest_category", "").strip(),
        "priority": form.get("priority", type=int) or 3,
    }
    if not payload["interest_category"]:
        return "<p class='error'>An interest category is required.</p>", 400
    try:
        resp = requests.put(
            f"{DB_API_URL}/interests/{interest_id}", json=payload, timeout=5
        )
    except requests.RequestException:
        return "<p class='error'>Could not update the interest.</p>", 503
    if not resp.ok:
        message = resp.json().get("error", "the interest could not be updated")
        return f"<p class='error'>{escape(message)}</p>", resp.status_code
    return render_profile(traveler_id)


@app.route("/interests/<int:interest_id>/delete", methods=["POST"])
def remove_interest(interest_id):
    traveler_id = request.form.get("traveler_id", type=int)
    try:
        requests.delete(f"{DB_API_URL}/interests/{interest_id}", timeout=5)
    except requests.RequestException:
        return "<p class='error'>Could not delete the interest.</p>", 503
    return render_profile(traveler_id)


# ---------------------------------------------------- accessibility needs CRUD
@app.route("/accessibility-needs", methods=["POST"])
def add_need():
    form = request.form
    traveler_id = form.get("traveler_id", type=int)
    payload = {
        "traveler_id": traveler_id,
        "requirement": form.get("requirement", "").strip(),
        "dietary_restriction": form.get("dietary_restriction", "").strip(),
    }
    if not payload["requirement"]:
        return "<p class='error'>A requirement is required (enter 'None' if not applicable).</p>", 400
    try:
        resp = requests.post(f"{DB_API_URL}/accessibility-needs", json=payload, timeout=5)
    except requests.RequestException:
        return "<p class='error'>Could not save the requirement.</p>", 503
    if not resp.ok:
        message = resp.json().get("error", "the requirement could not be saved")
        return f"<p class='error'>{escape(message)}</p>", resp.status_code
    return render_profile(traveler_id)


@app.route("/accessibility-needs/<int:need_id>/edit")
def edit_need_form(need_id):
    try:
        need = requests.get(
            f"{DB_API_URL}/accessibility-needs/{need_id}", timeout=5
        ).json()
    except requests.RequestException:
        return "<p class='error'>Preferences database service is unavailable.</p>", 503
    if "error" in need:
        return "<p class='error'>Requirement not found.</p>", 404

    dietary = need["dietary_restriction"] or ""
    return f"""
    <h4>Edit requirement {need_id}</h4>
    <form hx-post="/api/accessibility-needs/{need_id}/update" hx-target="#profile">
        <input type="hidden" name="traveler_id" value="{need['traveler_id']}">
        <label>Requirement
            <input name="requirement" value="{escape(need['requirement'])}" required></label>
        <label>Dietary restriction
            <input name="dietary_restriction" value="{escape(dietary)}"></label>
        <button type="submit">Update requirement</button>
    </form>
    """


@app.route("/accessibility-needs/<int:need_id>/update", methods=["POST"])
def update_need(need_id):
    form = request.form
    traveler_id = form.get("traveler_id", type=int)
    payload = {
        "requirement": form.get("requirement", "").strip(),
        "dietary_restriction": form.get("dietary_restriction", "").strip(),
    }
    if not payload["requirement"]:
        return "<p class='error'>A requirement is required.</p>", 400
    try:
        resp = requests.put(
            f"{DB_API_URL}/accessibility-needs/{need_id}", json=payload, timeout=5
        )
    except requests.RequestException:
        return "<p class='error'>Could not update the requirement.</p>", 503
    if not resp.ok:
        message = resp.json().get("error", "the requirement could not be updated")
        return f"<p class='error'>{escape(message)}</p>", resp.status_code
    return render_profile(traveler_id)


@app.route("/accessibility-needs/<int:need_id>/delete", methods=["POST"])
def remove_need(need_id):
    traveler_id = request.form.get("traveler_id", type=int)
    try:
        requests.delete(f"{DB_API_URL}/accessibility-needs/{need_id}", timeout=5)
    except requests.RequestException:
        return "<p class='error'>Could not delete the requirement.</p>", 503
    return render_profile(traveler_id)


# --------------------------------------------------------------- AI: summarise
@app.route("/summarise", methods=["POST"])
def summarise_picked_traveler():
    traveler_id = resolve_traveler_id()
    if not traveler_id:
        return "<p class='error'>Select a traveller first.</p>", 400
    return summarise(traveler_id)


@app.route("/summarise/<int:traveler_id>", methods=["POST"])
def summarise(traveler_id):
    """Plan -> Act -> Observe -> Adapt.

    PLAN    decide what evidence the preference set needs
    ACT     fetch that evidence and ask the LLM for the structured summary
    OBSERVE check the answer actually carries all four required labels
    ADAPT   re-prompt once, naming the labels that were missing
    """
    if not AI_MODE_ENABLED:
        return "<p class='muted'>AI-Mode is disabled in this environment.</p>", 503

    log_stage("PLAN", f"Summarise traveler {traveler_id}: need profile, budget, "
                      "interests and accessibility needs from the database API.")

    profile, err = get_preference_set(traveler_id)
    if err == "not found":
        return f"<p class='error'>Traveler {traveler_id} not found.</p>", 404
    if err:
        return "<p class='error'>Preferences database service is unavailable.</p>", 503

    evidence = build_evidence(profile)
    log_stage("ACT", f"Retrieved profile for {evidence['traveler']}; "
                     f"calling {OLLAMA_MODEL} for the structured preference set.")

    system_prompt = load_prompt("preferences_system_prompt.txt")
    task_prompt = (
        load_prompt("preferences_task_prompt.txt")
        .replace("{{TRAVELER}}", evidence["traveler"])
        .replace("{{STYLE}}", evidence["style"])
        .replace("{{BUDGET}}", evidence["budget"])
        .replace("{{PACE}}", evidence["pace"])
        .replace("{{INTERESTS}}", evidence["interests"])
        .replace("{{NEEDS}}", evidence["needs"])
    )

    summary, ai_error = call_model(system_prompt, task_prompt)
    if ai_error:
        log_stage("OBSERVE", f"Model call failed: {ai_error}")
        return (
            "<p class='error'>AI summary failed. Check that Ollama is running.</p>"
            f"<pre>{escape(ai_error)}</pre>",
            503,
        )

    issues = review_summary(summary, profile)
    log_stage("OBSERVE", f"Model returned {len(summary)} characters; "
                         f"issues found: {len(issues)}"
                         + (" (" + "; ".join(issues) + ")" if issues else ""))

    adapted = False
    if issues:
        log_stage("ADAPT", "Re-prompting once with the rejected answer's faults named.")
        adapt_prompt = (
            load_prompt("adapt_task_prompt.txt")
            .replace("{{ISSUES}}", "\n".join(f"- {i}" for i in issues))
            .replace("{{EVIDENCE}}", task_prompt)
        )
        retry, retry_error = call_model(system_prompt, adapt_prompt)
        if retry and not retry_error:
            retry_issues = review_summary(retry, profile)
            # Only keep the retry when it is genuinely better than the first answer.
            if len(retry_issues) < len(issues):
                summary, issues, adapted = retry, retry_issues, True
            log_stage("OBSERVE", f"After adapt, issues: {len(retry_issues)}. "
                                 f"Retry {'accepted' if adapted else 'discarded'}.")
        else:
            log_stage("OBSERVE", f"Retry failed: {retry_error}")
    else:
        log_stage("ADAPT", "Answer accepted on the first attempt, no retry needed.")

    note = ""
    if adapted:
        note = ("<p class='muted'>The first response did not match the stored "
                "profile, so the agent re-prompted itself once.</p>")
    if issues:
        note += ("<p class='error'>The model still did not reproduce the profile "
                 "faithfully. Shown as returned, for human review.</p>")

    # Small models append stray sentences and sometimes repeat the whole block,
    # so show the first line for each label, in the order the prompt asked for.
    first_seen = {}
    for line in summary.splitlines():
        text = line.strip()
        for label in REQUIRED_LABELS:
            if text.upper().startswith(label) and label not in first_seen:
                first_seen[label] = text
    labelled = [first_seen[label] for label in REQUIRED_LABELS if label in first_seen]
    shown = labelled or [line.strip() for line in summary.splitlines() if line.strip()]
    lines = "".join(f"<p>{escape(line)}</p>" for line in shown)
    return f"<div>{lines}{note}</div>"


# ------------------------------------------------------------ AI: completeness
@app.route("/completeness", methods=["POST"])
def completeness_for_picked_traveler():
    traveler_id = resolve_traveler_id()
    if not traveler_id:
        return "<p class='error'>Select a traveller first.</p>", 400
    return completeness(traveler_id)


@app.route("/completeness/<int:traveler_id>", methods=["POST"])
def completeness(traveler_id):
    """Deterministic validation first, then an AI explanation of the gaps."""
    log_stage("PLAN", f"Check whether traveler {traveler_id} is ready for trip planning.")

    profile, err = get_preference_set(traveler_id)
    if err == "not found":
        return f"<p class='error'>Traveler {traveler_id} not found.</p>", 404
    if err:
        return "<p class='error'>Preferences database service is unavailable.</p>", 503

    result = check_completeness(profile)
    log_stage("ACT", f"Deterministic check scored {result['score']}% "
                     f"with {len(result['gaps'])} gap(s).")

    system_prompt = load_prompt("completeness_system_prompt.txt")
    task_prompt = (
        load_prompt("completeness_task_prompt.txt")
        .replace("{{TRAVELER}}", profile["traveler"]["name"])
        .replace("{{SCORE}}", str(result["score"]))
        .replace("{{PRESENT}}", ", ".join(result["present"]) or "nothing yet")
        .replace("{{GAPS}}", "; ".join(result["gaps"]) or "none")
    )

    if AI_MODE_ENABLED:
        advice, ai_error = call_model(system_prompt, task_prompt, max_tokens=180)
    else:
        advice, ai_error = None, "AI-Mode is disabled in this environment"
    if ai_error:
        log_stage("OBSERVE", f"Model call failed: {ai_error}")
        advice = None
    else:
        log_stage("OBSERVE", "Model explained the gaps to the traveller.")

    status = ("Ready for trip planning."
              if result["ready_for_trip_planning"]
              else "Not ready for trip planning yet.")
    log_stage("ADAPT", f"Reported to the traveller: {status}")

    gap_items = "".join(f"<li>{escape(g)}</li>" for g in result["gaps"])
    gap_html = f"<p>Still missing:</p><ul>{gap_items}</ul>" if gap_items else ""
    if advice:
        advice_html = f"<p>{escape(advice)}</p>"
    elif not AI_MODE_ENABLED:
        advice_html = ("<p class='muted'>AI-Mode is disabled in this environment. "
                       "The score above is still valid.</p>")
    else:
        advice_html = ("<p class='error'>AI explanation unavailable - check that "
                       "Ollama is running. The score above is still valid.</p>")

    return f"""
    <div>
      <p><strong>{result['score']}% complete.</strong> {status}</p>
      {gap_html}
      {advice_html}
    </div>
    """


# ------------------------------------------------------------ shared MCP tools
@app.route("/mcp/tool", methods=["POST"])
def run_mcp_tool():
    """Frontend -> this backend -> shared MCP HTTP server -> tools.py and back.

    Accepts form data (HTMX) or JSON: tool_name and traveler_id.
    """
    data = request.get_json(silent=True) or request.form
    tool_name = data.get("tool_name", "")
    try:
        traveler_id = int(data.get("traveler_id", ""))
    except (TypeError, ValueError):
        traveler_id = 0

    if tool_name not in MCP_TOOLS:
        return f"<p class='error'>Unknown MCP tool: {escape(tool_name)}</p>", 400
    if traveler_id < 1:
        return "<p class='error'>Select a traveller first.</p>", 400
    if not MCP_ENABLED:
        return "<p class='muted'>MCP is disabled in this environment.</p>", 503

    log_stage("MCP", f"Calling shared MCP tool {tool_name} for traveler {traveler_id}.")
    try:
        resp = requests.post(
            f"{MCP_BASE_URL}/mcp/tool",
            json={"tool_name": tool_name, "arguments": {"traveler_id": traveler_id}},
            timeout=15,
        )
        payload = resp.json()
    except (requests.RequestException, ValueError):
        return ("<p class='error'>The shared MCP server is unavailable. "
                "Start it with python3 ai-services/mcp-server/http_server.py.</p>"), 503

    if not payload.get("ok"):
        return ("<p class='error'>MCP tool failed.</p>"
                f"<pre>{escape(payload.get('error', 'unknown error'))}</pre>"), 502

    result = payload["result"]
    log_stage("MCP", f"{tool_name} returned {len(json.dumps(result))} bytes.")
    error_html = f"<p class='error'>{escape(result['error'])}</p>" if result.get("error") else ""
    return f"""
    <div>
      <p><strong>{escape(MCP_TOOLS[tool_name])}</strong>
         <span class='muted'>&middot; shared MCP tool <code>{escape(tool_name)}</code></span></p>
      {error_html}
      <pre>{escape(json.dumps(result, indent=2))}</pre>
    </div>
    """


# ------------------------------------------------------------- shared RAG Q&A
INSUFFICIENT_CONTEXT_HTML = (
    "<p><strong>Insufficient context.</strong> The project data does not contain "
    "enough evidence to answer this, so no answer was generated.</p>"
)


@app.route("/rag/ask", methods=["POST"])
def rag_ask():
    """Frontend -> this backend -> shared RAG server /rag/answer and back.

    Only shows an answer that is grounded: it must cite at least one
    retrieved chunk. Anything else is reported as insufficient context.
    """
    data = request.get_json(silent=True) or request.form
    question = (data.get("question") or "").strip()

    if not question:
        return "<p class='error'>Type a question first.</p>", 400
    if len(question) > RAG_MAX_QUESTION:
        return (f"<p class='error'>Questions are limited to {RAG_MAX_QUESTION} "
                "characters.</p>"), 400
    if not RAG_ENABLED:
        return "<p class='muted'>RAG is disabled in this environment.</p>", 503

    log_stage("RAG", f"Asking shared RAG server: {question!r}")
    try:
        resp = requests.post(f"{RAG_BASE_URL}/rag/answer",
                             json={"query": question, "k": 5}, timeout=170)
        payload = resp.json()
    except (requests.RequestException, ValueError):
        return ("<p class='error'>The shared RAG server is unavailable. "
                "Start it with python rag-server/rag_http_server.py.</p>"), 503

    if payload.get("status") != "success":
        return ("<p class='error'>The RAG server could not answer.</p>"
                f"<pre>{escape(payload.get('error', 'unknown error'))}</pre>"), 502

    answer = (payload.get("answer") or "").strip()
    citations = payload.get("citations") or []
    confidence = payload.get("confidence_category") or "Unknown"
    retrieved = (payload.get("retrieval_summary") or {}).get("retrieved_count", 0)

    if answer.lower().rstrip(".") == "insufficient evidence" or not citations:
        log_stage("RAG", f"Insufficient context ({retrieved} chunks retrieved, none cited).")
        return f"""
        <div>
          {INSUFFICIENT_CONTEXT_HTML}
          <p class='muted'>Confidence: Unknown &middot; {retrieved} chunks retrieved, none supported an answer.</p>
        </div>
        """

    log_stage("RAG", f"Grounded answer, confidence {confidence}, {len(citations)} citation(s).")
    citation_items = "".join(
        f"<li><code>{escape(c.get('chunk_id', ''))}</code> "
        f"<span class='muted'>from {escape(c.get('source_id', ''))}</span></li>"
        for c in citations
    )
    return f"""
    <div>
      <p>{escape(answer)}</p>
      <p><strong>Confidence:</strong> {escape(confidence)}</p>
      <p><strong>Sources:</strong></p>
      <ul>{citation_items}</ul>
    </div>
    """


# ------------------------------------------------- Release 2: shared Multi-Agent
# Frontend -> this backend -> shared Multi-Agent server:
#   Planner (what to check) -> Worker (answer from the supplied preference set)
#   -> Reviewer (check the answer against that evidence) -> Human Review here.
# The shared server only analyses the evidence sent to it; a recorded decision
# never changes the traveller's data.
def multi_agent_disabled():
    return ("<p class='muted'>Multi-Agent mode is disabled in this environment.</p>",
            503)


def multi_agent_context(profile):
    """The evidence the agents work from: the stored preference set plus the
    deterministic completeness verdict. The email address is left out because
    no review task needs it."""
    traveler = profile["traveler"]
    return {
        "traveler": {
            "traveler_id": traveler["traveler_id"],
            "name": traveler["name"],
            "home_location": traveler["home_location"],
            "travel_style": traveler["travel_style"],
        },
        "preferences": profile.get("preferences"),
        "interests": [
            {"interest_category": i["interest_category"], "priority": i["priority"]}
            for i in profile.get("interests") or []
        ],
        "accessibility_needs": [
            {"requirement": n["requirement"],
             "dietary_restriction": n["dietary_restriction"]}
            for n in profile.get("accessibility_needs") or []
        ],
        "completeness": check_completeness(profile),
    }


def multi_agent_request(traveler_id, user_request=""):
    """Builds the shared server's POST /workflow body for one traveller.
    Returns (body, None) or (None, (message, status))."""
    profile, err = get_preference_set(traveler_id)
    if err == "not found":
        return None, (f"Traveler {traveler_id} not found.", 404)
    if err:
        return None, ("Preferences database service is unavailable.", 503)
    return {
        "service": MULTI_AGENT_SERVICE,
        "task": MULTI_AGENT_TASK,
        "user_request": user_request or DEFAULT_REVIEW_REQUEST,
        "context": multi_agent_context(profile),
    }, None


def call_multi_agent(method, path, payload=None):
    """One call to the shared server. Returns (json, None) or (None, (message, status))."""
    url = f"{MULTI_AGENT_SERVICE_URL}{path}"
    try:
        if method == "POST":
            resp = requests.post(url, json=payload, timeout=MULTI_AGENT_TIMEOUT_SECONDS)
        else:
            resp = requests.get(url, timeout=MULTI_AGENT_TIMEOUT_SECONDS)
    except requests.Timeout:
        return None, ("The shared Multi-Agent server did not answer within "
                      f"{MULTI_AGENT_TIMEOUT_SECONDS} seconds.", 504)
    except requests.RequestException:
        return None, ("The shared Multi-Agent server is unavailable. Start it with "
                      "python ai-services/multi-agent-server/app.py.", 503)
    try:
        data = resp.json()
    except ValueError:
        return None, ("The shared Multi-Agent server returned a non-JSON response.", 502)
    if not resp.ok:
        status = resp.status_code if resp.status_code in (400, 404) else 502
        return None, (data.get("error", "the Multi-Agent request failed"), status)
    return data, None


def valid_workflow_id(workflow_id):
    """Only well-formed IDs are forwarded to the shared server."""
    try:
        return str(uuid.UUID(workflow_id)) == workflow_id.lower()
    except (ValueError, AttributeError):
        return False


def is_own_workflow(workflow):
    """The shared server keeps every student's history together, so only
    workflows this feature started are shown or reviewed here."""
    return (workflow.get("service") == MULTI_AGENT_SERVICE
            and workflow.get("task") == MULTI_AGENT_TASK)


def agent_card(number, title, result, text_key):
    result = result or {}
    status = result.get("status", "unknown")
    status_class = "" if status == "success" else " error"
    error = (f"<p class='error'>{escape(result['error'])}</p>"
             if result.get("error") else "")
    return f"""
    <div class='ma-stage'>
      <h4>{number}. {title}
        <span class='muted{status_class}'>&middot; {escape(status)}
        &middot; {escape(result.get('model', ''))}</span></h4>
      <div class='ma-text'>{escape(result.get(text_key, ''))}</div>
      {error}
    </div>
    """


def render_workflow(workflow, notice=""):
    workflow_id = workflow.get("workflow_id", "")
    decision = workflow.get("human_decision") or {}
    traveler = (workflow.get("context") or {}).get("traveler") or {}

    if decision.get("status") == "recorded":
        evidence = (f"<p><strong>Evidence:</strong> {escape(decision['evidence'])}</p>"
                    if decision.get("evidence") else "")
        human_html = f"""
        <div class='ma-stage'>
          <h4>4. Human review <span class='muted'>&middot; recorded</span></h4>
          <p><strong>{escape(decision.get('decision', ''))}</strong>
             <span class='muted'>&middot; {escape(decision.get('timestamp', ''))}</span></p>
          <p>{escape(decision.get('reason', ''))}</p>
          {evidence}
        </div>
        """
    else:
        radios = "".join(
            f"<label class='ma-choice'><input type='radio' name='decision' "
            f"value='{value}' required> {value}</label>"
            for value in REVIEW_DECISIONS
        )
        human_html = f"""
        <div class='ma-stage'>
          <h4>4. Human review <span class='muted'>&middot; pending</span></h4>
          <form hx-post='/api/multi-agent/workflows/{escape(workflow_id)}/review'
                hx-target='#ma-workflow' hx-indicator='#ma-loading'>
            <fieldset><legend>Decision</legend>{radios}</fieldset>
            <label>Reason or correction (at least {REVIEW_MIN_REASON} characters)
              <textarea name='reason' minlength='{REVIEW_MIN_REASON}' rows='3'
                        required></textarea></label>
            <label>Evidence checked (optional)
              <input name='evidence' placeholder='Profile, interests and needs tables'></label>
            <button type='submit' class='primary-button'>Record decision</button>
          </form>
        </div>
        """

    return f"""
    <div>
      {notice}
      <p class='muted'>Workflow <code>{escape(workflow_id)}</code>
         &middot; traveller {escape(traveler.get('traveler_id', ''))}
         {escape(traveler.get('name', ''))}
         &middot; {escape(workflow.get('status', ''))}
         &middot; {escape(workflow.get('duration_ms', ''))} ms</p>
      <p><strong>Request:</strong> {escape(workflow.get('user_request', ''))}</p>
      {agent_card(1, "Planner", workflow.get("planner_result"), "plan")}
      {agent_card(2, "Worker", workflow.get("worker_result"), "output")}
      {agent_card(3, "Reviewer", workflow.get("reviewer_result"), "review")}
      {human_html}
    </div>
    """


def error_fragment(err):
    message, status = err
    return f"<p class='error'>{escape(message)}</p>", status


@app.route("/multi-agent/evidence/<int:traveler_id>")
def multi_agent_evidence(traveler_id):
    """JSON body this feature sends to the shared server. Used by the
    terminal client (tools/preferences_review_cli.py)."""
    if not MULTI_AGENT_ENABLED:
        return jsonify({"error": "Multi-Agent mode is disabled in this environment"}), 503
    body, err = multi_agent_request(traveler_id, request.args.get("user_request", "").strip())
    if err:
        return jsonify({"error": err[0]}), err[1]
    return jsonify(body)


@app.route("/multi-agent/workflow", methods=["POST"])
def multi_agent_start():
    if not MULTI_AGENT_ENABLED:
        return multi_agent_disabled()
    data = request.get_json(silent=True) or request.form
    try:
        traveler_id = int(data.get("traveler_id", ""))
    except (TypeError, ValueError):
        traveler_id = 0
    user_request = str(data.get("user_request") or "").strip()
    if traveler_id < 1:
        return "<p class='error'>Select a traveller first.</p>", 400
    if len(user_request) > MULTI_AGENT_MAX_REQUEST:
        return (f"<p class='error'>Requests are limited to {MULTI_AGENT_MAX_REQUEST} "
                "characters.</p>"), 400

    log_stage("MULTI-AGENT", f"PLAN: traveller {traveler_id} - send the preference set "
                             "to the shared Planner, Worker and Reviewer agents.")
    body, err = multi_agent_request(traveler_id, user_request)
    if err:
        return error_fragment(err)

    log_stage("MULTI-AGENT", f"ACT: POST {MULTI_AGENT_SERVICE_URL}/workflow "
                             f"(service={MULTI_AGENT_SERVICE}, task={MULTI_AGENT_TASK}).")
    workflow, err = call_multi_agent("POST", "/workflow", body)
    if err:
        log_stage("MULTI-AGENT", f"OBSERVE: failed - {err[0]}")
        return error_fragment(err)

    log_stage("MULTI-AGENT", f"OBSERVE: workflow {workflow.get('workflow_id')} "
                             f"{workflow.get('status')}; planner="
                             f"{(workflow.get('planner_result') or {}).get('status')}, "
                             f"worker={(workflow.get('worker_result') or {}).get('status')}, "
                             f"reviewer={(workflow.get('reviewer_result') or {}).get('status')}.")
    log_stage("MULTI-AGENT", "ADAPT: waiting for the human decision.")
    return render_workflow(workflow)


@app.route("/multi-agent/lookup")
def multi_agent_lookup_form():
    """The frontend's "Load workflow" box sends the ID as a query parameter."""
    return multi_agent_lookup(request.args.get("workflow_id", "").strip())


@app.route("/multi-agent/workflows/<workflow_id>")
def multi_agent_lookup(workflow_id):
    if not MULTI_AGENT_ENABLED:
        return multi_agent_disabled()
    if not valid_workflow_id(workflow_id):
        return "<p class='error'>Invalid workflow ID.</p>", 400
    workflow, err = call_multi_agent("GET", f"/workflow/{workflow_id}")
    if err:
        return error_fragment(err)
    if not is_own_workflow(workflow):
        return "<p class='error'>Workflow not found.</p>", 404
    return render_workflow(workflow)


@app.route("/multi-agent/workflows/<workflow_id>/review", methods=["POST"])
def multi_agent_review(workflow_id):
    if not MULTI_AGENT_ENABLED:
        return multi_agent_disabled()
    if not valid_workflow_id(workflow_id):
        return "<p class='error'>Invalid workflow ID.</p>", 400

    data = request.get_json(silent=True) or request.form
    decision = str(data.get("decision") or "").strip()
    reason = str(data.get("reason") or "").strip()
    evidence = str(data.get("evidence") or "").strip()
    if decision not in REVIEW_DECISIONS:
        return "<p class='error'>Choose Accept, Partially Accept or Reject.</p>", 400
    if len(reason) < REVIEW_MIN_REASON:
        return (f"<p class='error'>Give a reason of at least {REVIEW_MIN_REASON} "
                "characters.</p>"), 400

    existing, err = call_multi_agent("GET", f"/workflow/{workflow_id}")
    if err:
        return error_fragment(err)
    if not is_own_workflow(existing):
        return "<p class='error'>Workflow not found.</p>", 404

    workflow, err = call_multi_agent("POST", f"/workflow/{workflow_id}/review",
                                     {"decision": decision, "reason": reason,
                                      "evidence": evidence})
    if err:
        return error_fragment(err)
    log_stage("MULTI-AGENT", f"HUMAN REVIEW: {decision} recorded for workflow {workflow_id}.")
    notice = "<p class='success'>Decision recorded by the shared Multi-Agent server.</p>"
    return render_workflow(workflow, notice)


# ------------------------------------------------------- cross-feature contract
@app.route("/preference-set/<int:traveler_id>")
def preference_set(traveler_id):
    """JSON contract for the other teams' backends (Trip Planning, Booking,
    Budget). Includes the completeness verdict so a caller can refuse to plan
    a trip for an incomplete profile.
    """
    profile, err = get_preference_set(traveler_id)
    if err == "not found":
        return jsonify({"error": "traveler not found"}), 404
    if err:
        return jsonify({"error": "preferences database unavailable"}), 503
    profile["completeness"] = check_completeness(profile)
    return jsonify(profile)


@app.route("/health")
def health():
    return jsonify({"service": "student-1-backend", "model": OLLAMA_MODEL,
                    "ai_mode_enabled": AI_MODE_ENABLED,
                    "mcp_enabled": MCP_ENABLED, "rag_enabled": RAG_ENABLED,
                    "multi_agent_enabled": MULTI_AGENT_ENABLED,
                    "status": "ok"})


if __name__ == "__main__":
    # Direct runs listen on 127.0.0.1 with the debugger off unless FLASK_HOST /
    # FLASK_DEBUG say otherwise. Containers start gunicorn (see the Dockerfile).
    app.run(host=os.getenv("FLASK_HOST", "127.0.0.1"), port=PORT,
            debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
