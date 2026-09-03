from flask import Flask, jsonify, request
import sqlite3

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('bookings.db')
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# Itinerary endpoints
@app.route('/itineraries', methods=['GET'])
def get_itineraries():
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM Itineraries').fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route('/itineraries', methods=['POST'])
def create_itinerary():
    data = request.get_json()
    conn = get_db_connection()
    conn.execute('INSERT INTO Itineraries (trip_id, date, time, activity, location, notes) VALUES (?, ?, ?, ?, ?, ?)',
                 (data['trip_id'], data['date'], data['time'], data['activity'], data['location'], data['notes']))
    conn.commit()
    conn.close()
    return jsonify({"message": "Itinerary created successfully"}), 201

@app.route('/itineraries/<int:itinerary_id>', methods=['PUT'])
def update_itinerary(itinerary_id):
    data = request.get_json()
    conn = get_db_connection()
    conn.execute('UPDATE Itineraries SET trip_id=?, date=?, time=?, activity=?, location=?, notes=? WHERE itinerary_id=?',
                 (data['trip_id'], data['date'], data['time'], data['activity'], data['location'], data['notes'], itinerary_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Itinerary updated successfully"}), 200

@app.route('/itineraries/<int:itinerary_id>', methods=['DELETE'])
def delete_itinerary(itinerary_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM Itineraries WHERE itinerary_id=?', (itinerary_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Itinerary deleted successfully"}), 200



#Provider endpoints
@app.route('/provider', methods=['GET'])
def get_providers():
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM Provider').fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route('/provider', methods=['POST'])
def create_provider():
    data = request.get_json()
    conn = get_db_connection()
    conn.execute('INSERT INTO Provider (name, type, contact_info) VALUES (?, ?, ?)',
                 (data['name'], data['type'], data['contact_info']))
    conn.commit()
    conn.close()
    return jsonify({"message": "Provider created successfully"}), 201

@app.route('/provider/<int:provider_id>', methods=['PUT'])
def update_provider(provider_id):   
    data = request.get_json()
    conn = get_db_connection()
    conn.execute('UPDATE Provider SET name=?, type=?, contact_info=? WHERE provider_id=?',
                 (data['name'], data['type'], data['contact_info'], provider_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Provider updated successfully"}), 200

@app.route('/provider/<int:provider_id>', methods=['DELETE'])
def delete_provider(provider_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM Provider WHERE provider_id=?', (provider_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Provider deleted successfully"}), 200



#Bookings endpoints
@app.route('/bookings', methods=['GET'])
def get_bookings():
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM Bookings').fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route('/bookings', methods=['POST'])
def create_booking():
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('INSERT INTO Bookings (trip_id, provider_id, booking_date, status, cost, create_time) VALUES (?, ?, ?, ?, ?, ?)',
                 (data['trip_id'], data['provider_id'], data['booking_date'], data['status'], data['cost'], data['create_time']))

    booking_id = cursor.lastrowid  # Get the last inserted booking_id
    conn.commit()
    conn.close()
    return jsonify({"message": "Booking created successfully", "booking_id": booking_id}), 201

@app.route('/bookings/<int:booking_id>', methods=['PUT'])
def update_booking(booking_id):
    data = request.get_json()
    conn = get_db_connection()
    conn.execute('UPDATE Bookings SET trip_id=?, provider_id=?, booking_date=?, status=?, cost=?, create_time=? WHERE booking_id=?',
                 (data['trip_id'], data['provider_id'], data['booking_date'], data['status'], data['cost'], data['create_time'], booking_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Booking updated successfully"}), 200

@app.route('/bookings/<int:booking_id>', methods=['DELETE'])
def delete_booking(booking_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM Bookings WHERE booking_id=?', (booking_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Booking deleted successfully"}), 200


#BookingItems endpoints
@app.route('/booking_items', methods=['GET'])
def get_booking_items():
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM BookingItems').fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route('/booking_items', methods=['POST'])
def create_booking_item():
    data = request.get_json()
    conn = get_db_connection()
    conn.execute('INSERT INTO BookingItems (booking_id, itinerary_id, quantity) VALUES (?, ?, ?)',
                 (data['booking_id'], data['itinerary_id'], data['quantity']))
    conn.commit()
    conn.close()
    return jsonify({"message": "Booking item created successfully"}), 201

@app.route('/booking_items/<int:booking_item_id>', methods=['PUT'])
def update_booking_item(booking_item_id):
    data = request.get_json()
    conn = get_db_connection()
    conn.execute('UPDATE BookingItems SET booking_id=?, itinerary_id=?, quantity=? WHERE booking_item_id=?',
                 (data['booking_id'], data['itinerary_id'], data['quantity'], booking_item_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Booking item updated successfully"}), 200

@app.route('/booking_items/<int:booking_item_id>', methods=['DELETE'])
def delete_booking_item(booking_item_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM BookingItems WHERE booking_item_id=?', (booking_item_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Booking item deleted successfully"}), 200



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

