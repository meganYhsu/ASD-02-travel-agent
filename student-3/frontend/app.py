from flask import Flask, jsonify, render_template, request, send_from_directory
import os
import requests

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:5003")
# Longer than the backend's wait for the shared Multi-Agent server (420 s)
PROXY_TIMEOUT_SECONDS = int(os.getenv("PROXY_TIMEOUT_SECONDS", "450"))
# Public address of the shared home page (navigation bar and shared CSS).
# Local default matches docker-compose; in AWS it is the load balancer URL.
SHARED_HOME_URL = os.getenv("SHARED_HOME_URL", "http://127.0.0.1:8080").rstrip("/")

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html", shared_home_url=SHARED_HOME_URL)


@app.route("/health")
def health():
    """Load-balancer / ECS health check (does not depend on the backend)."""
    return jsonify({"service": "student-3-frontend", "status": "ok"})


@app.route("/css/<path:filename>")
def css(filename):
    return send_from_directory("static", filename)


@app.route("/api/<path:subpath>", methods=["GET", "POST"])
def proxy(subpath):
    try:
        resp = requests.request(
            request.method,
            f"{BACKEND_URL}/{subpath}",
            params=request.args,
            data=request.form,
            timeout=PROXY_TIMEOUT_SECONDS,
        )
        return resp.text, resp.status_code
    except requests.RequestException:
        return "<p class='error'>Backend service is unavailable.</p>", 503


if __name__ == "__main__":
    # Direct runs (python app.py) listen on 127.0.0.1 unless FLASK_HOST is set,
    # and the debugger stays off unless FLASK_DEBUG=true. Containers start
    # gunicorn instead (see the Dockerfile).
    app.run(host=os.getenv("FLASK_HOST", "127.0.0.1"), port=3003,
            debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")