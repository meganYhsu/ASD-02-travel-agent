from flask import Flask, render_template, request, redirect, url_for
import requests
import os

app = Flask(__name__)

BACKEND_URL = os.getenv("BACKEND_URL") or "http://127.0.0.1:5001"

print("BACKEND_URL =", BACKEND_URL)


@app.route('/itinerary')
def itinerary():
    response = requests.get(f"{BACKEND_URL}/itineraries")
    itinerary_list = response.json()

    return render_template(
        'itinerary.html',
        itineraries=itinerary_list
    )


@app.route('/itinerary/add', methods=['POST'])
def add_itinerary():
    data = {
        'trip_id': request.form['trip_id'],
        'date': request.form['date'],
        'time': request.form['time'],
        'activity': request.form['activity'],
        'location': request.form['location'],
        'notes': request.form['notes']
    }

    requests.post(
        f"{BACKEND_URL}/itineraries",
        json=data
    )

    return redirect(url_for('itinerary'))


@app.route('/itinerary/update/<int:itinerary_id>', methods=['POST'])
def update_itinerary(itinerary_id):
    data = {
        'trip_id': request.form['trip_id'],
        'date': request.form['date'],
        'time': request.form['time'],
        'activity': request.form['activity'],
        'location': request.form['location'],
        'notes': request.form['notes']
    }

    requests.put(
        f"{BACKEND_URL}/itineraries/{itinerary_id}",
        json=data
    )

    return redirect(url_for('itinerary'))


@app.route('/itinerary/delete/<int:itinerary_id>', methods=['POST'])
def delete_itinerary(itinerary_id):

    requests.delete(
        f"{BACKEND_URL}/itineraries/{itinerary_id}"
    )

    return redirect(url_for('itinerary'))



@app.route('/booking')
def booking():
    booking_response = requests.get(f"{BACKEND_URL}/bookings")
    bookings = booking_response.json()

    provider_response = requests.get(f"{BACKEND_URL}/provider")
    providers = provider_response.json()

    itinerary_response = requests.get(f"{BACKEND_URL}/itineraries")
    itineraries = itinerary_response.json()

    booking_item_response = requests.get( f"{BACKEND_URL}/booking_items")
    booking_items = booking_item_response.json()

    provider_names = {
    provider['provider_id']: provider['name']
    for provider in providers
    }

    itinerary_activities = {
    itinerary['itinerary_id']: itinerary['activity']
    for itinerary in itineraries
    }

    booking_activities = {}

    for item in booking_items:
        booking_id = item['booking_id']
        itinerary_id = item['itinerary_id']

        booking_activities[booking_id] = (
            itinerary_activities.get (
                itinerary_id,
                'Unknown Activity'
            )
        )

    return render_template(
        'booking.html',
        bookings=bookings,
        providers=providers,
        itineraries=itineraries,
        provider_names=provider_names,
        booking_activities=booking_activities
    )



@app.route('/booking/add', methods=['POST'])
def add_booking():
    data = {
        'trip_id': int(request.form['trip_id']),
        'provider_id': int(request.form['provider_id']),
        'itinerary_id': int(request.form['itinerary_id']),
        'booking_date': request.form['booking_date'],
        'status': request.form['status'],
        'cost': float(request.form['cost']),
        'create_time': request.form['create_time'],
        'quantity': int(request.form['quantity'])
    }

    response = requests.post(
        f"{BACKEND_URL}/bookings/from-itinerary",
        json=data
    )

    print("ADD STATUS:", response.status_code)
    print("ADD RESPONSE:", response.text)

    return redirect(url_for('booking'))


@app.route('/booking/update/<int:booking_id>', methods=['POST'])
def update_booking(booking_id):
    data = {
        'trip_id': int(request.form['trip_id']),
        'provider_id': int(request.form['provider_id']),
        'booking_date': request.form['booking_date'],
        'status': request.form['status'],
        'cost': float(request.form['cost']),
        'create_time': request.form['create_time']
    }

    response = requests.put(
        f"{BACKEND_URL}/bookings/{booking_id}",
        json=data
    )

    print("UPDATE STATUS:", response.status_code)
    print("UPDATE RESPONSE:", response.text)

    return redirect(url_for('booking'))

@app.route('/booking/delete/<int:booking_id>', methods=['POST'])
def delete_booking(booking_id):

    response = requests.delete(
        f"{BACKEND_URL}/bookings/{booking_id}"
    )

    print("DELETE STATUS:", response.status_code)
    print("DELETE RESPONSE:", response.text)

    return redirect(url_for('booking'))


#booking AI agent
@app.route('/booking/ai-match', methods=['POST'])
def ai_match_provider():
    itinerary_id = request.form.get('itinerary_id')

    if not itinerary_id:
        return """
            <div>
                <strong>Error:</strong> Please select an itinerary.
            </div>
        """, 400

    try:
        response = requests.post(
            f"{BACKEND_URL}/ai/match-provider",
            json={
                "itinerary_id": int(itinerary_id)
            },
            timeout=30
        )

        data = response.json()

    except requests.RequestException:
        return """
            <div>
                <strong>Error:</strong> AI service is unavailable.
            </div>
        """, 503

    if response.status_code == 422:
            return """
            <div>
            <h3>AI Booking Recommendation</h3>
            <p><strong>No suitable provider found.</strong></p>
            <p>
                The AI could not find a suitable provider for this itinerary
                from the currently available providers.
            </p>
            </div>
            """

    if response.status_code != 200:
        error_message = data.get(
            'error',
            'Unable to generate recommendation.'
        )

        return f"""
            <div>
                <strong>Error:</strong> {error_message}
            </div>
        """, response.status_code

    provider = data['recommended_provider']
    reason = data['reason']
    itinerary_id = data['itinerary']['itinerary_id']

    return f"""
    <div>
        <h3>AI Booking Recommendation</h3>

        <p>
            <strong>Recommended Provider:</strong>
            {provider['name']}
        </p>

        <p>
            <strong>Provider Type:</strong>
            {provider['type']}
        </p>

        <p>
            <strong>Reason:</strong>
            {reason}
        </p>

        <button
            type="button"
            onclick="useAIProvider(
                {itinerary_id},
                {provider['provider_id']}
            )"
        >
            Use This Provider
        </button>
    </div>
    """


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)