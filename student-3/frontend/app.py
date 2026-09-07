from flask import Flask, render_template, request
import os
import requests

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:5003")

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/<path:subpath>", methods=["GET", "POST"])
def proxy(subpath):
    try:
        resp = requests.request(
            request.method,
            f"{BACKEND_URL}/{subpath}",
            params=request.args,
            data=request.form,
            timeout=180,
        )
        return resp.text, resp.status_code
    except requests.RequestException:
        return "<p class='error'>Backend service is unavailable.</p>", 503


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3003, debug=True)
