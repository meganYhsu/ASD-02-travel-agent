from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/trips/<int:trip_id>")
def get_trip(trip_id):
    return jsonify({
        "trip_id": trip_id,
        "destination": "Tokyo",
        "start_date": "2026-09-01",
        "end_date": "2026-09-05",
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6004, debug=True)