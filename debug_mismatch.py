from backend.database import DatabaseManager
from backend.binance_wrapper import BinanceWrapper
# Removed TESTNET import as it evidently doesn't exist in config.py or is named differently
from backend.config import API_KEY, API_SECRET

db = DatabaseManager()
user_id = 1

# 1. Check Internal DB State for both
print("--- INTERNAL DB STATE ---")
print(f"SYMBOL setting: {db.get_setting('symbol', user_id=user_id)}")
print(
    f"BTC Position Qty: {db.get_state('accumulated_qty_BTCUSDT', user_id=user_id)}")
print(
    f"BNB Position Qty: {db.get_state('accumulated_qty_BNBUSDT', user_id=user_id)}")

# 2. Check Recent Trades in DB
print("\n--- RECENT TRADES IN DB ---")
trades = db.get_trades(user_id=user_id)
for t in trades[:5]:
    try:
        print(
            f"{t.get('time')} - {t.get('symbol')} - {t.get('type')} - Qty: {t.get('qty')}")
    except:
        print(f"Raw trade: {t}")

# 3. Check REAL Account Balances (if possible without exposing credentials)
try:
    creds = db.get_state("credentials", is_json=True, user_id=user_id)
    if creds:
        # Pass testnet arg correctly based on stored creds
        client = BinanceWrapper(
            creds['api_key'], creds['api_secret'], testnet=creds.get('is_testnet', True))
        print("\n--- REAL WALLET BALANCES ---")
        btc = client.get_account_balance("BTC")
        bnb = client.get_account_balance("BNB")
        usdt = client.get_account_balance("USDT")
        print(f"BTC: {btc}")
        print(f"BNB: {bnb}")
        print(f"USDT: {usdt}")
    else:
        print("\nCould not load credentials for real balance check.")
except Exception as e:
    print(f"\nError checking real balances: {e}")
