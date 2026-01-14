from backend.database import DatabaseManager
import os

db_path = "backend/bot_data.db"
if os.path.exists(db_path):
    db = DatabaseManager(db_path)
    # Check if bot is running
    is_running = db.get_setting("bot_is_running", "False", user_id=8)
    active_strategy = db.get_setting(
        "active_strategy", "rsi_rebound", user_id=8)
    symbol = db.get_setting("current_symbol", "BTCUSDT", user_id=8)

    print(f"Bot Is Running: {is_running}")
    print(f"Active Strategy: {active_strategy}")
    print(f"Current Symbol: {symbol}")
else:
    print("Database not found")
