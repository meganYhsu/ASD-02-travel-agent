from flask import Flask, request, jsonify

from rag_pipeline import (
    refresh_corpus,
    retrieve_context,
    answer_question,
)

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "shared-rag-server"
    })


@app.route("/rag/refresh", methods=["POST"])
def rag_refresh():
    result = refresh_corpus(caller="http")
    return jsonify(result)


@app.route("/rag/retrieve", methods=["POST"])
def rag_retrieve():
    data = request.get_json(silent=True) or {}

    query = data.get("query", "").strip()
    k = data.get("k", 5)

    if not query:
        return jsonify({
            "status": "error",
            "error": "query is required"
        }), 400

    result = retrieve_context(
        query=query,
        k=k,
        caller="http"
    )

    return jsonify(result)


@app.route("/rag/answer", methods=["POST"])
def rag_answer():
    data = request.get_json(silent=True) or {}

    query = data.get("query", "").strip()
    k = data.get("k", 5)

    if not query:
        return jsonify({
            "status": "error",
            "error": "query is required"
        }), 400

    result = answer_question(
        query=query,
        k=k,
        caller="http"
    )

    return jsonify(result)


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=7001,
        debug=True
    )