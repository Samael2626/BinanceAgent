from binance.client import Client
from backend.config import API_KEY, API_SECRET

try:
    client = Client(API_KEY, API_SECRET)
    info = client.get_symbol_info('BTCUSDT')
    print("STATUS: SUCCESS")
    for f in info['filters']:
        if f['filterType'] == 'LOT_SIZE':
            print(f"Min Qty: {f['minQty']}")
            print(f"Step Size: {f['stepSize']}")
        if f['filterType'] == 'NOTIONAL':
            print(f"Min Notional: {f['minNotional']}")
        if f['filterType'] == 'MIN_NOTIONAL':  # Newer API version might use this
            print(f"Min Notional: {f['minNotional']}")

except Exception as e:
    print(f"STATUS: ERROR: {e}")
