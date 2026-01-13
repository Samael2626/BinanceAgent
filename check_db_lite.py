import sqlite3
import json


def check_db():
    conn = sqlite3.connect('backend/bot_data.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("--- USERS ---")
    cursor.execute("SELECT id, username, session_token FROM users")
    users = cursor.fetchall()
    for u in users:
        print(dict(u))

    if not users:
        return

    user_id = users[0]['id']

    print("\n--- SETTINGS ---")
    cursor.execute(
        "SELECT key, value FROM settings WHERE user_id = ?", (user_id,))
    settings = cursor.fetchall()
    for s in settings:
        print(f"{s['key']}: {s['value']}")

    print("\n--- STATE ---")
    cursor.execute(
        "SELECT key, value FROM state WHERE user_id = ?", (user_id,))
    state = cursor.fetchall()
    for s in state:
        key = s['key']
        val = s['value']
        if key == "credentials":
            creds = json.loads(val)
            print(
                f"credentials: API_KEY={creds.get('api_key')[:5]}... (Testnet={creds.get('is_testnet')})")
        else:
            print(f"{key}: {val}")

    conn.close()


if __name__ == "__main__":
    check_db()
