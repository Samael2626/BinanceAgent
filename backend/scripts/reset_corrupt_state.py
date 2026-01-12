import sqlite3

import os

# Get path to database relative to this script
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'bot_data.db')


def clear_corrupt_state():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        user_id = 1
        keys_to_reset = [
            "entry_price",
            "position_orders",
            "accumulated_qty",
            "highest_price"
        ]

        print(f"Resetting state for User {user_id}...")
        for key in keys_to_reset:
            cursor.execute(
                "UPDATE state SET value = 0 WHERE user_id = ? AND key = ?",
                (user_id, key)
            )
            print(f"  - Set {key} to 0")

        conn.commit()
        print("Done. Please restart the backend.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    clear_corrupt_state()
