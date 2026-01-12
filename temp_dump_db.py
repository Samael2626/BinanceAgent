import sqlite3
import json


def dump_db():
    conn = sqlite3.connect('backend/bot_data.db')
    cursor = conn.cursor()

    print("--- SETTINGS ---")
    cursor.execute("SELECT key, value FROM settings")
    for row in cursor.fetchall():
        print(f"{row[0]}: {row[1]}")

    print("\n--- STATE ---")
    cursor.execute("SELECT key, value FROM state")
    for row in cursor.fetchall():
        print(f"{row[0]}: {row[1]}")

    conn.close()


if __name__ == "__main__":
    dump_db()
