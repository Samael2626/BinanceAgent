
import sqlite3
import os

# Get path to database relative to this script
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'bot_data.db')

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
for table in ['state', 'settings', 'trades']:
    cur.execute(f"SELECT sql FROM sqlite_master WHERE name='{table}'")
    print(f"Table {table}: {cur.fetchone()}")
