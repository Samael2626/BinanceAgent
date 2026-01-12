import sqlite3
import json

import os

# Get path to database relative to this script
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'bot_data.db')


def inspect_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        print(f"--- DATABASE INSPECTION: {DB_PATH} ---")

        # 1. Check User (assume ID 1)
        print("\n[USERS]")
        cursor.execute("SELECT id, username, is_testnet FROM users")
        for row in cursor.fetchall():
            print(row)

        user_id = 1

        # 2. Check Settings
        print(f"\n[SETTINGS (User {user_id})]")
        cursor.execute(
            "SELECT key, value FROM settings WHERE user_id=?", (user_id,))
        settings = {row[0]: row[1] for row in cursor.fetchall()}
        interesting_keys = [
            "buy_rsi", "sell_rsi", "active_strategy", "max_dca_orders",
            "dca_step_pct", "min_balance", "trade_qty", "enable_buying",
            "enable_selling", "symbol"
        ]
        for k in interesting_keys:
            print(f"  {k}: {settings.get(k, 'N/A')}")

        # 3. Check State
        print(f"\n[STATE (User {user_id})]")
        cursor.execute(
            "SELECT key, value FROM state WHERE user_id=?", (user_id,))
        state = {row[0]: row[1] for row in cursor.fetchall()}
        interesting_state = [
            "position_orders", "accumulated_qty", "entry_price", "highest_price"
        ]
        for k in interesting_state:
            print(f"  {k}: {state.get(k, 'N/A')}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    inspect_db()
