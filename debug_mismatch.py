from backend.database import DatabaseManager
import os

db = DatabaseManager()
users = db.get_all_users()

print(f"{'ID':<3} | {'Username':<15} | {'Symbol':<10} | {'Running':<8} | {'Session':<10}")
print("-" * 60)

for u in users:
    uid = u['id']
    username = u['username']
    symbol = db.get_setting("current_symbol", "N/A", user_id=uid)
    is_running = db.get_setting("bot_is_running", "N/A", user_id=uid)
    # Also check 'is_running' in state
    state_running = db.get_state("is_running", "N/A", user_id=uid)
    session = u.get('session_token')
    session_str = "YES" if session else "NO"

    print(f"{uid:<3} | {username:<15} | {symbol:<10} | {is_running}/{state_running} | {session_str}")
