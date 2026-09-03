from flask import Flask, jsonify, request
from pathlib import Path
import sqlite3

DB_PATH = Path(__file__).with_name("budget.db")

app = Flask(__name__)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS ExpenseCategories (
        category_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        name          TEXT NOT NULL UNIQUE,
        description   TEXT,
        default_allocation_pct REAL NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS Budgets (
        budget_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        trip_id       INTEGER NOT NULL,
        total_budget  REAL NOT NULL CHECK (total_budget > 0),
        currency      TEXT NOT NULL DEFAULT 'AUD',
        created_date  TEXT NOT NULL DEFAULT (date('now'))
    );
    CREATE TABLE IF NOT EXISTS Expenses (
        expense_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        trip_id       INTEGER NOT NULL,
        category_id   INTEGER NOT NULL REFERENCES ExpenseCategories(category_id),
        description   TEXT NOT NULL,
        amount        REAL NOT NULL CHECK (amount >= 0),
        expense_date  TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS AdjustmentRecommendations (
        rec_id             INTEGER PRIMARY KEY AUTOINCREMENT,
        trip_id            INTEGER NOT NULL,
        recommendation     TEXT NOT NULL,
        target_activity_id INTEGER,
        status             TEXT NOT NULL DEFAULT 'proposed'
                           CHECK (status IN ('proposed','accepted','dismissed')),
        created_date       TEXT NOT NULL DEFAULT (date('now'))
    );
    """)

    if conn.execute("SELECT COUNT(*) c FROM ExpenseCategories").fetchone()["c"] == 0:
        conn.executemany(
            "INSERT INTO ExpenseCategories (name, description, default_allocation_pct) VALUES (?,?,?)",
            [
                ("Accommodation", "Hotels and stays", 35),
                ("Food", "Meals and snacks", 25),
                ("Transport", "Flights, trains, taxis", 15),
                ("Activities", "Tours and attractions", 15),
                ("Shopping", "Souvenirs and goods", 5),
                ("Insurance", "Travel insurance", 2),
                ("Connectivity", "SIM and wifi", 1),
                ("Emergency", "Unplanned costs", 1),
                ("Nightlife", "Bars and shows", 0.5),
                ("Misc", "Anything else", 0.5),
            ],
        )
        conn.executemany(
            "INSERT INTO Budgets (trip_id, total_budget, currency, created_date) VALUES (?,?,?,?)",
            [(1, 3000, "AUD", "2026-08-20"), (2, 1500, "AUD", "2026-07-01"),
             (3, 5200, "AUD", "2026-06-15"), (4, 800, "AUD", "2026-06-01"),
             (5, 2400, "AUD", "2026-05-20"), (6, 3100, "AUD", "2026-05-01"),
             (7, 950, "AUD", "2026-04-11"), (8, 4300, "AUD", "2026-03-30"),
             (9, 1200, "AUD", "2026-03-02"), (10, 2750, "AUD", "2026-02-14")],
        )
        conn.executemany(
            "INSERT INTO Expenses (trip_id, category_id, description, amount, expense_date) VALUES (?,?,?,?,?)",
            [
                (1, 1, "Shinjuku hotel deposit", 620, "2026-09-01"),
                (1, 3, "Narita Express tickets", 95, "2026-09-01"),
                (1, 2, "Ramen dinner, Shibuya", 48, "2026-09-01"),
                (1, 4, "teamLab tickets", 110, "2026-09-02"),
                (1, 2, "Sushi lunch, Tsukiji", 130, "2026-09-02"),
                (1, 5, "Souvenirs, Asakusa", 85, "2026-09-02"),
                (1, 2, "Izakaya dinner", 165, "2026-09-02"),
                (1, 3, "Metro day passes", 42, "2026-09-03"),
                (1, 4, "Ghibli Museum", 90, "2026-09-03"),
                (1, 2, "Wagyu dinner (unplanned)", 465, "2026-09-03"),
            ],
        )
        conn.executemany(
            "INSERT INTO AdjustmentRecommendations (trip_id, recommendation, target_activity_id, status, created_date) VALUES (?,?,?,?,?)",
            [
                (2, "Swap paid garden tour for free walking route", 21, "accepted", "2026-07-03"),
                (2, "Reduce dining budget by 15 AUD per day", None, "dismissed", "2026-07-03"),
                (3, "Replace day-5 helicopter tour with lookout hike", 34, "accepted", "2026-06-20"),
                (3, "Move one hotel night to a hostel", None, "dismissed", "2026-06-21"),
                (4, "Cook two dinners at the apartment", None, "accepted", "2026-06-04"),
                (5, "Use rail pass instead of taxis", None, "accepted", "2026-05-23"),
                (6, "Cancel optional wine tasting", 58, "dismissed", "2026-05-05"),
                (7, "Switch to free museum day", 61, "accepted", "2026-04-14"),
                (8, "Downgrade rental car class", None, "accepted", "2026-04-02"),
                (9, "Replace paid onsen with public bath", 77, "proposed", "2026-03-05"),
            ],
        )
    conn.commit()
    conn.close()


@app.route("/expenses")
def list_expenses():
    trip_id = request.args.get("trip_id", type=int)
    conn = get_conn()
    if trip_id:
        rows = conn.execute(
            """SELECT e.*, c.name AS category_name
               FROM Expenses e JOIN ExpenseCategories c USING (category_id)
               WHERE e.trip_id = ? ORDER BY e.expense_date""",
            (trip_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT e.*, c.name AS category_name
               FROM Expenses e JOIN ExpenseCategories c USING (category_id)
               ORDER BY e.expense_date"""
        ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/expenses", methods=["POST"])
def create_expense():
    data = request.get_json(silent=True) or {}
    required = ("trip_id", "category_id", "description", "amount", "expense_date")
    if not all(k in data for k in required):
        return jsonify({"error": f"required fields: {required}"}), 400
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO Expenses (trip_id, category_id, description, amount, expense_date) VALUES (?,?,?,?,?)",
        (data["trip_id"], data["category_id"], data["description"],
         data["amount"], data["expense_date"]),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return jsonify({"expense_id": new_id}), 201


@app.route("/expenses/<int:expense_id>", methods=["PUT"])
def update_expense(expense_id):
    data = request.get_json(silent=True) or {}
    required = ("description", "amount", "category_id", "expense_date")
    if not all(k in data for k in required):
        return jsonify({"error": f"required fields: {required}"}), 400
    conn = get_conn()
    cur = conn.execute(
        """UPDATE Expenses
           SET description = ?, amount = ?, category_id = ?, expense_date = ?
           WHERE expense_id = ?""",
        (data["description"], data["amount"], data["category_id"],
         data["expense_date"], expense_id),
    )
    conn.commit()
    updated = cur.rowcount
    conn.close()
    if not updated:
        return jsonify({"error": "not found"}), 404
    return jsonify({"updated": expense_id})


@app.route("/expenses/<int:expense_id>", methods=["DELETE"])
def delete_expense(expense_id):
    conn = get_conn()
    cur = conn.execute("DELETE FROM Expenses WHERE expense_id = ?", (expense_id,))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    if not deleted:
        return jsonify({"error": "not found"}), 404
    return jsonify({"deleted": expense_id})


@app.route("/budgets/<int:trip_id>")
def get_budget(trip_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM Budgets WHERE trip_id = ? ORDER BY budget_id DESC LIMIT 1",
        (trip_id,),
    ).fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "no budget for this trip"}), 404
    return jsonify(dict(row))


