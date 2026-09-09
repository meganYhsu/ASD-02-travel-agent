from flask import Flask, jsonify, request
import requests
from pathlib import Path
from llm_client import OLLAMA_MODEL, create_chat_completion
import os


app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL") or "http://127.0.0.1:5000"

BASE_DIR = Path(__file__).resolve().parent

BOOKING_PROMPT_FILE = (
    BASE_DIR
    / "prompts"
    / "booking_assistant_prompt.txt"
)


#itinerary routes Create, Read, Update, Delete (CRUD) operations
@app.route('/itineraries', methods=['GET'])
def get_itineraries():
    response = requests.get(f"{DATABASE_URL}/itineraries")
    return jsonify(response.json()), response.status_code


@app.route('/itineraries', methods=['POST'])
def create_itinerary():
    data = request.get_json()

    if not data:
            return jsonify({"error": "Missing required fields"}), 400
    

    required_fields = [
        'trip_id', 
        'date',
        'time', 
        'activity', 
        'location']

    for field in required_fields:
        if not data.get(field):
            return jsonify({"error": f"Missing required field: {field}"}), 400

    response = requests.post(f"{DATABASE_URL}/itineraries", json=data)
    return jsonify(response.json()), response.status_code


@app.route('/itineraries/<int:itinerary_id>', methods=['PUT'])
def update_itinerary(itinerary_id):
    data = request.get_json()

    if not data:
            return jsonify({"error": "Missing required fields"}), 400
    

    required_fields = [
        'trip_id', 
        'date',
        'time', 
        'activity', 
        'location']

    for field in required_fields:
        if not data.get(field):
            return jsonify({"error": f"Missing required field: {field}"}), 400

    response = requests.put(f"{DATABASE_URL}/itineraries/{itinerary_id}", json=data)
    return jsonify(response.json()), response.status_code


@app.route('/itineraries/<int:itinerary_id>', methods=['DELETE'])
def delete_itinerary(itinerary_id):
    response = requests.delete(f"{DATABASE_URL}/itineraries/{itinerary_id}")
    return jsonify(response.json()), response.status_code






#provider routes Create, Read, Update, Delete (CRUD) operations
@app.route('/provider', methods=['GET'])
def get_provider():
    response = requests.get(f"{DATABASE_URL}/provider")
    return jsonify(response.json()), response.status_code

@app.route('/provider', methods=['POST'])
def create_provider():  
    data = request.get_json()

    if not data:
            return jsonify({"error": "Missing required fields"}), 400
    

    required_fields = [
        'name', 
        'type', 
        'contact_info'
    ]

    for field in required_fields:
        if not data.get(field):
            return jsonify({"error": f"Missing required field: {field}"}), 400

    response = requests.post(f"{DATABASE_URL}/provider", json=data)
    return jsonify(response.json()), response.status_code


@app.route('/provider/<int:provider_id>', methods=['PUT'])
def update_provider(provider_id):   
    data = request.get_json()

    if not data:
            return jsonify({"error": "Missing required fields"}), 400
    

    required_fields = [
        'name', 
        'type', 
        'contact_info'
    ]

    for field in required_fields:
        if not data.get(field):
            return jsonify({"error": f"Missing required field: {field}"}), 400

    response = requests.put(f"{DATABASE_URL}/provider/{provider_id}", json=data)
    return jsonify(response.json()), response.status_code


@app.route('/provider/<int:provider_id>', methods=['DELETE'])
def delete_provider(provider_id):  
    response = requests.delete(f"{DATABASE_URL}/provider/{provider_id}")
    return jsonify(response.json()), response.status_code






#bookings routes Create, Read, Update, Delete (CRUD) operations
@app.route('/bookings', methods=['GET'])
def get_bookings():
    response = requests.get(f"{DATABASE_URL}/bookings")
    return jsonify(response.json()), response.status_code


@app.route('/bookings', methods=['POST'])
def create_booking():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Missing required fields"}), 400

    required_fields = [
        'trip_id',  
        'provider_id',
        'booking_date',
        'status',
        'cost',
        'create_time'
    ]

    if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required field"}), 400

    if data['status'] not in ['pending', 'confirmed', 'cancelled']:
        return jsonify({"error": "Invalid status value"}), 400

    if data['cost'] < 0:
        return jsonify({"error": "Cost cannot be negative"}), 400
    

    response = requests.post(f"{DATABASE_URL}/bookings", json=data)
    return jsonify(response.json()), response.status_code


@app.route('/bookings/<int:booking_id>', methods=['PUT'])
def update_booking(booking_id):
    data = request.get_json()

    if not data:
            return jsonify({"error": "Missing required fields"}), 400

    required_fields = [
        'trip_id',
        'provider_id',
        'booking_date',
        'status',
        'cost',
        'create_time'
    ]

    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    if data['status'] not in ['pending', 'confirmed', 'cancelled']:
        return jsonify({"error": "Invalid status value"}), 400

    if data['cost'] < 0:
        return jsonify({"error": "Cost cannot be negative"}), 400

    response = requests.put(f"{DATABASE_URL}/bookings/{booking_id}", json=data)
    return jsonify(response.json()), response.status_code

