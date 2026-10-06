from __future__ import annotations

import math
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any

import requests
from flask import Flask, jsonify, request


WORD_RE = re.compile(r"[a-z0-9][a-z0-9'-]+")
DEFAULT_DOCUMENTS = Path(__file__).with_name("knowledge")


def words(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


def split_document(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    sections: list[dict[str, str]] = []
    heading = path.stem.replace("-", " ").title()
    paragraphs: list[str] = []

    def flush() -> None:
        if paragraphs:
            sections.append({"source": path.name, "section": heading, "text": "\n".join(paragraphs)})
            paragraphs.clear()

    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if not block:
            continue
        if block.startswith("#"):
            flush()
            heading = block.lstrip("# ").strip()
        else:
            paragraphs.append(block)
    flush()
    return sections


class Retriever:
    def __init__(self, document_paths: list[Path]):
        self.chunks: list[dict[str, Any]] = []
        for root in document_paths:
            files = sorted(root.rglob("*.md")) if root.is_dir() else [root]
            for path in files:
                if path.is_file():
                    for chunk in split_document(path):
                        chunk["terms"] = Counter(words(f"{chunk['section']} {chunk['text']}"))
                        self.chunks.append(chunk)

        self.document_frequency = Counter()
        for chunk in self.chunks:
            self.document_frequency.update(chunk["terms"].keys())

    def search(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
        query_terms = Counter(words(query))
        scores: list[tuple[float, dict[str, Any]]] = []
        total = max(len(self.chunks), 1)
        for chunk in self.chunks:
            score = 0.0
            for term, query_count in query_terms.items():
                term_count = chunk["terms"].get(term, 0)
                if term_count:
                    inverse_frequency = math.log((total + 1) / (self.document_frequency[term] + 1)) + 1
                    score += query_count * (1 + math.log(term_count)) * inverse_frequency
            if score:
                scores.append((score, chunk))
        scores.sort(key=lambda item: (-item[0], item[1]["source"], item[1]["section"]))
        return [
            {"source": chunk["source"], "section": chunk["section"], "text": chunk["text"], "score": round(score, 3)}
            for score, chunk in scores[:limit]
        ]


def configured_paths() -> list[Path]:
    value = os.getenv("RAG_DOCUMENT_PATHS", str(DEFAULT_DOCUMENTS))
    return [Path(item) for item in value.split(os.pathsep) if item]


def generate_answer(question: str, sources: list[dict[str, Any]]) -> str | None:
    if os.getenv("RAG_GENERATION_ENABLED", "true").lower() not in {"1", "true", "yes"}:
        return None
    context = "\n\n".join(
        f"SOURCE: {item['source']} / {item['section']}\n{item['text']}" for item in sources
    )
    prompt = (
        "You are a travel preparation assistant. Answer only from the supplied context. "
        "If the context is insufficient, say so. Keep the answer concise and do not present "
        "demonstration entry requirements as official advice.\n\n"
        f"QUESTION: {question}\n\nCONTEXT:\n{context}"
    )
    try:
        response = requests.post(
            f"{os.getenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434').rstrip('/')}/api/generate",
            json={
                "model": os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 300},
            },
            timeout=int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120")),
        )
        response.raise_for_status()
        answer = response.json().get("response", "").strip()
        return answer or None
    except (requests.RequestException, ValueError):
        return None


def create_app(retriever: Retriever | None = None) -> Flask:
    app = Flask(__name__)
    app.config["RETRIEVER"] = retriever or Retriever(configured_paths())

    @app.get("/health")
    def health():
        active: Retriever = app.config["RETRIEVER"]
        return jsonify({"status": "ok", "service": "shared-rag", "chunks": len(active.chunks)})

    @app.post("/query")
    def query():
        payload = request.get_json(silent=True)
        question = payload.get("question", "").strip() if isinstance(payload, dict) else ""
        if not question:
            return jsonify({"success": False, "error": "question is required"}), 400
        if len(question) > 2000:
            return jsonify({"success": False, "error": "question must be 2000 characters or fewer"}), 400

        active: Retriever = app.config["RETRIEVER"]
        sources = active.search(question)
        if not sources:
            return jsonify(
                {
                    "success": True,
                    "data": {
                        "answer": "I could not find relevant information in the approved knowledge base.",
                        "sources": [],
                        "mode": "no_match",
                    },
                }
            )

        answer = generate_answer(question, sources)
        mode = "generated" if answer else "retrieval_only"
        if not answer:
            answer = sources[0]["text"]
        public_sources = [
            {"source": item["source"], "section": item["section"], "score": item["score"]}
            for item in sources
        ]
        return jsonify(
            {
                "success": True,
                "data": {
                    "answer": answer,
                    "sources": public_sources,
                    "mode": mode,
                    "disclaimer": "Verify travel and entry requirements against official sources.",
                },
            }
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "7005")))