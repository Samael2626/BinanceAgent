
import sqlite3
import json

import os

# Get path to database relative to this script
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'bot_data.db')

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute('SELECT value FROM state WHERE key="credentials"')
row = cur.fetchone()
if row:
    print(f"Credentials exist (length: {len(row[0])})")
else:
    print("No credentials found in state.")

cur.execute('SELECT value FROM settings WHERE key="active_strategy"')
row = cur.fetchone()
print(f"Active Strategy: {row[0] if row else 'None'}")

cur.execute('SELECT value FROM settings WHERE key="trade_qty"')
row = cur.fetchone()
print(f"Trade Qty: {row[0] if row else 'None'}")
