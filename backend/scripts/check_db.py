
import sqlite3
import json

import os

# Get path to database relative to this script
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'bot_data.db')

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute('SELECT val FROM state WHERE key="credentials"')
row = cur.fetchone()
if row:
    print(f"Credentials exist: {row[0][:20]}...")
else:
    print("No credentials found in state.")

cur.execute('SELECT val FROM state WHERE key="entry_price"')
row = cur.fetchone()
print(f"Entry Price: {row[0] if row else 'None'}")

cur.execute('SELECT val FROM state WHERE key="initial_balance"')
row = cur.fetchone()
print(f"Initial Balance: {row[0] if row else 'None'}")
