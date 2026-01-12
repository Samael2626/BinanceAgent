import unittest.mock as mock
from backend.bot_logic import BinanceBot
from backend.indicators import calculate_predictive_metrics
import sys
import os
import pandas as pd
import pandas_ta as ta
import numpy as np

# Add project root to path
sys.path.append(os.getcwd())


def verify_math():
    print("--- Verifying Math ---")
    # Create Valid Dataframe
    periods = 100
    dates = pd.date_range(start='2024-01-01', periods=periods, freq='1min')
    close = np.linspace(100, 105, periods)  # Uptrend

    # Add noise
    close += np.random.normal(0, 0.5, periods)

    df = pd.DataFrame({
        'open': close - 0.2,
        'high': close + 0.5,
        'low': close - 0.5,
        'close': close,
        'volume': [1000.0] * periods
    }, index=dates)

    # Run calculation
    metrics = calculate_predictive_metrics(df)

    print("Metrics result:")
    print(metrics)

    # Assertions
    if metrics['market_score'] > 0:
        print("✅ Market Score calculated.")
    else:
        print("❌ Market Score invalid.")

    if len(metrics['projection']) == 3:
        print("✅ Projection has 3 points.")
    else:
        print(f"❌ Projection wrong length: {len(metrics['projection'])}")

    if metrics['expected_move']['min'] < metrics['expected_move']['max']:
        print("✅ Expected move range valid.")
    else:
        print("❌ Expected move range invalid.")


def verify_integration():
    print("\n--- Verifying Bot Integration ---")
    try:
        bot = BinanceBot()
        # Mock data client again
        pass  # We assume bot init works from previous tests

        # Check if get_status has prediction key
        status = bot.get_status()
        if 'prediction' in status:
            print("✅ 'prediction' key found in bot status.")
        else:
            print("❌ 'prediction' key MISSING in bot status.")

    except Exception as e:
        print(f"Bot integration error: {e}")


if __name__ == "__main__":
    verify_math()
    verify_integration()
