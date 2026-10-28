from flask import Flask, request, jsonify
from dotenv import load_dotenv
from openai import OpenAI
from markupsafe import escape
from pathlib import Path
from datetime import date
import os
import re
import requests

load_dotenv()

DB_API_URL = os.getenv("DB_API_URL", "http://127.0.0.1:6003")
TRIP_API_URL = os.getenv("TRIP_API_URL", "http://127.0.0.1:6004")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:7004")
RAG_SERVER_URL = os.getenv("RAG_SERVER_URL", "http://127.0.0.1:7001")
# Shared Multi-Agent server (ai-services/multi-agent-server, default port 6767)
MULTI_AGENT_SERVICE_URL = os.getenv("MULTI_AGENT_SERVICE_URL",
                                    "http://127.0.0.1:6767").rstrip("/")
# Planner + Worker + Reviewer run one after another on a local model
MULTI_AGENT_TIMEOUT_SECONDS = int(os.getenv("MULTI_AGENT_TIMEOUT_SECONDS", "420"))

# Release 2: every AI service is OFF unless the environment turns it on.
# docker-compose.yml (local) sets them to "true"; CI and the cloud
# deployment leave them off, which is the required cloud baseline.
def flag(name):
    return os.getenv(name, "false").lower() == "true"


AI_MODE_ENABLED = flag("AI_MODE_ENABLED")
MCP_ENABLED = flag("MCP_ENABLED")
RAG_ENABLED = flag("RAG_ENABLED")
MULTI_AGENT_ENABLED = flag("MULTI_AGENT_ENABLED")
MULTI_AGENT_SERVICE = "budget"
MULTI_AGENT_TASK = "review_spending"
WORKFLOW_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
RAG_CALLER = os.getenv("RAG_CALLER", "student-3-budget")
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
RAG_TIMEOUT_SECONDS = int(os.getenv("RAG_TIMEOUT_SECONDS", "300"))

ALLOWED_MCP_TOOLS = {
    "total_activity_count":
        "Planned activity count for a trip - gives budget per activity",
    "total_activities_count_a_day":
        "Planned activities on one day - gives daily budget pacing",
    "get_trip_activities_desc":
        "Planned activity descriptions - matches expenses to the itinerary",
}

MCP_TOOL_ARGUMENTS = {
    "total_activity_count": ("itinerary_id",),
    "total_activities_count_a_day": ("itinerary_id", "day_no"),
    "get_trip_activities_desc": ("itinerary_id",),
}

PROMPT_DIR = Path(__file__).with_name("prompts")

app = Flask(__name__)

client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")


def load_prompt(filename):
    return (PROMPT_DIR / filename).read_text(encoding="utf-8").strip()
RAG_ANSWER_KEYS = ("answer", "response", "output", "text")
RAG_LIST_KEYS = ("citations", "results", "sources", "documents",
                 "contexts", "chunks")
RAG_CONFIDENCE_KEYS = ("confidence_category", "confidence", "confidence_label")
RAG_TITLE_KEYS = ("source_id", "chunk_id", "title", "source", "document", "id")
RAG_SNIPPET_KEYS = ("text", "snippet", "content", "chunk")


def read_first(payload, *keys):
    """Return the first key present in payload, or None."""
    if not isinstance(payload, dict):
        return None
    for key in keys:
        if key in payload and payload[key] not in (None, ""):
            return payload[key]
    return None

def request_value(name, as_int=False):
    """Read a field from a form post (htmx) or a JSON body (agentic loop)."""
    raw = request.form.get(name)
    if raw is None:
        body = request.get_json(silent=True) or {}
        raw = body.get(name)
    if raw is None or raw == "":
        return None
    if as_int:
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None
    return str(raw)

