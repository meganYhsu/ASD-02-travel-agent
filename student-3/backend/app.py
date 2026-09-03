from flask import Flask, request
from dotenv import load_dotenv
from openai import OpenAI
from markupsafe import escape
from pathlib import Path
from datetime import date
import os
import requests

load_dotenv()

DB_API_URL = os.getenv("DB_API_URL", "http://localhost:6003")
TRIP_DB_API_URL = os.getenv("TRIP_DB_API_URL", "http://localhost:6004")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")

PROMPT_DIR = Path(__file__).with_name("prompts")

app = Flask(__name__)

client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")


def load_prompt(filename):
    return (PROMPT_DIR / filename).read_text(encoding="utf-8").strip()


def get_trip(trip_id):
    try:
        resp = requests.get(f"{TRIP_DB_API_URL}/trips/{trip_id}", timeout=5)
        resp.raise_for_status()
        return resp.json(), None
    except requests.RequestException:
        return None, (
            "<p class='error'>Trip Planning service is unavailable. "
            "Budget analysis needs live trip data - try again later.</p>"
        )

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

    spent = sum(e["amount"] for e in expenses)
    remaining = budget["total_budget"] - spent

    per_cat = {}
    for e in expenses:
        per_cat[e["category_name"]] = per_cat.get(e["category_name"], 0) + e["amount"]

    rows = "".join(
        f"<tr><td>{escape(name)}</td><td>{amt:.2f}</td></tr>"
        for name, amt in sorted(per_cat.items(), key=lambda x: -x[1])
    )
    return f"""
    <h3>Trip {trip_id} budget</h3>
    <p>Total: {budget['total_budget']:.2f} {budget['currency']} |
       Spent: {spent:.2f} | Remaining: {remaining:.2f}</p>
    <table><tr><th>Category</th><th>Spent</th></tr>{rows}</table>
    """


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
    return dashboard(payload["trip_id"])


@app.route("/expenses/<int:expense_id>/delete", methods=["POST"])
def delete_expense(expense_id):
    trip_id = request.form.get("trip_id", type=int)
    try:
        requests.delete(f"{DB_API_URL}/expenses/{expense_id}", timeout=5)
    except requests.RequestException:
        return "<p class='error'>Could not delete the expense.</p>", 503
    return dashboard(trip_id)


@app.route("/analyse/<int:trip_id>", methods=["POST"])
def analyse(trip_id):
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

    spent = sum(e["amount"] for e in expenses)
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=True)