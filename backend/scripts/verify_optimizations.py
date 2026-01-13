from backend.binance_wrapper import BinanceWrapper
import sys
import os
import time
import asyncio

# Setup path
sys.path.append(os.getcwd())


def test_filters():
    print("--- Testing Filter Logic & Caching ---")
    wrapper = BinanceWrapper(testnet=True)
    symbol = "BTCUSDT"

    # Test Caching
    s1 = time.time()
    info1 = wrapper.get_symbol_info(symbol)
    e1 = time.time()
    print(f"First (API): {e1-s1:.4f}s")

    s2 = time.time()
    info2 = wrapper.get_symbol_info(symbol)
    e2 = time.time()
    print(f"Second (Cache): {e2-s2:.4f}s")

    if info1 and (e2-s2 < e1-s1 or e2-s2 < 0.05):
        print("✅ Symbol info caching working.")

    # Test Adjustment
    price = float(wrapper.client.get_symbol_ticker(symbol=symbol)['price'])
    sm = 0.000001
    adj = wrapper.adjust_to_min_notional(symbol, sm, price)
    print(f"Adjusted {sm} -> {adj} (Expected ~0.0001+)")
    if adj and adj > sm:
        v, r = wrapper.validate_order(symbol, adj, price)
        if v:
            print("✅ Filter adjustment successful and valid.")
        else:
            print(f"❌ Still invalid: {r}")


if __name__ == "__main__":
    test_filters()
