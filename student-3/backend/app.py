from flask import Flask, request, jsonify
from dotenv import load_dotenv
from openai import OpenAI
from markupsafe import escape
from pathlib import Path
from datetime import date
import os
import requests

load_dotenv()

DB_API_URL = os.getenv("DB_API_URL", "http://127.0.0.1:6003")
TRIP_API_URL = os.getenv("TRIP_API_URL", "http://127.0.0.1:6004")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:7004")
RAG_SERVER_URL = os.getenv("RAG_SERVER_URL", "http://127.0.0.1:7001")
MCP_ENABLED = os.getenv("MCP_ENABLED", "true").lower() == "true"
RAG_ENABLED = os.getenv("RAG_ENABLED", "true").lower() == "true"
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


# ------------------------------------------------------------------ dashboard
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


# ------------------------------------------------------------------ AI analyse
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


@app.route("/analyse/<int:trip_id>", methods=["POST"])
def analyse(trip_id):
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

    # Release 0 stretch goal: if accepted, also send the itinerary
    # adjustment to the Trip Planning DB API here, e.g.
    #   requests.put(f"{TRIP_DB_API_URL}/activities/<id>", json={...})
    # Agreed API contract required first - see docs/api-contract.md
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


@app.route("/health")
def health():
    """Release 1 configuration check - used by the agentic loop and CI."""
    return jsonify({
        "service": "student-3-backend",
        "db_api": DB_API_URL,
        "trip_api": TRIP_API_URL,
        "mcp_server": MCP_SERVER_URL,
        "rag_server": RAG_SERVER_URL,
        "rag_caller": RAG_CALLER,
        "rag_timeout_seconds": RAG_TIMEOUT_SECONDS,
        "mcp_enabled": MCP_ENABLED,
        "rag_enabled": RAG_ENABLED,
        "allowed_mcp_tools": sorted(ALLOWED_MCP_TOOLS),
    })
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=True)
