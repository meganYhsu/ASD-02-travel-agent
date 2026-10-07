"""Student 1 - shared RAG integration checks.

Run with the database API (6001) and backend (5001) already started:
    python tests/test_rag.py

RAG_ENABLED=false (CI): the backend must refuse cleanly with "RAG is disabled".
RAG_ENABLED=true (local): the shared RAG server (7001) and Ollama must also be
running. A question about the seed data must come back grounded, with a
confidence rating and student-1 sources; an unrelated question must come back
as insufficient context.
"""

import os
import requests

BACKEND = os.getenv("BACKEND_URL", "http://127.0.0.1:5001")
RAG_ENABLED = os.getenv("RAG_ENABLED", "true").lower() not in ("false", "0", "no")


def ask(question):
    return requests.post(f"{BACKEND}/rag/ask", data={"question": question}, timeout=200)


def check(label, ok):
    print(f"  {label:44s} -> {'PASS' if ok else 'FAIL'}")
    return ok


def run():
    results = [
        check("reject empty question", ask("").status_code == 400),
        check("reject over-long question", ask("x" * 301).status_code == 400),
    ]

    if RAG_ENABLED:
        resp = ask("What dietary restriction does Traveller One have?")
        results.append(check("grounded answer with confidence",
                             resp.status_code == 200 and "Confidence:" in resp.text
                             and "Insufficient context" not in resp.text))
        results.append(check("answer cites student-1 data",
                             "student1-traveller-1" in resp.text))
        resp = ask("Who won the 1998 FIFA World Cup?")
        results.append(check("unrelated question -> insufficient context",
                             resp.status_code == 200 and "Insufficient context" in resp.text))
    else:
        resp = ask("What dietary restriction does Traveller One have?")
        results.append(check("RAG disabled response",
                             resp.status_code == 503 and "RAG is disabled" in resp.text))

    passed = sum(results)
    print(f"\n{passed} passed, {len(results) - passed} failed "
          f"(RAG {'enabled' if RAG_ENABLED else 'disabled'})")
    return passed == len(results)


if __name__ == "__main__":
    raise SystemExit(0 if run() else 1)
