import sys
import os
from backend.database import DatabaseManager
from backend.bot_manager import BotManager
from backend.bot_logic import BinanceBot

def diagnose():
    db = DatabaseManager()
    users = db.get_all_users()
    if not users:
        print("No users found in database.")
        return

    user = users[0] # Assuming first user for diagnosis
    user_id = user['id']
    username = user['username']
    print(f"Diagnosing for user: {username} (ID: {user_id})")

    # Get settings
    sniper_mode = db.get_setting("sniper_mode", "False", user_id=user_id) == "True"
    trade_qty = float(db.get_setting("trade_qty", 20.0, user_id=user_id))
    trade_qty_type = db.get_setting("trade_qty_type", "quote", user_id=user_id)
    symbol = db.get_setting("symbol", "BTCUSDT", user_id=user_id)
    
    print(f"Settings: Symbol={symbol}, Qty={trade_qty} ({trade_qty_type}), Sniper={sniper_mode}")

    # Initialize bot to check balance and connection
    bot = BinanceBot(user_id=user_id)
    creds = db.get_state("credentials", is_json=True, user_id=user_id)
    if not creds:
        print("No credentials found.")
        return

    bot._init_client(creds.get("api_key"), creds.get("api_secret"), creds.get("is_testnet", True))
    
    # Wait for initialization
    import time
    time.sleep(2)
    
    bot._update_account_balances()
    print(f"Balances: USDT={bot.balance:.2f}, BTC={bot.crypto_balance:.6f}")
    
    # Check current price
    ticker = bot.client.client.get_symbol_ticker(symbol=symbol)
    price = float(ticker['price'])
    print(f"Current Price: {price}")

    # Simulate validate_order like in _place_buy_order
    is_quote = (trade_qty_type == "quote")
    test_qty = 62.0 # User's attempt
    
    if sniper_mode:
        test_qty = bot.balance * 0.98 if is_quote else (bot.balance * 0.98 / price)
        print(f"Sniper Mode Adjustment: New test_qty = {test_qty}")

    is_valid, reason = bot.client.validate_order(symbol, test_qty, price, is_quote_qty=is_quote)
    print(f"Validation Result for {test_qty} {'USDT' if is_quote else 'units'}: {is_valid}, Reason: {reason}")

    # Adjust to min notional simulation
    if not is_valid:
        adj = bot.client.adjust_to_min_notional(symbol, test_qty, price)
        print(f"Adjustment logic: {adj}")

if __name__ == "__main__":
    diagnose()
