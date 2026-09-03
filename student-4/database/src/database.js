const fs = require("fs");
const path = require("path");
const Database = require("better-sqlite3");

const dataDir = path.resolve(__dirname, "../data");
const dbPath = path.join(dataDir, "traveller-itinerary-details.sqlite");

fs.mkdirSync(dataDir, { recursive: true });

const db = new Database(dbPath);

db.pragma("foreign_keys = ON");

db.exec(`
  CREATE TABLE IF NOT EXISTS itinerary (
    itinerary_id INTEGER PRIMARY KEY AUTOINCREMENT,
    destination TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    budget TEXT NOT NULL,
    travel_group TEXT,
    travel_style TEXT NOT NULL,
    requirements TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE IF NOT EXISTS activity (
    activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
    itinerary_id INTEGER NOT NULL,
    day_no INTEGER NOT NULL,
    date TEXT NOT NULL,
    location TEXT NOT NULL,
    time TEXT NOT NULL,
    cost TEXT,
    note TEXT,
    FOREIGN KEY (itinerary_id) REFERENCES itinerary(itinerary_id)
  );
`);

module.exports = db;
module.exports.dbPath = dbPath;

