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
import os
import requests

load_dotenv()

DB_API_URL = os.getenv("DB_API_URL", "http://127.0.0.1:6001")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")

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

    advice, ai_error = call_model(system_prompt, task_prompt, max_tokens=180)
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
    advice_html = (f"<p>{escape(advice)}</p>" if advice else
                   "<p class='error'>AI explanation unavailable - check that "
                   "Ollama is running. The score above is still valid.</p>")

    return f"""
    <div>
      <p><strong>{result['score']}% complete.</strong> {status}</p>
      {gap_html}
      {advice_html}
    </div>
    """


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
    return jsonify({"service": "student-1-backend", "model": OLLAMA_MODEL, "status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)
