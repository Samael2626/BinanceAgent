from binance.client import Client
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")
api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")

client = Client(api_key, api_secret, testnet=True)
client.https_proxy = None

intervals = ["1m", "5m", "15m", "1h"]

print(f"Checking BTCUSDT candles on Testnet...")

for interval in intervals:
    try:
        klines = client.get_klines(
            symbol="BTCUSDT", interval=interval, limit=500)
        print(f"Interval {interval}: {len(klines)} candles returned.")
    except Exception as e:
        print(f"Interval {interval}: Error {e}")
