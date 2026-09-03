import sqlite3

connection = sqlite3.connect('bookings.db')
connection.execute("PRAGMA foreign_keys = ON")
cursor = connection.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS Itineraries (
    itinerary_id INTEGER PRIMARY KEY AUTOINCREMENT,
    trip_id INTEGER,
    date TEXT NOT NULL,
    time TEXT,
    activity TEXT NOT NULL,
    location TEXT NOT NULL,
    notes TEXT
)''')


cursor.execute('''
CREATE TABLE IF NOT EXISTS Provider (
    provider_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    contact_info TEXT
)''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Bookings (
    booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
    trip_id INTEGER,
    provider_id INTEGER,
    status TEXT NOT NULL DEFAULT 'pending',
    cost INTEGER NOT NULL,
    booking_date TEXT NOT NULL,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (provider_id) REFERENCES Provider(provider_id)


)''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS BookingItems (
    booking_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL,
    itinerary_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,

    FOREIGN KEY (booking_id) REFERENCES Bookings(booking_id),
    
    FOREIGN KEY (itinerary_id) REFERENCES Itineraries(itinerary_id)
)''')


connection.commit()
connection.close()

print("Database created successfully.")