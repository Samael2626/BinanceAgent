from backend.database import DatabaseManager

db = DatabaseManager()
user_id = 1
print(f"IS_RUNNING: {db.get_state('is_running', user_id=user_id)}")
print(f"ENABLE_BUYING: {db.get_state('enable_buying', user_id=user_id)}")
print(f"ACTIVE_STRATEGY: {db.get_setting('active_strategy', user_id=user_id)}")
print(f"SYMBOL: {db.get_setting('symbol', user_id=user_id)}")
# Check specific symbol or loop?
print(
    f"ACCUMULATED_QTY: {db.get_state('accumulated_qty_BNBUSDT', user_id=user_id)}")
# Actually, I need to know the symbol first.
symbol = db.get_setting('symbol', "BTCUSDT", user_id=user_id)
print(f"TARGET_SYMBOL: {symbol}")
scope_qty = f"accumulated_qty_{symbol}"
print(f"POS_QTY: {db.get_state(scope_qty, user_id=user_id)}")

print(f"RSI_BUY_THRESHOLD: {db.get_setting('buy_rsi', user_id=user_id)}")
print(
    f"MUTUAL_EXCLUSION: {db.get_setting('enable_mutual_exclusion', user_id=user_id)}")