@app.route('/bookings/<int:booking_id>', methods=['DELETE'])
def delete_booking(booking_id):
    response = requests.delete(f"{DATABASE_URL}/bookings/{booking_id}")
    return jsonify(response.json()), response.status_code


@app.route('/bookings/from-itinerary', methods=['POST'])
def create_booking_from_itinerary():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Missing required fields"}), 400

    required_fields = [
        'trip_id',
        'provider_id',
        'itinerary_id',
        'booking_date',
        'status',
        'cost',
        'create_time',
        'quantity'
    ]

    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    if data['status'] not in ['pending', 'confirmed', 'cancelled']:
        return jsonify({"error": "Invalid status value"}), 400

    if data['cost'] < 0:
        return jsonify({"error": "Cost cannot be negative"}), 400

    if not isinstance(data['quantity'], int) or data['quantity'] <= 0:
        return jsonify({"error": "Quantity must be a positive integer"}), 400

    booking_data = {
        'trip_id': data['trip_id'],
        'provider_id': data['provider_id'],
        'booking_date': data['booking_date'],
        'status': data['status'],
        'cost': data['cost'],
        'create_time': data['create_time']
    }

    booking_response = requests.post(f"{DATABASE_URL}/bookings", json=booking_data) 

    if booking_response.status_code != 201:
        return jsonify({"error": "Failed to create booking"}), booking_response.status_code

    booking_id = booking_response.json().get('booking_id')
    if not booking_id:
            return jsonify({"error": "Failed to create booking"}), 500  

    booking_item_data = {
        'booking_id': booking_id,
        'itinerary_id': data['itinerary_id'],
        'quantity': data['quantity']
    }

    booking_item_response = requests.post(f"{DATABASE_URL}/booking_items", json=booking_item_data)  

    if booking_item_response.status_code != 201: 
        return jsonify({"error": "Failed to create booking item"}), booking_item_response.status_code

    return jsonify({"message": "Booking and booking item created successfully", "booking_id": booking_id}), 201




#A helpfuntion 
def is_provider_suitable(selected_itinerary, recommended_provider, providers):

    activity = selected_itinerary['activity'].lower()

    recommended_name = recommended_provider['name'].lower()
    recommended_type = recommended_provider['type'].lower()

    # Current provider directly matches the activity
    if recommended_name in activity or activity in recommended_name:
        return True

    if recommended_type in activity:
        return True

    # Check whether another provider is a clearly better match
    for provider in providers:

        provider_name = provider['name'].lower()
        provider_type = provider['type'].lower()

        if provider['provider_id'] == recommended_provider['provider_id']:
            continue

        if provider_name in activity or activity in provider_name:
            return False

        if provider_type in activity:
            return False

    # No clearly better provider found
    return True


#AI assistant endpoint
@app.route('/ai/match-provider', methods=['POST'])
def match_provider():

    data = request.get_json()

    if not data or 'itinerary_id' not in data:
        return jsonify({
            "error": "itinerary_id is required"
        }), 400


    itinerary_id = data['itinerary_id']


    # PLAN
    print("[PLAN] Retrieve itinerary and provider information.")


    try:
        itinerary_response = requests.get(
            f"{DATABASE_URL}/itineraries",
            timeout=5
        )

        provider_response = requests.get(
            f"{DATABASE_URL}/provider",
            timeout=5
        )

        itinerary_response.raise_for_status()
        provider_response.raise_for_status()

        itineraries = itinerary_response.json()
        providers = provider_response.json()

    except requests.RequestException as exc:
        return jsonify({
            "error": "Failed to retrieve booking context",
            "details": str(exc)
        }), 503


    selected_itinerary = None

    for itinerary in itineraries:
        if itinerary['itinerary_id'] == itinerary_id:
            selected_itinerary = itinerary
            break


    if selected_itinerary is None:
        return jsonify({
            "error": "Itinerary not found"
        }), 404


    if not providers:
        return jsonify({
            "error": "No providers available"
        }), 404

