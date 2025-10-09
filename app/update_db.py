import sqlite3
import os
DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'guests.db')
try:
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE guests ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
    print("Column 'status' added successfully.")
    conn.commit()
except Exception as e:
    print(f"An error occurred (column might already exist): {e}")
finally:
    if conn:
        conn.close()