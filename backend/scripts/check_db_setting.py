from backend.database import DatabaseManager

db = DatabaseManager()
timeframe = db.get_setting("timeframe", "not_set")
print(f"Current Timeframe in DB: {timeframe}")
