from backend.database import DatabaseManager

db = DatabaseManager()
db.save_setting("timeframe", "1m")
print(f"Updated Timeframe in DB to: 1m")
