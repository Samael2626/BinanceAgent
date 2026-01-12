from backend.bot_logic import BinanceBot
import sys
import os
import time
import pandas as pd
import pandas_ta as ta
import unittest.mock as mock

# Add project root to path
sys.path.append(os.getcwd())


def verify():
    print("Initializing bot...")
    try:
        bot = BinanceBot()
        print("Bot instance created.")
    except Exception as e:
        print(f"Failed to init bot: {e}")
        return

    print("Testing _update_market_data logic with mock data...")

    # Mock dataframe with enough data for indicators
    periods = 300
    dates = pd.date_range(start='2024-01-01', periods=periods, freq='1min')
    # Create some movement to generate valid RSI/SMA
    import numpy as np
    close_prices = np.linspace(100, 200, periods) + \
        np.random.normal(0, 5, periods)

    df = pd.DataFrame({
        'open': close_prices,
        'high': close_prices + 2,
        'low': close_prices - 2,
        'close': close_prices,
        'volume': [1000.0] * periods,
    }, index=dates)

    # Mock bot.data_client.get_historical_klines
    # We assign it to the instance
    bot.data_client = mock.Mock()
    bot.data_client.get_historical_klines.return_value = df

    # Run update
    print("Running _update_market_data...")
    try:
        start_time = time.time()
        success = bot._update_market_data()
        duration = time.time() - start_time
        print(f"Update took {duration:.4f}s")

        if success:
            print("Update function returned True.")
            if not bot.history:
                print("❌ History is empty!")
                return

            last_candle = bot.history[-1]
            print(f"Last candle keys: {list(last_candle.keys())}")

            required = ['sma_50', 'sma_200', 'rsi', 'volume']
            missing = [k for k in required if k not in last_candle]

            if missing:
                print(f"❌ Missing keys in history: {missing}")
            else:
                print("✅ All required keys present in history.")
                print(
                    f"Sample values (Last Candle): RSI={last_candle.get('rsi')}, SMA50={last_candle.get('sma_50')}, SMA200={last_candle.get('sma_200')}")

                # Check previous candle to ensure it's a list correct
                print(f"History length: {len(bot.history)}")
        else:
            print("❌ Update function returned False.")
    except Exception as e:
        print(f"❌ Exception during update: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    verify()