@app.route("/budgets", methods=["POST"])
def create_budget():
    data = request.get_json(silent=True) or {}
    if "trip_id" not in data or "total_budget" not in data:
        return jsonify({"error": "trip_id and total_budget are required"}), 400
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO Budgets (trip_id, total_budget, currency) VALUES (?,?,?)",
        (data["trip_id"], data["total_budget"], data.get("currency", "AUD")),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return jsonify({"budget_id": new_id}), 201


@app.route("/categories")
def list_categories():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM ExpenseCategories ORDER BY category_id").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/recommendations")
def list_recommendations():
    trip_id = request.args.get("trip_id", type=int)
    conn = get_conn()
    if trip_id:
        rows = conn.execute(
            "SELECT * FROM AdjustmentRecommendations WHERE trip_id = ? ORDER BY rec_id DESC",
            (trip_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM AdjustmentRecommendations ORDER BY rec_id DESC"
        ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/recommendations", methods=["POST"])
def create_recommendation():
    data = request.get_json(silent=True) or {}
    if "trip_id" not in data or "recommendation" not in data:
        return jsonify({"error": "trip_id and recommendation are required"}), 400
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO AdjustmentRecommendations (trip_id, recommendation, target_activity_id) VALUES (?,?,?)",
        (data["trip_id"], data["recommendation"], data.get("target_activity_id")),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return jsonify({"rec_id": new_id}), 201


@app.route("/recommendations/<int:rec_id>", methods=["PATCH"])
def update_recommendation_status(rec_id):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in ("accepted", "dismissed"):
        return jsonify({"error": "status must be 'accepted' or 'dismissed'"}), 400
    conn = get_conn()
    cur = conn.execute(
        "UPDATE AdjustmentRecommendations SET status = ? WHERE rec_id = ?",
        (status, rec_id),
    )
    conn.commit()
    updated = cur.rowcount
    conn.close()
    if not updated:
        return jsonify({"error": "not found"}), 404
    return jsonify({"rec_id": rec_id, "status": status})


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=6003, debug=True)