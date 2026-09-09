from flask import Flask, jsonify

app = Flask(__name__)

ITINERARIES = {
    1: {
        "itinerary_id": 1,
        "destination": "Japan Test Seed",
        "start_date": "2026-10-01",
        "end_date": "2026-10-06",
        "budget": "AUD 4200",
        "travel_group": "solo",
        "travel_style": "Sightseeing Travel",
    },
    2: {
        "itinerary_id": 2,
        "destination": "Italy City Break",
        "start_date": "2026-10-08",
        "end_date": "2026-10-13",
        "budget": "AUD 5100",
        "travel_group": "friends",
        "travel_style": "Cultural Travel",
    },
}


@app.route("/itineraries/<int:itinerary_id>")
def get_itinerary(itinerary_id):
    itinerary = ITINERARIES.get(itinerary_id)
    if itinerary is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(itinerary)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6004, debug=True)