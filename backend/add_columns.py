"""
Migration: add email and phone columns to technicians table.
Run this script with the backend venv active:
  cd backend
  venv\Scripts\activate
  python add_columns.py
"""
import sqlite3, os, sys

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dispatchgrid.db")
if not os.path.exists(db_path):
    print(f"ERROR: Database not found at {db_path}")
    sys.exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("PRAGMA table_info(technicians)")
cols = [row[1] for row in cur.fetchall()]
print("Existing columns:", cols)

changed = False
if "email" not in cols:
    cur.execute("ALTER TABLE technicians ADD COLUMN email TEXT")
    print("Added email column")
    changed = True
else:
    print("email column already exists")

if "phone" not in cols:
    cur.execute("ALTER TABLE technicians ADD COLUMN phone TEXT")
    print("Added phone column")
    changed = True
else:
    print("phone column already exists")

conn.commit()
conn.close()
print("Migration complete!" if changed else "Nothing to do.")