# ACT

    system_prompt = BOOKING_PROMPT_FILE.read_text(
        encoding="utf-8"
    ).strip()


    provider_context = ""

    for provider in providers:
        provider_context += (
            f"Provider ID: {provider['provider_id']}\n"
            f"Name: {provider['name']}\n"
            f"Type: {provider['type']}\n"
            f"Contact: {provider.get('contact_info', '')}\n\n"
        )


    user_prompt = f"""
    Selected Itinerary:
    Activity: {selected_itinerary['activity']}
    Location: {selected_itinerary['location']}
    Date: {selected_itinerary['date']}
    Time: {selected_itinerary.get('time', '')}
    Notes: {selected_itinerary.get('notes', '')}

    Available Providers:
    {provider_context}"""


    # Maximum two recommendation attempts
    for attempt in range(2):

        print(
            f"[ACT] Attempt {attempt + 1}: "
            "Send booking context to Qwen."
        )

        try:
            answer = create_chat_completion(
                [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                max_tokens=150,
                temperature=0.2,
                model=OLLAMA_MODEL
            )

        except Exception as exc:
            return jsonify({
                "error": "AI request failed",
                "details": str(exc)
            }), 503


        # OBSERVE
        print(
            "[OBSERVE] Validate AI provider recommendation."
        )

        provider_id = None
        reason = ""
        reading_reason = False

        for line in answer.splitlines():

            line = line.strip()

            if line.lower().startswith("provider id:"):

                value = line.split(":", 1)[1].strip()

                try:
                    provider_id = int(value)

                except ValueError:
                    provider_id = None

            elif line.lower().startswith("reason:"):

                reason = line.split(":", 1)[1].strip()
                reading_reason = True

            elif reading_reason and line:

                reason += " " + line


        recommended_provider = None

        for provider in providers:

            if provider['provider_id'] == provider_id:

                recommended_provider = provider
                break


        # Check whether provider exists
        if recommended_provider is None:

            print(
                "[ADAPT] Provider ID is invalid. "
                "Retry recommendation."
            )

            user_prompt += f"""
            The previous recommendation was invalid because the provider
            does not exist in the supplied provider list.
            Previous AI response:
            {answer}
            
            Choose another provider using only the supplied provider data.
            """

            continue


        # OBSERVE provider suitability using live application data
        print(
            "[OBSERVE] Compare recommendation "
            "with live provider data."
        )

        is_suitable = is_provider_suitable(
            selected_itinerary,
            recommended_provider,
            providers
        )


        # ADAPT
        if is_suitable:

            print(
                "[ADAPT] Provider recommendation accepted."
            )

            return jsonify({
                "itinerary": selected_itinerary,
                "recommended_provider": recommended_provider,
                "reason": reason,
                "agentic_loop": {
                    "plan":
                        "Retrieve itinerary and provider information",
                    "act":
                        f"Ask Qwen for a provider recommendation "
                        f"(attempt {attempt + 1})",
                    "observe":
                        "Compare the recommendation with "
                        "live provider data",
                    "adapt":
                        "Accept a suitable provider or retry "
                        "with the previous recommendation excluded"
                }
            }), 200


        print(
            "[ADAPT] A more relevant provider exists. "
            "Refine context and retry."
        )

        user_prompt += f"""
        The previous provider recommendation was not suitable.
        
        Previous provider:
        {recommended_provider['name']}
        
        Provider type:
        {recommended_provider['type']}
        
        Do not recommend this provider again.
        Review the supplied provider names and types again and choose
        a provider that more directly matches the selected itinerary activity:
        
        {selected_itinerary['activity']} """

# Both attempts failed
    print(
        "[ADAPT] No suitable provider found after two attempts."
        )

    return jsonify({
        "error":
        "AI could not find a suitable provider after two attempts."
        }), 422

    








#booking_item routes Create, Read, Update, Delete (CRUD) operations
@app.route('/booking_items', methods=['GET'])
def get_booking_items():
    response = requests.get(f"{DATABASE_URL}/booking_items")
    return jsonify(response.json()), response.status_code


@app.route('/booking_items', methods=['POST'])
def create_booking_item():
    data = request.get_json()

    if not data:
            return jsonify({"error": "Missing required fields"}), 400

    required_fields = [
        'booking_id',
        'itinerary_id',
        'quantity'
    ]

    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    if not isinstance(data['quantity'], int) or data['quantity'] <= 0:
        return jsonify({"error": "Quantity must be a positive integer"}), 400

    
    response = requests.post(f"{DATABASE_URL}/booking_items", json=data)
    return jsonify(response.json()), response.status_code   

@app.route('/booking_items/<int:booking_item_id>', methods=['PUT'])
def update_booking_item(booking_item_id):
    data = request.get_json()

    if not data:
        return jsonify({"error": "Missing required fields"}), 400

    required_fields = [
        'booking_id',
        'itinerary_id',
        'quantity'
    ]

    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    if not isinstance(data['quantity'], int) or data['quantity'] <= 0:
        return jsonify({"error": "Quantity must be a positive integer"}), 400

    response = requests.put(f"{DATABASE_URL}/booking_items/{booking_item_id}", json=data)
    return jsonify(response.json()), response.status_code


@app.route('/booking_items/<int:booking_item_id>', methods=['DELETE'])
def delete_booking_item(booking_item_id):
    response = requests.delete(f"{DATABASE_URL}/booking_items/{booking_item_id}")
    return jsonify(response.json()), response.status_code






if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)