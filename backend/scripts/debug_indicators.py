import pandas as pd
import pandas_ta as ta
import numpy as np
import sys
import os

# Add backend to path to import indicators
current_dir = os.path.dirname(os.path.abspath(__file__))
# Assuming indicators.py is in backend/ folder which is the parent of scripts/
backend_path = os.path.dirname(current_dir)
sys.path.append(backend_path)

try:
    from indicators import calculate_indicators
except ImportError as e:
    print(f"Error importing indicators: {e}")
    sys.exit(1)


def test_indicators():
    print("Generating MOCK data...")
    # Create a dummy dataframe with enough data
    # 500 rows
    close_prices = np.random.normal(90000, 1000, 500)

    # Make sure we have some trend so MACD isn't zero
    trend = np.linspace(90000, 95000, 500)
    close_prices += trend

    df = pd.DataFrame({
        'open': close_prices,
        'high': close_prices + 10,
        'low': close_prices - 10,
        'close': close_prices,
        'volume': np.random.random(500) * 100
    })

    print(f"DataFrame shape: {df.shape}")

    settings = {
        'ema_length': 200,
        'macd_fast': 12,
        'macd_slow': 26,
        'macd_signal': 9
    }

    print("Running calculate_indicators...")
    # Clean previous log
    log_path = os.path.join(os.path.dirname(
        backend_path), "backend", "logs", "debug_indicators.log")
    if os.path.exists(log_path):
        os.remove(log_path)

    results = calculate_indicators(df, settings)
    print("\nResults returned:")
    for k, v in results.items():
        print(f"{k}: {v}")

    print(f"\nContent of {log_path}:")
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            print(f.read())
    else:
        print("Log file was NOT created.")


if __name__ == "__main__":
    test_indicators()
