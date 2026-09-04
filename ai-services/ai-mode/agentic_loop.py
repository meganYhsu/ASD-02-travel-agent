import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

PROMPT_DIR = Path(__file__).with_name("prompts")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")
IMPLEMENTATION_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
REVIEW_MODEL = os.getenv("OLLAMA_REVIEW_MODEL", "llama3.1:8b")

DB_API_URL = os.getenv("DB_API_URL", "http://127.0.0.1:6003")
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:5003")
TRIP_DB_API_URL = os.getenv("TRIP_DB_API_URL", "http://127.0.0.1:6004")

PLAN = {
    "goal": "Validate the Budget & Expense Tracking microservices before release",
    "db_plan": [
        "Check every table holds at least 10 demonstration records",
        "Check expenses reference valid categories",
    ],
    "endpoints_plan": [
        "GET /categories - list expense categories",
        "GET /expenses?trip_id=1 - list expenses for a trip",
        "GET /budgets/1 - budget for a trip",
        "GET /dashboard/1 - backend aggregation",
        "GET /trips/1 - cross-service trip lookup",
    ],
}


def load_prompt(filename):
    return (PROMPT_DIR / filename).read_text(encoding="utf-8").strip()


def observe_database():
    results = []
    all_ok = True

    try:
        categories = requests.get(f"{DB_API_URL}/categories", timeout=5).json()
        expenses = requests.get(f"{DB_API_URL}/expenses", timeout=5).json()
        recommendations = requests.get(f"{DB_API_URL}/recommendations", timeout=5).json()
    except requests.RequestException as exc:
        line = f"database API unreachable: {exc}"
        print(f"  Checked {line}")
        return [line], False

    counts = {
        "ExpenseCategories": len(categories),
        "Expenses": len(expenses),
        "AdjustmentRecommendations": len(recommendations),
    }
    for table, count in counts.items():
        status = "OK" if count >= 10 else "FAIL: fewer than 10 records"
        print(f"  Checked {table} = {count} records -> {status}")
        results.append(f"{table} has {count} records")
        if count < 10:
            all_ok = False

    valid_ids = []
    for c in categories:
        valid_ids.append(c["category_id"])

    for e in expenses:
        if e["category_id"] not in valid_ids:
            line = f"expense {e['expense_id']} references unknown category"
            print(f"  Checked {line} -> FAIL")
            results.append(line)
            all_ok = False

    if all_ok:
        results.append("all expenses reference valid categories")

    return results, all_ok


def observe_live_endpoints():
    results = []

    checks = [
        ("/categories", f"{DB_API_URL}/categories"),
        ("/expenses?trip_id=1", f"{DB_API_URL}/expenses?trip_id=1"),
        ("/budgets/1", f"{DB_API_URL}/budgets/1"),
        ("/dashboard/1", f"{BACKEND_URL}/dashboard/1"),
        ("/trips/1 (cross-service)", f"{TRIP_DB_API_URL}/trips/1"),
    ]

    for label, url in checks:
        try:
            response = requests.get(url, timeout=5)
            content_ok = bool(response.text and response.text.strip())
            line = f"{label} -> HTTP {response.status_code}, content_ok={content_ok}"
        except requests.RequestException as exc:
            line = f"{label} -> error: {exc}"
        print(f"  Checked {line}")
        results.append(line)

    return results


def call_model(model_name, system_prompt, user_prompt, max_tokens=150):
    try:
        client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama", timeout=180.0)
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.1,
        )
        content = response.choices[0].message.content
        if content and content.strip():
            return content.strip(), None
        return "No response generated.", None
    except Exception as exc:
        return None, f"{model_name} unavailable or timed out ({exc})"


def get_implementation_agent_advice(observe_message):
    system_prompt = load_prompt("loop_implementation_system_prompt.txt")
    task_prompt = load_prompt("loop_implementation_task_prompt.txt").replace(
        "{{VALIDATION_EVIDENCE}}", observe_message
    )
    return call_model(IMPLEMENTATION_MODEL, system_prompt, task_prompt, max_tokens=150)


def get_review_agent_advice(implementation_message, observe_message):
    system_prompt = load_prompt("loop_review_system_prompt.txt")
    task_prompt = (
        load_prompt("loop_review_task_prompt.txt")
        .replace("{{IMPLEMENTATION_RECOMMENDATION}}", implementation_message)
        .replace("{{VALIDATION_EVIDENCE}}", observe_message)
    )
    return call_model(REVIEW_MODEL, system_prompt, task_prompt, max_tokens=150)


def human_review():
    print()
    print("HUMAN REVIEW")
    print("1 - Accept")
    print("2 - Partially Accept")
    print("3 - Reject")

    decision = input("Decision: ").strip()

    if decision == "1":
        return "Accept"
    if decision == "2":
        return "Partially Accept"
    return "Reject"


def adapt(decision):
    print()
    if decision == "Accept":
        print("ADAPT: Apply the recommendation and rerun validation.")
    elif decision == "Partially Accept":
        print("ADAPT: Apply selected recommendations and rerun validation.")
    else:
        print("ADAPT: Keep the current implementation and document the rationale.")


def main():
    print("=" * 60)
    print("ASD RELEASE 0 AGENTIC LOOP - BUDGET & EXPENSE TRACKING")
    print("=" * 60)

    print()
    print("PLAN")
    print(PLAN)

    print()
    print("ACT")
    print("Validate the database contents and the live service endpoints")

    print()
    print("OBSERVE: Database Check")
    db_results, db_ok = observe_database()

    print()
    print("OBSERVE: Live Endpoint Check")
    live_results = observe_live_endpoints()

    observe_message = (
        "Database checks: " + "; ".join(db_results) + ". "
        "Live endpoint checks: " + "; ".join(live_results)
    )

    print()
    print("IMPLEMENTATION AGENT")
    print(f"Model: {IMPLEMENTATION_MODEL}")
    implementation_advice, implementation_error = get_implementation_agent_advice(
        observe_message
    )
    print()
    if implementation_advice:
        print(implementation_advice)
    else:
        print(implementation_error)
        implementation_advice = "Implementation agent unavailable."

    print()
    print("REVIEW AGENT")
    print(f"Model: {REVIEW_MODEL}")
    review_advice, review_error = get_review_agent_advice(
        implementation_advice, observe_message
    )
    print()
    if review_advice:
        print(review_advice)
    else:
        print(review_error)

    print()
    print("HUMAN DECISION")
    decision = human_review()
    print()
    print(f"Decision: {decision}")
    adapt(decision)

    print()
    print("LOOP COMPLETE")


if __name__ == "__main__":
    main()