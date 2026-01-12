
import requests
import time

try:
    r1 = requests.get('http://127.0.0.1:8000/api/status').json()
    time.sleep(5)
    r2 = requests.get('http://127.0.0.1:8000/api/status').json()
    print(f"RSI 1: {r1.get('rsi')}")
    print(f"RSI 2: {r2.get('rsi')}")
    print(f"Price 1: {r1.get('price')}")
    print(f"Price 2: {r2.get('price')}")
    print(f"Is Running: {r1.get('is_running')}")
except Exception as e:
    print(f"Error connecting to bot: {e}")
