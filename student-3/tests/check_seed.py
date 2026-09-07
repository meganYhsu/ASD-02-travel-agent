import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "database" / "budget.db"

conn = sqlite3.connect(DB_PATH)
tables = ["Budgets", "Expenses", "ExpenseCategories", "AdjustmentRecommendations"]

for table in tables:
    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(table, count, "records")
    if count < 10:
        print("FAIL:", table, "needs at least 10 records")
        raise SystemExit(1)

print("All tables have at least 10 records")