def get_trip(trip_id):
    try:
        resp = requests.get(
            f"{TRIP_API_URL}/itineraries/{trip_id}", timeout=5
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException:
        return None, (
            "<p class='error'>Trip Planning service is unavailable. "
            "Budget analysis needs live trip data - try again later.</p>"
        )

    trip = {
        "destination": data.get("destination") or "the destination",
        "start_date": data.get("start_date") or data.get("startDate"),
        "end_date": data.get("end_date") or data.get("endDate"),
    }

    if not trip["start_date"] or not trip["end_date"]:
        return None, (
            "<p class='error'>Trip Planning response did not include "
            "trip dates.</p>"
        )

    return trip, None


# ------------------------------------------------------------- model helper
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


# ------------------------------------------------------------------ dashboard
@app.route("/dashboard/<int:trip_id>")
def dashboard(trip_id):
    try:
        budget = requests.get(f"{DB_API_URL}/budgets/{trip_id}", timeout=5).json()
        expenses = requests.get(
            f"{DB_API_URL}/expenses", params={"trip_id": trip_id}, timeout=5
        ).json()
    except requests.RequestException:
        return "<p class='error'>Budget database service is unavailable.</p>", 503

    if "error" in budget:
        return f"<p>No budget set for trip {trip_id} yet.</p>", 404

    spent = 0
    for e in expenses:
        spent += e["amount"]
    remaining = budget["total_budget"] - spent

    per_cat = {}
    for e in expenses:
        name = e["category_name"]
        if name not in per_cat:
            per_cat[name] = 0
        per_cat[name] += e["amount"]

    sorted_cats = sorted(per_cat.items(), key=lambda x: x[1], reverse=True)
    rows = ""
    for name, amt in sorted_cats:
        rows += f"<tr><td>{escape(name)}</td><td>{amt:.2f}</td></tr>"

    items = ""
    for e in expenses:
        items += (
            "<tr>"
            f"<td>{e['expense_date']}</td>"
            f"<td>{escape(e['description'])}</td>"
            f"<td>{escape(e['category_name'])}</td>"
            f"<td>{e['amount']:.2f}</td>"
            "<td>"
            f"<button hx-get='/api/expenses/{e['expense_id']}/edit' "
            "hx-target='#edit-form'>Edit</button> "
            f"<form hx-post='/api/expenses/{e['expense_id']}/delete' "
            "hx-target='#dashboard' style='display:inline'>"
            f"<input type='hidden' name='trip_id' value='{trip_id}'>"
            "<button type='submit'>Delete</button></form>"
            "</td></tr>"
        )

    return f"""
    <h3>Trip {trip_id} budget</h3>
    <p>Total: {budget['total_budget']:.2f} {budget['currency']} |
       Spent: {spent:.2f} | Remaining: {remaining:.2f}</p>
    <table><tr><th>Category</th><th>Spent</th></tr>{rows}</table>
    <h4>Expenses</h4>
    <table>
      <tr><th>Date</th><th>Description</th><th>Category</th><th>Amount</th><th></th></tr>
      {items}
    </table>
    """


# ----------------------------------------------------------- expense CRUD (UI)
@app.route("/expenses", methods=["POST"])
def add_expense():
    form = request.form
    payload = {
        "trip_id": form.get("trip_id", type=int),
        "category_id": form.get("category_id", type=int),
        "description": form.get("description", "").strip(),
        "amount": form.get("amount", type=float),
        "expense_date": form.get("expense_date") or date.today().isoformat(),
    }
    if not payload["description"] or payload["amount"] is None:
        return "<p class='error'>Description and amount are required.</p>", 400
    try:
        resp = requests.post(f"{DB_API_URL}/expenses", json=payload, timeout=5)
        resp.raise_for_status()
    except requests.RequestException:
        return "<p class='error'>Could not save the expense.</p>", 503
    # Return the refreshed dashboard so HTMX swaps it in one step
    return dashboard(payload["trip_id"])


@app.route("/expenses/<int:expense_id>/delete", methods=["POST"])
def delete_expense(expense_id):
    trip_id = request.form.get("trip_id", type=int)
    try:
        requests.delete(f"{DB_API_URL}/expenses/{expense_id}", timeout=5)
    except requests.RequestException:
        return "<p class='error'>Could not delete the expense.</p>", 503
    return dashboard(trip_id)


@app.route("/expenses/<int:expense_id>/edit")
def edit_expense_form(expense_id):
    try:
        expense = requests.get(f"{DB_API_URL}/expenses/{expense_id}", timeout=5).json()
        categories = requests.get(f"{DB_API_URL}/categories", timeout=5).json()
    except requests.RequestException:
        return "<p class='error'>Budget database service is unavailable.</p>", 503

    if "error" in expense:
        return "<p class='error'>Expense not found.</p>", 404

    options = ""
    for c in categories:
        selected = ""
        if c["category_id"] == expense["category_id"]:
            selected = " selected"
        options += f"<option value='{c['category_id']}'{selected}>{escape(c['name'])}</option>"

    return f"""
    <h4>Edit expense {expense_id}</h4>
    <form hx-post="/api/expenses/{expense_id}/update" hx-target="#dashboard">
        <input type="hidden" name="trip_id" value="{expense['trip_id']}">
        <label>Description
            <input name="description" value="{escape(expense['description'])}" required></label>
        <label>Amount (AUD)
            <input name="amount" type="number" step="0.01" min="0"
                   value="{expense['amount']}" required></label>
        <label>Category <select name="category_id">{options}</select></label>
        <label>Date
            <input name="expense_date" type="date" value="{expense['expense_date']}"></label>
        <button type="submit">Update expense</button>
    </form>
    """


@app.route("/expenses/<int:expense_id>/update", methods=["POST"])
def update_expense(expense_id):
    form = request.form
    trip_id = form.get("trip_id", type=int)
    payload = {
        "description": form.get("description", "").strip(),
        "amount": form.get("amount", type=float),
        "category_id": form.get("category_id", type=int),
        "expense_date": form.get("expense_date") or date.today().isoformat(),
    }
    if not payload["description"] or payload["amount"] is None:
        return "<p class='error'>Description and amount are required.</p>", 400
    try:
        resp = requests.put(
            f"{DB_API_URL}/expenses/{expense_id}", json=payload, timeout=5
        )
        resp.raise_for_status()
    except requests.RequestException:
        return "<p class='error'>Could not update the expense.</p>", 503
    return dashboard(trip_id)


# ------------------------------------------------------------------ AI analyse
@app.route("/analyse/<int:trip_id>", methods=["POST"])
def analyse(trip_id):
    if not AI_MODE_ENABLED:
        return ("<p class='error'>AI-Mode is disabled in this environment "
                "(AI_MODE_ENABLED=false).</p>"), 503

    # 1. OBSERVE - gather live evidence from both services
    trip, err = get_trip(trip_id)
    if err:
        return err, 503
    try:
        budget = requests.get(f"{DB_API_URL}/budgets/{trip_id}", timeout=5).json()
        expenses = requests.get(
            f"{DB_API_URL}/expenses", params={"trip_id": trip_id}, timeout=5
        ).json()
    except requests.RequestException:
        return "<p class='error'>Budget database service is unavailable.</p>", 503

    spent = 0
    for e in expenses:
        spent += e["amount"]
    total_days = (date.fromisoformat(trip["end_date"])
                  - date.fromisoformat(trip["start_date"])).days + 1
    seen_dates = []
    for e in expenses:
        if e["expense_date"] not in seen_dates:
            seen_dates.append(e["expense_date"])
    days_elapsed = len(seen_dates)
    days_left = max(total_days - days_elapsed, 0)

    expense_lines = "\n".join(
        f"- {e['expense_date']} {e['category_name']}: {e['description']} ({e['amount']} AUD)"
        for e in expenses
    )

    # 2. Build context for the LLM (same pattern as the lab's /ask-with-context)
    system_prompt = load_prompt("budget_system_prompt.txt")
    task_prompt = (
        load_prompt("budget_task_prompt.txt")
        .replace("{{TRIP}}", f"{trip['destination']}, {total_days} days, "
                             f"day {days_elapsed} of {total_days}")
        .replace("{{BUDGET}}", f"{budget['total_budget']} {budget['currency']}")
        .replace("{{SPENT}}", f"{spent:.2f}")
        .replace("{{DAYS_LEFT}}", str(days_left))
        .replace("{{EXPENSES}}", expense_lines)
    )

    advice, ai_error = call_model(system_prompt, task_prompt)
    if ai_error:
        return (
            "<p class='error'>AI analysis failed. Check that Ollama is running.</p>"
            f"<pre>{escape(ai_error)}</pre>",
            503,
        )

    # 3. Store the recommendation so the human decision is recorded (ADAPT)
    try:
        rec = requests.post(
            f"{DB_API_URL}/recommendations",
            json={"trip_id": trip_id, "recommendation": advice},
            timeout=5,
        ).json()
        rec_id = rec.get("rec_id")
    except requests.RequestException:
        rec_id = None

    buttons = ""
    if rec_id:
        buttons = f"""
        <button hx-post="/api/recommendations/{rec_id}/decide"
                hx-vals='{{"status": "accepted"}}' hx-target="#ai-result">Accept</button>
        <button hx-post="/api/recommendations/{rec_id}/decide"
                hx-vals='{{"status": "dismissed"}}' hx-target="#ai-result">Dismiss</button>
        """
    return f"<div><p>{escape(advice)}</p>{buttons}</div>"


@app.route("/recommendations/<int:rec_id>/decide", methods=["POST"])
def decide(rec_id):
    status = request.form.get("status")
    try:
        requests.patch(
            f"{DB_API_URL}/recommendations/{rec_id}",
            json={"status": status}, timeout=5,
        )
    except requests.RequestException:
        return "<p class='error'>Could not record the decision.</p>", 503

    return f"<p>Recommendation {status}. Decision recorded for human review evidence.</p>"


# =============================================================================
# RELEASE 1 - MCP
# =============================================================================
@app.route("/mcp/tools")
def mcp_tools():
    """Registered tools on the shared MCP server, with this feature's boundary.

    Shared server contract:
        GET {MCP_SERVER_URL}/mcp/tools -> {"ok": true, "tools": ["name", ...]}
    """
    if not MCP_ENABLED:
        return ("<p class='error'>MCP mode is disabled in this environment "
                "(MCP_ENABLED=false).</p>"), 503

    try:
        resp = requests.get(f"{MCP_SERVER_URL}/mcp/tools", timeout=5)
        resp.raise_for_status()
        payload = resp.json()
    except requests.RequestException:
        return ("<p class='error'>Shared MCP server is unavailable at "
                f"{escape(MCP_SERVER_URL)}. Start it locally and try again.</p>"), 503
    except ValueError:
        return "<p class='error'>MCP server returned a non-JSON response.</p>", 502

    if isinstance(payload, dict):
        server_tools = payload.get("tools", [])
    else:
        server_tools = payload

    names = []
    for t in server_tools:
        names.append(t.get("name") if isinstance(t, dict) else str(t))

    rows = ""
    for name in names:
        if name in ALLOWED_MCP_TOOLS:
            verdict = "permitted"
            purpose = ALLOWED_MCP_TOOLS[name]
        else:
            verdict = "outside this feature's boundary"
            purpose = "owned by another feature"
        rows += (f"<tr><td>{escape(name)}</td><td>{escape(purpose)}</td>"
                 f"<td>{verdict}</td></tr>")

    missing = [n for n in ALLOWED_MCP_TOOLS if n not in names]
    note = ""
    if missing:
        note = ("<p class='error'>Permitted but not registered on the shared "
                f"server: {escape(', '.join(missing))}</p>")

    return f"""
    <h4>Tools on the shared MCP server ({len(names)} registered)</h4>
    <table>
      <tr><th>Tool</th><th>Purpose for Budget</th><th>Boundary</th></tr>
      {rows}
    </table>
    {note}
    <p class="muted">A tool outside this feature's boundary is refused by this
       backend before the MCP server is contacted.</p>
    """


@app.route("/mcp/<tool_name>", methods=["POST"])
def mcp_call(tool_name):
    """Frontend -> backend/API -> shared local MCP server -> registered tool.

    Shared server contract:
        POST {MCP_SERVER_URL}/mcp/tool
        <- {"tool_name": "<name>", "arguments": {...}}
        -> {"ok": true, "tool_name": "<name>", "result": {...}}
        -> {"ok": false, "error": "<message>"}   on failure
    """
    if tool_name not in ALLOWED_MCP_TOOLS:
        return (f"<p class='error'>Tool '{escape(tool_name)}' is outside the "
                "Budget &amp; Expense Tracking boundary and was refused by "
                "this backend. The shared MCP server was not contacted.</p>"), 403

    if not MCP_ENABLED:
        return ("<p class='error'>MCP mode is disabled in this environment "
                "(MCP_ENABLED=false).</p>"), 503

    arguments = {}
    for arg in MCP_TOOL_ARGUMENTS.get(tool_name, ()):
        if arg == "itinerary_id":
            value = request_value("trip_id", as_int=True)
        elif arg == "day_no":
            value = request_value("day_no", as_int=True)
            if value is None:
                value = 1
        else:
            value = request_value(arg, as_int=True)
        if value is None:
            return (f"<p class='error'>{escape(arg)} is required for "
                    f"{escape(tool_name)}.</p>"), 400
        arguments[arg] = value

    try:
        resp = requests.post(
            f"{MCP_SERVER_URL}/mcp/tool",
            json={"tool_name": tool_name, "arguments": arguments},
            timeout=15,
        )
    except requests.RequestException:
        return ("<p class='error'>Shared MCP server is unavailable at "
                f"{escape(MCP_SERVER_URL)}. Start it locally and try again.</p>"), 503

    try:
        data = resp.json()
    except ValueError:
        return "<p class='error'>MCP server returned a non-JSON response.</p>", 502

    if resp.status_code >= 400 or not data.get("ok", True):
        message = data.get("error", f"HTTP {resp.status_code}")
        return f"<p class='error'>MCP tool failed: {escape(str(message))}</p>", 502

    result = data.get("result", data)

    rows = ""
    if isinstance(result, dict):
        for key, value in result.items():
            if isinstance(value, list):
                value = "; ".join(str(v) for v in value)
            rows += (f"<tr><td>{escape(str(key))}</td>"
                     f"<td>{escape(str(value))}</td></tr>")
    elif isinstance(result, list):
        for i, value in enumerate(result, start=1):
            rows += f"<tr><td>{i}</td><td>{escape(str(value))}</td></tr>"
    else:
        rows = f"<tr><td>result</td><td>{escape(str(result))}</td></tr>"

    return f"""
    <h4>MCP tool result</h4>
    <p>Tool: <strong>{escape(tool_name)}</strong>
       &middot; arguments: {escape(str(arguments))}
       &middot; purpose: {escape(ALLOWED_MCP_TOOLS[tool_name])}</p>
    <table>
      <tr><th>Field</th><th>Value</th></tr>
      {rows}
    </table>
    <p class="muted">Itinerary data was read through the shared MCP server, not
       from the Trip Planning database directly.</p>
    """


@app.route("/mcp/provide/budget_summary/<int:trip_id>")
def mcp_provide_budget_summary(trip_id):
    """Tool-provider endpoint.

    The shared MCP server registers 'get_budget_summary' and executes it by
    calling this endpoint, so budget data stays behind this feature's own API
    (Cross-Feature Database API rule). JSON, not HTML - the caller is a service.
    """
    try:
        budget = requests.get(f"{DB_API_URL}/budgets/{trip_id}", timeout=5).json()
        expenses = requests.get(
            f"{DB_API_URL}/expenses", params={"trip_id": trip_id}, timeout=5
        ).json()
    except requests.RequestException:
        return jsonify({"error": "budget database service unavailable"}), 503

    if "error" in budget:
        return jsonify({"error": f"no budget for trip {trip_id}"}), 404

    spent = 0
    for e in expenses:
        spent += e["amount"]

    per_cat = {}
    for e in expenses:
        per_cat[e["category_name"]] = per_cat.get(e["category_name"], 0) + e["amount"]
    top_category = ""
    if per_cat:
        top_category = sorted(per_cat.items(), key=lambda x: x[1], reverse=True)[0][0]

    return jsonify({
        "trip_id": trip_id,
        "currency": budget["currency"],
        "total_budget": round(budget["total_budget"], 2),
        "spent": round(spent, 2),
        "remaining": round(budget["total_budget"] - spent, 2),
        "expense_count": len(expenses),
        "top_category": top_category,
    })

# =============================================================================
# RELEASE 1 - RAG
# =============================================================================
@app.route("/rag/query", methods=["POST"])
def rag_query():
    """Frontend -> backend/API -> shared local RAG server -> grounded answer."""
    if not RAG_ENABLED:
        return ("<p class='error'>RAG mode is disabled in this environment "
                "(RAG_ENABLED=false).</p>"), 503
    
    question = (request_value("question") or "").strip()
    if not question:
        return "<p class='error'>A question is required.</p>", 400

    try:
        resp = requests.post(
            f"{RAG_SERVER_URL}/rag/answer",
            json={
                "query": question,
                "k": RAG_TOP_K,
                "caller": RAG_CALLER,
            },
            timeout=RAG_TIMEOUT_SECONDS,
        )
    except requests.Timeout:
        return ("<p class='error'>The shared RAG server did not answer within "
                f"{RAG_TIMEOUT_SECONDS} seconds. The local model is still "
                "generating - try a shorter question or retry.</p>"), 504
    except requests.RequestException:
        return ("<p class='error'>Shared RAG server is unavailable at "
                f"{escape(RAG_SERVER_URL)}. Start it locally and try again.</p>"), 503

    try:
        data = resp.json()
    except ValueError:
        return "<p class='error'>RAG server returned a non-JSON response.</p>", 502

    if resp.status_code >= 400 or data.get("status") == "error":
        message = data.get("error", f"HTTP {resp.status_code}")
        return f"<p class='error'>RAG query failed: {escape(str(message))}</p>", 502
    
    answer = str(read_first(data, *RAG_ANSWER_KEYS) or "").strip()
    citations = read_first(data, *RAG_LIST_KEYS) or []
    confidence = str(read_first(data, *RAG_CONFIDENCE_KEYS) or "unknown").lower()
    summary = data.get("retrieval_summary") or {}
    retrieved_count = summary.get("retrieved_count")

    if answer.strip().lower() == "insufficient evidence." or not answer:
        detail = ""
        if retrieved_count:
            detail = (f"<p class='muted'>{retrieved_count} chunks were retrieved "
                      "but none supported an answer.</p>")
        return f"""
        <div class="rag-answer">
          <p class="error"><strong>Insufficient context.</strong>
             The shared knowledge base holds no evidence that supports an
             answer to this question, so no grounded answer is given.</p>
          <p>Question: {escape(question)}</p>
          {detail}
          <p class="muted">Confidence: {escape(confidence)}
             &middot; Citations: 0</p>
        </div>
        """

    if not citations:
        return f"""
        <div class="rag-answer">
          <p class="error"><strong>Answer not grounded.</strong>
             The model produced text but returned no supporting citations,
             so it is not presented as a grounded answer.</p>
          <p>{escape(answer)}</p>
          <p class="muted">Confidence: {escape(confidence)}
             &middot; Citations: 0
             &middot; Chunks retrieved: {escape(str(retrieved_count or 0))}</p>
        </div>
        """
    
    has_text = any(
        isinstance(c, dict) and read_first(c, *RAG_SNIPPET_KEYS)
        for c in citations
    )

    rows = ""
    for i, c in enumerate(citations, start=1):
        if isinstance(c, dict):
            source = read_first(c, *RAG_TITLE_KEYS) or f"source {i}"
            chunk_id = c.get("chunk_id", "")
            tier = c.get("authority_tier", "")
            snippet = str(read_first(c, *RAG_SNIPPET_KEYS) or "")
        else:
            source, chunk_id, tier, snippet = str(c), "", "", ""
        if len(snippet) > 160:
            snippet = snippet[:160] + "..."
        text_cell = f"<td>{escape(snippet)}</td>" if has_text else ""
        rows += (f"<tr><td>[{i}]</td><td>{escape(str(source))}</td>"
                 f"<td>{escape(str(chunk_id))}</td><td>{escape(str(tier))}</td>"
                 f"{text_cell}</tr>")

    text_header = "<th>Text</th>" if has_text else ""

    return f"""
    <div class="rag-answer">
      <p>{escape(answer)}</p>
      <p class="muted">Confidence: <strong>{escape(confidence)}</strong>
         &middot; Citations: {len(citations)}
         &middot; Chunks retrieved: {escape(str(retrieved_count or len(citations)))}</p>
      <h5>Citations</h5>
      <table>
        <tr><th>#</th><th>Source</th><th>Chunk</th><th>Tier</th>{text_header}</tr>
        {rows}
      </table>
      <p class="muted">Each citation is a retrieved chunk the answer is
         grounded in. Use "Show retrieved context only" to read the chunk
         text.</p>
    </div>
    """


@app.route("/rag/retrieve", methods=["POST"])
def rag_retrieve():
    """Retrieval-only view: shows what the RAG server found, before generation.

    Useful as report evidence and as a fast check when the local model is slow,
    because it skips answer generation entirely.
    """
    if not RAG_ENABLED:
        return ("<p class='error'>RAG mode is disabled in this environment "
                "(RAG_ENABLED=false).</p>"), 503

    question = (request_value("question") or "").strip()
    if not question:
        return "<p class='error'>A question is required.</p>", 400

    try:
        resp = requests.post(
            f"{RAG_SERVER_URL}/rag/retrieve",
            json={"query": question, "k": RAG_TOP_K, "caller": RAG_CALLER},
            timeout=30,
        )
        data = resp.json()
    except requests.RequestException:
        return ("<p class='error'>Shared RAG server is unavailable at "
                f"{escape(RAG_SERVER_URL)}.</p>"), 503
    except ValueError:
        return "<p class='error'>RAG server returned a non-JSON response.</p>", 502

    chunks = read_first(data, *RAG_LIST_KEYS) or []
    if not chunks:
        return (f"<p class='error'>No context retrieved for "
                f"{escape(question)}.</p>")

    mode = data.get("retrieval_mode", "")
    rows = ""
    for i, c in enumerate(chunks, start=1):
        if isinstance(c, dict):
            source = read_first(c, *RAG_TITLE_KEYS) or f"source {i}"
            tier = c.get("authority_tier", "")
            snippet = str(read_first(c, *RAG_SNIPPET_KEYS) or "")
        else:
            source, tier, snippet = str(c), "", ""
        if len(snippet) > 160:
            snippet = snippet[:160] + "..."
        rows += (f"<tr><td>{i}</td><td>{escape(str(source))}</td>"
                 f"<td>{escape(str(tier))}</td><td>{escape(snippet)}</td></tr>")

    mode_note = f" &middot; mode: {escape(str(mode))}" if mode else ""
    return f"""
    <h4>Retrieved context ({len(chunks)} chunks){mode_note}</h4>
    <table>
      <tr><th>#</th><th>Source</th><th>Tier</th><th>Text</th></tr>
      {rows}
    </table>
    <p class="muted">Retrieval only - no answer generation, so this returns
       in seconds even when the local model is slow.</p>
    """


# =============================================================================
# RELEASE 2 - MULTI-AGENT
# Shared server: ai-services/multi-agent-server (port 6767, not containerised)
#   Frontend UI -> this backend -> POST /workflow
#     -> Planner -> Worker -> Reviewer (run by the shared server)
#   -> human decision in this UI -> POST /workflow/<id>/review
#   -> recommendation saved in this feature's database
# =============================================================================
MA_DECISIONS = ("Accept", "Partially Accept", "Reject")
MA_MIN_REASON = 20


def ma_disabled():
    return ("<p class='error'>Multi-Agent mode is disabled in this environment "
            "(MULTI_AGENT_ENABLED=false).</p>"), 503


def budget_review_request(trip_id, focus=""):
    text = (f"Review the spending of trip {trip_id} against its budget and "
            "recommend one concrete adjustment for the rest of the trip. Use only "
            "the supplied budget context and give amounts in its currency.")
    if focus:
        text += f" Focus on: {focus[:200]}"
    return text


def build_budget_evidence(trip_id):
    """Context the agents may use. Budget data comes only from this feature's
    own DB API; trip dates from Trip Planning; activities through shared MCP.
    Returns (evidence, None) or (None, (message, http_status))."""
    try:
        budget = requests.get(f"{DB_API_URL}/budgets/{trip_id}", timeout=5).json()
        expenses = requests.get(
            f"{DB_API_URL}/expenses", params={"trip_id": trip_id}, timeout=5
        ).json()
    except (requests.RequestException, ValueError):
        return None, ("Budget database service is unavailable.", 503)
    if "error" in budget:
        return None, (f"No budget set for trip {trip_id} yet.", 404)

    total = budget["total_budget"]
    spent = 0
    per_cat = {}
    for e in expenses:
        spent += e["amount"]
        per_cat[e["category_name"]] = per_cat.get(e["category_name"], 0) + e["amount"]

    recent = sorted(expenses, key=lambda e: e["expense_date"], reverse=True)[:15]
    evidence = {
        "budget": {"trip_id": trip_id, "total_budget": round(total, 2),
                   "currency": budget["currency"]},
        "spending": {"spent": round(spent, 2), "remaining": round(total - spent, 2),
                     "expense_count": len(expenses),
                     "percent_used": round(spent / total * 100, 1) if total else 0},
        "spent_by_category": {name: round(amount, 2) for name, amount in
                              sorted(per_cat.items(), key=lambda x: x[1], reverse=True)},
        "recent_expenses": [
            {"date": e["expense_date"], "category": e["category_name"],
             "description": e["description"], "amount": e["amount"]}
            for e in recent
        ],
    }

    trip, _ = get_trip(trip_id)
    if trip:
        total_days = (date.fromisoformat(trip["end_date"])
                      - date.fromisoformat(trip["start_date"])).days + 1
        days_with = len({e["expense_date"] for e in expenses})
        evidence["trip"] = {"destination": trip["destination"],
                            "start_date": trip["start_date"],
                            "end_date": trip["end_date"],
                            "total_days": total_days,
                            "days_with_expenses": days_with,
                            "days_left": max(total_days - days_with, 0)}
    else:
        evidence["trip"] = {"available": False,
                            "note": "Trip Planning service unavailable - dates unknown"}

    if MCP_ENABLED:
        try:
            resp = requests.post(
                f"{MCP_SERVER_URL}/mcp/tool",
                json={"tool_name": "total_activity_count",
                      "arguments": {"itinerary_id": trip_id}},
                timeout=10,
            )
            data = resp.json()
            if resp.ok and data.get("ok", True):
                evidence["planned_activities"] = data.get("result", data)
        except (requests.RequestException, ValueError):
            evidence["planned_activities"] = {"available": False,
                                              "note": "shared MCP server unavailable"}
    return evidence, None


def ma_request_body(trip_id, evidence, focus=""):
    """Request format of the shared server (see its README)."""
    return {"service": MULTI_AGENT_SERVICE, "task": MULTI_AGENT_TASK,
            "user_request": budget_review_request(trip_id, focus),
            "context": evidence}


def ma_call(method, path, payload=None):
    """Call the shared server. Returns (data, None) or (None, (message, status))."""
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
        return None, ("Shared Multi-Agent server is unavailable at "
                      f"{MULTI_AGENT_SERVICE_URL}. Start it locally and try again.", 503)
    try:
        data = resp.json()
    except ValueError:
        return None, ("Multi-Agent server returned a non-JSON response.", 502)
    if resp.status_code >= 400:
        message = data.get("error") if isinstance(data, dict) else None
        return None, (str(message or f"HTTP {resp.status_code}"),
                      resp.status_code if resp.status_code < 500 else 502)
    return data, None


def ma_error(err):
    message, status = err
    return f"<p class='error'>{escape(message)}</p>", status


def ma_trip_id(wf):
    return ((wf.get("context") or {}).get("budget") or {}).get("trip_id")


def ma_agent_card(number, title, result, text, extra_html=""):
    """One agent's result. Model text is escaped; extra_html is built here."""
    status = str(result.get("status", "missing"))
    flag = "" if status == "success" else f" &middot; <strong class='error'>{escape(status)}</strong>"
    error = f"<p class='error'>{escape(str(result['error']))}</p>" if result.get("error") else ""
    return (f"<div class='ma-stage'><h4>{number}. {title} "
            f"<span class='muted'>{escape(str(result.get('model', '')))}{flag}</span></h4>"
            f"<div class='ma-text'>{escape(str(text or ''))}</div>{extra_html}{error}</div>")

def ma_status_strip(wf):
    """Request -> Planner -> Worker -> Reviewer -> Human review, one box each."""
    decision = wf.get("human_decision") or {}
    human = decision.get("decision") if decision.get("status") == "recorded" else "pending"
    stages = [
        ("Request", "received"),
        ("Planner", (wf.get("planner_result") or {}).get("status", "missing")),
        ("Worker", (wf.get("worker_result") or {}).get("status", "missing")),
        ("Reviewer", (wf.get("reviewer_result") or {}).get("status", "missing")),
        ("Human review", human),
    ]
    items = ""
    for number, (name, state) in enumerate(stages, start=1):
        state = str(state)
        css = ("ma-wait" if state == "pending" else
               "ma-bad" if state in ("timeout", "error", "missing") else "ma-ok")
        items += (f"<li class='{css}'>{number}. {name}: "
                  f"<strong>{escape(state)}</strong></li>")
    return f"<ol class='ma-status'>{items}</ol>"


def ma_render(wf, notice=""):
    """The three agent results and the human-review step as one HTML fragment."""
    wid = str(wf.get("workflow_id", ""))
    planner = wf.get("planner_result") or {}
    worker = wf.get("worker_result") or {}
    reviewer = wf.get("reviewer_result") or {}

    steps = ""
    if isinstance(planner.get("steps"), list):
        steps = "<ol>" + "".join(
            f"<li>{escape(str(s.get('agent', '')))}: {escape(str(s.get('action', '')))}</li>"
            for s in planner["steps"] if isinstance(s, dict)) + "</ol>"
    cards = (ma_agent_card(1, "Planner", planner, planner.get("plan"), steps)
             + ma_agent_card(2, "Worker", worker, worker.get("output"))
             + ma_agent_card(3, "Reviewer", reviewer, reviewer.get("review")))

    decision = wf.get("human_decision") or {}
    if decision.get("status") == "recorded":
        action = (f"<p><strong>Human decision: {escape(str(decision.get('decision', '')))}</strong></p>"
                  f"<p class='muted'>Reason: {escape(str(decision.get('reason', '')))}</p>")
        trip_id = ma_trip_id(wf)
        if decision.get("decision") == "Partially Accept" and trip_id:
            action += f"""
            <form hx-post="/api/multi-agent/budget-review/{int(trip_id)}"
                  hx-target="#ma-result" hx-indicator="#ma-loading">
              <input type="hidden" name="focus" value="{escape(str(decision.get('reason', '')))}">
              <button type="submit">Run the agents again with this correction</button>
            </form>"""
    else:
        options = "".join(
            f"<label><input type='radio' name='decision' value='{d}' required> {d}</label><br>"
            for d in MA_DECISIONS)
        action = f"""
        <form hx-post="/api/multi-agent/workflow/{escape(wid)}/decision"
              hx-target="#ma-workflow" hx-swap="outerHTML">
          <fieldset><legend>Human review</legend>
            {options}
            <label>Reason (at least {MA_MIN_REASON} characters)<br>
              <textarea name="reason" rows="2" cols="60" minlength="{MA_MIN_REASON}" required></textarea>
            </label><br>
            <label>Evidence (optional) <input name="evidence" size="50"></label>
            <button type="submit">Submit decision</button>
          </fieldset>
        </form>"""

    seconds = (wf.get("duration_ms") or 0) / 1000
    notice_html = f"<p>{escape(notice)}</p>" if notice else ""
    return f"""
    <div id="ma-workflow">
      <p>Workflow <code>{escape(wid)}</code> &middot; agents:
         <strong>{escape(str(wf.get('status', '')))}</strong> &middot; {seconds:.0f} s</p>
      {ma_status_strip(wf)}
      {notice_html}
      {cards}
      {action}
    </div>
    """


def ma_save_outcome(wf):
    """Store the human-reviewed recommendation in this feature's database."""
    trip_id = ma_trip_id(wf)
    decision = wf.get("human_decision") or {}
    choice = decision.get("decision")
    output = str((wf.get("worker_result") or {}).get("output") or "").strip()
    if not trip_id or not output or choice not in MA_DECISIONS:
        return ""
    text = output if len(output) <= 600 else output[:600] + "..."
    if choice == "Partially Accept":
        text += f" | Correction: {decision.get('reason', '')}"
    status = {"Accept": "accepted", "Reject": "dismissed"}.get(choice)
    try:
        rec = requests.post(
            f"{DB_API_URL}/recommendations",
            json={"trip_id": trip_id,
                  "recommendation": f"[Multi-agent {str(wf.get('workflow_id', ''))[:8]}] {text}"},
            timeout=5,
        ).json()
        rec_id = rec.get("rec_id")
        if not rec_id:
            raise ValueError("no rec_id returned")
        if status:
            requests.patch(f"{DB_API_URL}/recommendations/{rec_id}",
                           json={"status": status}, timeout=5)
    except (requests.RequestException, ValueError):
        return ("The decision was recorded by the Multi-Agent server, but the "
                "recommendation could not be saved.")
    return f"Recommendation #{rec_id} saved to the budget database as {status or 'proposed'}."


@app.route("/multi-agent/evidence/<int:trip_id>")
def multi_agent_evidence(trip_id):
    """The exact request this feature sends to the shared server, as JSON.
    Used by tools/budget_review_cli.py for the terminal workflow."""
    if not MULTI_AGENT_ENABLED:
        return jsonify({"error": "Multi-Agent mode is disabled (MULTI_AGENT_ENABLED=false)"}), 503
    evidence, err = build_budget_evidence(trip_id)
    if err:
        return jsonify({"error": err[0]}), err[1]
    return jsonify(ma_request_body(trip_id, evidence))


@app.route("/multi-agent/budget-review/<int:trip_id>", methods=["POST"])
def multi_agent_start(trip_id):
    if not MULTI_AGENT_ENABLED:
        return ma_disabled()
    evidence, err = build_budget_evidence(trip_id)
    if err:
        return ma_error(err)
    focus = (request_value("focus") or "").strip()
    wf, err = ma_call("POST", "/workflow", ma_request_body(trip_id, evidence, focus))
    if err:
        return ma_error(err)
    return ma_render(wf)


@app.route("/multi-agent/workflow/<workflow_id>")
def multi_agent_status(workflow_id):
    if not MULTI_AGENT_ENABLED:
        return ma_disabled()
    if not WORKFLOW_ID.match(workflow_id):
        return "<p class='error'>Invalid workflow id.</p>", 400
    wf, err = ma_call("GET", f"/workflow/{workflow_id}")
    if err:
        return ma_error(err)
    return ma_render(wf)


@app.route("/multi-agent/workflow/<workflow_id>/decision", methods=["POST"])
def multi_agent_decision(workflow_id):
    if not MULTI_AGENT_ENABLED:
        return ma_disabled()
    if not WORKFLOW_ID.match(workflow_id):
        return "<p class='error'>Invalid workflow id.</p>", 400
    decision = request_value("decision")
    reason = (request_value("reason") or "").strip()
    evidence = (request_value("evidence") or "").strip()

    problem = None
    if decision not in MA_DECISIONS:
        problem = "Choose Accept, Partially Accept or Reject."
    elif len(reason) < MA_MIN_REASON:
        problem = f"The reason must contain at least {MA_MIN_REASON} characters."
    wf = None
    if problem is None:
        wf, err = ma_call("POST", f"/workflow/{workflow_id}/review",
                          {"decision": decision, "reason": reason, "evidence": evidence})
        if err:
            problem = err[0]
    if problem:
        # Keep the review form on screen and say why the decision was refused.
        current, err = ma_call("GET", f"/workflow/{workflow_id}")
        if err:
            return ma_error(err)
        return ma_render(current, notice=f"Decision not recorded: {problem}")

    return ma_render(wf, notice=ma_save_outcome(wf))


@app.route("/health")
def health():
    """Configuration check (Release 1 and 2) - used by the agentic loop, CI and
    the cloud smoke test."""
    return jsonify({
        "service": "student-3-backend",
        "db_api": DB_API_URL,
        "trip_api": TRIP_API_URL,
        "mcp_server": MCP_SERVER_URL,
        "rag_server": RAG_SERVER_URL,
        "rag_caller": RAG_CALLER,
        "rag_timeout_seconds": RAG_TIMEOUT_SECONDS,
        "multi_agent_server": MULTI_AGENT_SERVICE_URL,
        "ai_mode_enabled": AI_MODE_ENABLED,
        "mcp_enabled": MCP_ENABLED,
        "rag_enabled": RAG_ENABLED,
        "multi_agent_enabled": MULTI_AGENT_ENABLED,
        "allowed_mcp_tools": sorted(ALLOWED_MCP_TOOLS),
    })


if __name__ == "__main__":
    # Direct runs (python app.py) listen on 127.0.0.1 unless FLASK_HOST is set,
    # and the debugger stays off unless FLASK_DEBUG=true. Containers start
    # gunicorn instead (see the Dockerfile).
    app.run(host=os.getenv("FLASK_HOST", "127.0.0.1"), port=5003,
            debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")

