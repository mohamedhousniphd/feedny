import os
import sqlite3
from app.database import init_db, get_db

print("Running init_db()...")
init_db()
print("init_db() completed.")

print("Checking schema...")
with get_db() as conn:
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"Tables: {tables}")

    assert 'feedbacks' in tables
    assert 'device_limits' in tables
    assert 'settings' in tables
    assert 'teachers' in tables
    assert 'payment_receipts' in tables
    assert 'analysis_history' in tables

print("All tests passed.")
