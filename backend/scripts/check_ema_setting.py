from backend.database import DatabaseManager

db = DatabaseManager()
ema_length = db.get_setting("ema_length", "not_set")
print(f"Current EMA Length in DB: {ema_length}")
