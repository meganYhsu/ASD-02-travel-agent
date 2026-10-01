"""Student 1 - Traveler Preferences Database API (port 6001)

This service SOLELY owns preferences.db. No other service may open the
SQLite file directly - all access goes through these HTTP endpoints.
Responses are JSON because the callers are other services, not browsers.
Every statement is parameterised, and every write is validated first.
"""

from flask import Flask, jsonify, request
from pathlib import Path
import os
import re
import sqlite3

DB_PATH = Path(os.getenv("DATABASE_PATH", Path(__file__).with_name("preferences.db")))
PORT = int(os.getenv("PORT", "6001"))

TRAVEL_STYLES = ("budget", "mid-range", "luxury")
PACES = ("relaxed", "balanced", "packed")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

app = Flask(__name__)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ---------------------------------------------------------------- schema + seed
def init_db():
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS Travelers (
        traveler_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        name          TEXT NOT NULL,
        email         TEXT NOT NULL UNIQUE,
        home_location TEXT NOT NULL,
        travel_style  TEXT NOT NULL DEFAULT 'mid-range'
                      CHECK (travel_style IN ('budget','mid-range','luxury'))
    );
    CREATE TABLE IF NOT EXISTS Preferences (
        preference_id INTEGER PRIMARY KEY AUTOINCREMENT,
        traveler_id   INTEGER NOT NULL UNIQUE
                      REFERENCES Travelers(traveler_id) ON DELETE CASCADE,
        budget_min    REAL NOT NULL CHECK (budget_min >= 0),
        budget_max    REAL NOT NULL CHECK (budget_max >= 0),
        pace          TEXT NOT NULL DEFAULT 'balanced'
                      CHECK (pace IN ('relaxed','balanced','packed')),
        currency      TEXT NOT NULL DEFAULT 'AUD',
        CHECK (budget_max >= budget_min)
    );
    CREATE TABLE IF NOT EXISTS Interests (
        interest_id       INTEGER PRIMARY KEY AUTOINCREMENT,
        traveler_id       INTEGER NOT NULL
                          REFERENCES Travelers(traveler_id) ON DELETE CASCADE,
        interest_category TEXT NOT NULL,
        priority          INTEGER NOT NULL DEFAULT 3
                          CHECK (priority BETWEEN 1 AND 5)
    );
    CREATE TABLE IF NOT EXISTS AccessibilityNeeds (
        need_id             INTEGER PRIMARY KEY AUTOINCREMENT,
        traveler_id         INTEGER NOT NULL
                            REFERENCES Travelers(traveler_id) ON DELETE CASCADE,
        requirement         TEXT NOT NULL,
        dietary_restriction TEXT
    );
    """)

    # Seed only once (spec: minimum 10 records per table).
    # Placeholder identities on purpose - no real people, and example.com is
    # the reserved documentation domain, so these addresses can never be mailed.
    if conn.execute("SELECT COUNT(*) c FROM Travelers").fetchone()["c"] == 0:
        conn.executemany(
            "INSERT INTO Travelers (name, email, home_location, travel_style) VALUES (?,?,?,?)",
            [
                ("Traveller One", "traveller.one@example.com", "Sydney, Australia", "mid-range"),
                ("Traveller Two", "traveller.two@example.com", "Sydney, Australia", "luxury"),
                ("Traveller Three", "traveller.three@example.com", "Melbourne, Australia", "budget"),
                ("Traveller Four", "traveller.four@example.com", "Seoul, South Korea", "mid-range"),
                ("Traveller Five", "traveller.five@example.com", "Brisbane, Australia", "luxury"),
                ("Traveller Six", "traveller.six@example.com", "Osaka, Japan", "budget"),
                ("Traveller Seven", "traveller.seven@example.com", "Perth, Australia", "mid-range"),
                ("Traveller Eight", "traveller.eight@example.com", "Rome, Italy", "luxury"),
                ("Traveller Nine", "traveller.nine@example.com", "Auckland, New Zealand", "budget"),
                ("Traveller Ten", "traveller.ten@example.com", "Adelaide, Australia", "mid-range"),
            ],
        )
        conn.executemany(
            "INSERT INTO Preferences (traveler_id, budget_min, budget_max, pace, currency) VALUES (?,?,?,?,?)",
            [
                (1, 2000, 3500, "balanced", "AUD"),
                (2, 4000, 7000, "relaxed", "AUD"),
                (3, 800, 1500, "packed", "AUD"),
                (4, 1800, 3000, "packed", "AUD"),
                (5, 5000, 9000, "relaxed", "AUD"),
                (6, 600, 1200, "balanced", "AUD"),
                (7, 2200, 4000, "balanced", "AUD"),
                (8, 4500, 8000, "relaxed", "AUD"),
                (9, 900, 1600, "packed", "AUD"),
                (10, 2500, 4200, "balanced", "AUD"),
            ],
        )
        conn.executemany(
            "INSERT INTO Interests (traveler_id, interest_category, priority) VALUES (?,?,?)",
            [
                (1, "Food and dining", 5),
                (1, "Museums and galleries", 4),
                (1, "Nature and hiking", 3),
                (2, "Luxury shopping", 5),
                (2, "Fine dining", 4),
                (3, "Backpacking", 5),
                (3, "Live music", 3),
                (4, "History and temples", 4),
                (5, "Spa and wellness", 5),
                (6, "Street food", 5),
                (7, "Beaches and surfing", 4),
                (8, "Architecture", 5),
                (9, "Adventure sports", 4),
                (10, "Local markets", 3),
            ],
        )
        conn.executemany(
            "INSERT INTO AccessibilityNeeds (traveler_id, requirement, dietary_restriction) VALUES (?,?,?)",
            [
                (1, "Step-free access at accommodation", "Vegetarian"),
                (2, "Ground floor room preferred", "Gluten free"),
                (3, "None", "Halal"),
                (4, "Quiet room away from lifts", "No shellfish"),
                (5, "Wheelchair accessible transport", "Dairy free"),
                (6, "None", "Vegan"),
                (7, "Extra legroom seating", "Nut allergy"),
                (8, "Lift access required", "Pescatarian"),
                (9, "None", "No pork"),
                (10, "Assistance at airport transfers", "Vegetarian"),
            ],
        )
    conn.commit()
    conn.close()


# ------------------------------------------------------------------ validation
def validate_traveler(data, partial=False):
    """Return an error string, or None when the payload is acceptable."""
    required = ("name", "email", "home_location", "travel_style")
    if not partial and not all(k in data for k in required):
        return f"required fields: {required}"
    if "name" in data and not str(data["name"]).strip():
        return "name cannot be empty"
    if "email" in data and not EMAIL_RE.match(str(data["email"]).strip()):
        return "email is not a valid address"
    if "home_location" in data and not str(data["home_location"]).strip():
        return "home_location cannot be empty"
    if "travel_style" in data and data["travel_style"] not in TRAVEL_STYLES:
        return f"travel_style must be one of {TRAVEL_STYLES}"
    return None


def validate_preference(data):
    if "traveler_id" not in data:
        return "traveler_id is required"
    for field in ("budget_min", "budget_max"):
        if field not in data:
            return f"{field} is required"
        try:
            value = float(data[field])
        except (TypeError, ValueError):
            return f"{field} must be a number"
        if value < 0:
            return f"{field} cannot be negative"
    if float(data["budget_max"]) < float(data["budget_min"]):
        return "budget_max must be greater than or equal to budget_min"
    if data.get("pace", "balanced") not in PACES:
        return f"pace must be one of {PACES}"
    return None


# ------------------------------------------------------------------- Travelers
@app.route("/travelers")
def list_travelers():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM Travelers ORDER BY traveler_id").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/travelers/<int:traveler_id>")
def get_traveler(traveler_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM Travelers WHERE traveler_id = ?", (traveler_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(dict(row))


@app.route("/travelers", methods=["POST"])
def create_traveler():
    data = request.get_json(silent=True) or {}
    error = validate_traveler(data)
    if error:
        return jsonify({"error": error}), 400
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO Travelers (name, email, home_location, travel_style) VALUES (?,?,?,?)",
            (str(data["name"]).strip(), str(data["email"]).strip(),
             str(data["home_location"]).strip(), data["travel_style"]),
        )
        conn.commit()
        new_id = cur.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "a traveler with that email already exists"}), 409
    conn.close()
    return jsonify({"traveler_id": new_id}), 201


@app.route("/travelers/<int:traveler_id>", methods=["PUT"])
def update_traveler(traveler_id):
    data = request.get_json(silent=True) or {}
    error = validate_traveler(data)
    if error:
        return jsonify({"error": error}), 400
    conn = get_conn()
    try:
        cur = conn.execute(
            """UPDATE Travelers
               SET name = ?, email = ?, home_location = ?, travel_style = ?
               WHERE traveler_id = ?""",
            (str(data["name"]).strip(), str(data["email"]).strip(),
             str(data["home_location"]).strip(), data["travel_style"], traveler_id),
        )
        conn.commit()
        updated = cur.rowcount
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "a traveler with that email already exists"}), 409
    conn.close()
    if not updated:
        return jsonify({"error": "not found"}), 404
    return jsonify({"updated": traveler_id})


@app.route("/travelers/<int:traveler_id>", methods=["DELETE"])
def delete_traveler(traveler_id):
    conn = get_conn()
    cur = conn.execute("DELETE FROM Travelers WHERE traveler_id = ?", (traveler_id,))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    if not deleted:
        return jsonify({"error": "not found"}), 404
    return jsonify({"deleted": traveler_id})


# ----------------------------------------------------------------- Preferences
@app.route("/preferences")
def list_preferences():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM Preferences ORDER BY preference_id").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/preferences/<int:traveler_id>")
def get_preference(traveler_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM Preferences WHERE traveler_id = ?", (traveler_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "no preferences for this traveler"}), 404
    return jsonify(dict(row))


@app.route("/preferences", methods=["POST"])
def upsert_preference():
    """Create the traveler's preference row, or replace it if one exists.

    One preference row per traveler is the rule the schema enforces, so an
    upsert is what the frontend actually needs when a budget range is saved.
    """
    data = request.get_json(silent=True) or {}
    error = validate_preference(data)
    if error:
        return jsonify({"error": error}), 400
    conn = get_conn()
    exists = conn.execute(
        "SELECT 1 FROM Travelers WHERE traveler_id = ?", (data["traveler_id"],)
    ).fetchone()
    if exists is None:
        conn.close()
        return jsonify({"error": "traveler not found"}), 404
    conn.execute(
        """INSERT INTO Preferences (traveler_id, budget_min, budget_max, pace, currency)
           VALUES (?,?,?,?,?)
           ON CONFLICT(traveler_id) DO UPDATE SET
               budget_min = excluded.budget_min,
               budget_max = excluded.budget_max,
               pace       = excluded.pace,
               currency   = excluded.currency""",
        (data["traveler_id"], float(data["budget_min"]), float(data["budget_max"]),
         data.get("pace", "balanced"), data.get("currency", "AUD")),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM Preferences WHERE traveler_id = ?", (data["traveler_id"],)
    ).fetchone()
    conn.close()
    return jsonify(dict(row)), 201


@app.route("/preferences/<int:traveler_id>", methods=["PUT"])
def update_preference(traveler_id):
    data = dict(request.get_json(silent=True) or {})
    data["traveler_id"] = traveler_id
    error = validate_preference(data)
    if error:
        return jsonify({"error": error}), 400
    conn = get_conn()
    cur = conn.execute(
        """UPDATE Preferences
           SET budget_min = ?, budget_max = ?, pace = ?, currency = ?
           WHERE traveler_id = ?""",
        (float(data["budget_min"]), float(data["budget_max"]),
         data.get("pace", "balanced"), data.get("currency", "AUD"), traveler_id),
    )
    conn.commit()
    updated = cur.rowcount
    conn.close()
    if not updated:
        return jsonify({"error": "not found"}), 404
    return jsonify({"updated": traveler_id})


@app.route("/preferences/<int:traveler_id>", methods=["DELETE"])
def delete_preference(traveler_id):
    conn = get_conn()
    cur = conn.execute("DELETE FROM Preferences WHERE traveler_id = ?", (traveler_id,))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    if not deleted:
        return jsonify({"error": "not found"}), 404
    return jsonify({"deleted": traveler_id})


# ------------------------------------------------------------------- Interests
@app.route("/interests")
def list_interests():
    traveler_id = request.args.get("traveler_id", type=int)
    conn = get_conn()
    if traveler_id:
        rows = conn.execute(
            "SELECT * FROM Interests WHERE traveler_id = ? ORDER BY priority DESC, interest_id",
            (traveler_id,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM Interests ORDER BY interest_id").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/interests/<int:interest_id>")
def get_interest(interest_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM Interests WHERE interest_id = ?", (interest_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(dict(row))


@app.route("/interests", methods=["POST"])
def create_interest():
    data = request.get_json(silent=True) or {}
    if "traveler_id" not in data or not str(data.get("interest_category", "")).strip():
        return jsonify({"error": "traveler_id and interest_category are required"}), 400
    priority = data.get("priority", 3)
    if priority not in (1, 2, 3, 4, 5):
        return jsonify({"error": "priority must be an integer from 1 to 5"}), 400
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO Interests (traveler_id, interest_category, priority) VALUES (?,?,?)",
            (data["traveler_id"], str(data["interest_category"]).strip(), priority),
        )
        conn.commit()
        new_id = cur.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "traveler not found"}), 404
    conn.close()
    return jsonify({"interest_id": new_id}), 201


@app.route("/interests/<int:interest_id>", methods=["PUT"])
def update_interest(interest_id):
    data = request.get_json(silent=True) or {}
    if not str(data.get("interest_category", "")).strip():
        return jsonify({"error": "interest_category is required"}), 400
    priority = data.get("priority", 3)
    if priority not in (1, 2, 3, 4, 5):
        return jsonify({"error": "priority must be an integer from 1 to 5"}), 400
    conn = get_conn()
    cur = conn.execute(
        "UPDATE Interests SET interest_category = ?, priority = ? WHERE interest_id = ?",
        (str(data["interest_category"]).strip(), priority, interest_id),
    )
    conn.commit()
    updated = cur.rowcount
    conn.close()
    if not updated:
        return jsonify({"error": "not found"}), 404
    return jsonify({"updated": interest_id})


@app.route("/interests/<int:interest_id>", methods=["DELETE"])
def delete_interest(interest_id):
    conn = get_conn()
    cur = conn.execute("DELETE FROM Interests WHERE interest_id = ?", (interest_id,))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    if not deleted:
        return jsonify({"error": "not found"}), 404
    return jsonify({"deleted": interest_id})


# ---------------------------------------------------------- AccessibilityNeeds
@app.route("/accessibility-needs")
def list_needs():
    traveler_id = request.args.get("traveler_id", type=int)
    conn = get_conn()
    if traveler_id:
        rows = conn.execute(
            "SELECT * FROM AccessibilityNeeds WHERE traveler_id = ? ORDER BY need_id",
            (traveler_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM AccessibilityNeeds ORDER BY need_id"
        ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/accessibility-needs/<int:need_id>")
def get_need(need_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM AccessibilityNeeds WHERE need_id = ?", (need_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(dict(row))


@app.route("/accessibility-needs", methods=["POST"])
def create_need():
    data = request.get_json(silent=True) or {}
    if "traveler_id" not in data or not str(data.get("requirement", "")).strip():
        return jsonify({"error": "traveler_id and requirement are required"}), 400
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO AccessibilityNeeds (traveler_id, requirement, dietary_restriction) VALUES (?,?,?)",
            (data["traveler_id"], str(data["requirement"]).strip(),
             (data.get("dietary_restriction") or "").strip() or None),
        )
        conn.commit()
        new_id = cur.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "traveler not found"}), 404
    conn.close()
    return jsonify({"need_id": new_id}), 201


@app.route("/accessibility-needs/<int:need_id>", methods=["PUT"])
def update_need(need_id):
    data = request.get_json(silent=True) or {}
    if not str(data.get("requirement", "")).strip():
        return jsonify({"error": "requirement is required"}), 400
    conn = get_conn()
    cur = conn.execute(
        """UPDATE AccessibilityNeeds
           SET requirement = ?, dietary_restriction = ?
           WHERE need_id = ?""",
        (str(data["requirement"]).strip(),
         (data.get("dietary_restriction") or "").strip() or None, need_id),
    )
    conn.commit()
    updated = cur.rowcount
    conn.close()
    if not updated:
        return jsonify({"error": "not found"}), 404
    return jsonify({"updated": need_id})


@app.route("/accessibility-needs/<int:need_id>", methods=["DELETE"])
def delete_need(need_id):
    conn = get_conn()
    cur = conn.execute("DELETE FROM AccessibilityNeeds WHERE need_id = ?", (need_id,))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    if not deleted:
        return jsonify({"error": "not found"}), 404
    return jsonify({"deleted": need_id})


# ------------------------------------------------------- cross-feature contract
@app.route("/preference-set/<int:traveler_id>")
def preference_set(traveler_id):
    """The structured preference set other features read (Trip Planning,
    Budget, Booking). One call, one JSON document, no direct file access.
    """
    conn = get_conn()
    traveler = conn.execute(
        "SELECT * FROM Travelers WHERE traveler_id = ?", (traveler_id,)
    ).fetchone()
    if traveler is None:
        conn.close()
        return jsonify({"error": "not found"}), 404
    preference = conn.execute(
        "SELECT * FROM Preferences WHERE traveler_id = ?", (traveler_id,)
    ).fetchone()
    interests = conn.execute(
        "SELECT * FROM Interests WHERE traveler_id = ? ORDER BY priority DESC, interest_id",
        (traveler_id,),
    ).fetchall()
    needs = conn.execute(
        "SELECT * FROM AccessibilityNeeds WHERE traveler_id = ? ORDER BY need_id",
        (traveler_id,),
    ).fetchall()
    conn.close()
    return jsonify({
        "traveler": dict(traveler),
        "preferences": dict(preference) if preference else None,
        "interests": [dict(r) for r in interests],
        "accessibility_needs": [dict(r) for r in needs],
    })


@app.route("/health")
def health():
    return jsonify({"service": "student-1-database", "status": "ok"})


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=PORT, debug=True)
