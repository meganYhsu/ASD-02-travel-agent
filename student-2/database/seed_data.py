import sqlite3

conn = sqlite3.connect('bookings.db')
conn.execute("PRAGMA foreign_keys = ON")
cursor = conn.cursor()

itineraries = [
    (1, 1, '2023-10-01', '10:00', 'sydneyopera house', 'sydney', 'Notes 1'),
    (2, 1, '2023-10-01', '15:00', 'sydney tower eye', 'sydney', 'Notes 2'),
    (3, 1, '2023-10-01', '15:40', 'sydney tower eye skywalk', 'sydney', 'Notes 3'),
    (4, 2, '2023-10-02', '09:00', 'SEA LIFE sydney aquarium', 'sydney', 'Notes 4'),
    (5, 2, '2023-10-02', '14:00', 'madame tussauds sydney', 'sydney', 'Notes 5'),
    (6, 3, '2023-10-03', '11:00', 'wild life sydney zoo', 'sydney', 'Notes 6'),
    (7, 4, '2023-10-04', '12:00', 'taronga zoo', 'sydney', 'Notes 7'),
    (8, 4, '2023-10-04', '14:00', 'luna park', 'sydney', 'Notes 8'),
    (9, 4, '2023-10-05', '19:00', 'sydney observatory stargazing', 'sydney', 'Notes 9'),
    (10, 5, '2023-10-05', '20:00', 'great opera hits', 'sydney', 'Notes 10')
]


Provider = [
    (1, 'Sydney Opera House', 'attraction', 'info@sydneyoperahouse.com'),
    (2, 'Sydney Tower Eye', 'attraction', 'info@sydneytowereye.com.au'),
    (3, 'Sydney Tower Eye Skywalk', 'experience', 'info@sydneytowereye.com.au'),
    (4, 'SEA LIFE Sydney Aquarium', 'aquarium', 'info@sealifesydney.com.au'),
    (5, 'Madame Tussauds Sydney', 'museum', 'info@madametussauds.com.au'),
    (6, 'WILD LIFE Sydney Zoo', 'zoo', 'info@wildlifesydney.com.au'),
    (7, 'Taronga Zoo Sydney', 'zoo', 'info@taronga.org.au'),
    (8, 'Luna Park Sydney', 'amusement park', 'info@lunaparksydney.com'),
    (9, 'Sydney Observatory', 'experience', 'info@sydneyobservatory.com.au'),
    (10, 'Sydney Opera House', 'performance', 'tickets@sydneyoperahouse.com')
]


Bookings = [
    (1, 1, 1, '2023-10-01', 'confirmed', 45.00, '2023-09-20 10:00:00'),
    (2, 1, 2, '2023-10-01', 'confirmed', 29.00, '2023-09-20 10:10:00'),
    (3, 1, 3, '2023-10-01', 'confirmed', 95.00, '2023-09-20 10:20:00'),
    (4, 2, 4, '2023-10-02', 'confirmed', 39.00, '2023-09-21 09:00:00'),
    (5, 2, 5, '2023-10-02', 'pending', 39.00, '2023-09-21 09:15:00'),
    (6, 3, 6, '2023-10-03', 'confirmed', 35.00, '2023-09-22 11:00:00'),
    (7, 4, 7, '2023-10-04', 'confirmed', 51.30, '2023-09-23 12:00:00'),
    (8, 4, 8, '2023-10-04', 'pending', 60.00, '2023-09-23 12:30:00'),
    (9, 4, 9, '2023-10-05', 'confirmed', 40.00, '2023-09-24 14:00:00'),
    (10, 5, 10, '2023-10-05', 'confirmed', 69.00, '2023-09-24 15:00:00')
]


BookingItems = [
    (1, 1, 1, 2),
    (2, 2, 2, 2),
    (3, 3, 3, 2),
    (4, 4, 4, 2),
    (5, 5, 5, 2),
    (6, 6, 6, 2),
    (7, 7, 7, 2),
    (8, 8, 8, 2),
    (9, 9, 9, 2),
    (10, 10, 10, 2)   
]

cursor.executemany(
    """
    INSERT INTO Itineraries 
    (itinerary_id, trip_id, date, time, activity, location, notes) 
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, 
    itineraries
)


cursor.executemany(
    """
    INSERT INTO Provider 
    (provider_id, name, type, contact_info) 
    VALUES (?, ?, ?, ?)
    """, 
    Provider
)

cursor.executemany(
    """
    INSERT INTO Bookings 
    (booking_id, trip_id, provider_id, booking_date, status, cost, create_time) 
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, 
    Bookings
)

cursor.executemany(
    """
    INSERT INTO BookingItems 
    (booking_item_id, booking_id, itinerary_id, quantity) 
    VALUES (?, ?, ?, ?)
    """, 
    BookingItems
)


print("Inserted itineraries:", cursor.rowcount)

conn.commit()
conn.close()

print("Seed data inserted successfully.")
