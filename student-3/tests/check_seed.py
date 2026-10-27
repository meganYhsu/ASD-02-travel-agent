import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "database" / "budget.db"

# Fixed queries, one per table - no SQL is built from strings (Ruff S608).
COUNT_QUERIES = {
    "Budgets": "SELECT COUNT(*) FROM Budgets",
    "Expenses": "SELECT COUNT(*) FROM Expenses",
    "ExpenseCategories": "SELECT COUNT(*) FROM ExpenseCategories",
    "AdjustmentRecommendations": "SELECT COUNT(*) FROM AdjustmentRecommendations",
}

conn = sqlite3.connect(DB_PATH)

for table, query in COUNT_QUERIES.items():
    count = conn.execute(query).fetchone()[0]
    print(table, count, "records")
    if count < 10:
        print("FAIL:", table, "needs at least 10 records")
        raise SystemExit(1)

print("All tables have at least 10 records")
