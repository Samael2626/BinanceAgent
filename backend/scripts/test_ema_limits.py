import pandas as pd
import pandas_ta as ta
import numpy as np


def test_ema_warmup():
    print("Testing EMA 150 with 172 data points...")

    # Create 172 data points
    count = 172
    close_prices = np.random.normal(90000, 1000, count)
    df = pd.DataFrame({'close': close_prices})

    # Calculate EMA 150
    ema = df.ta.ema(length=150)

    print(f"Dataframe length: {len(df)}")
    print(f"EMA Series length: {len(ema)}")
    print(f"Last value (iloc[-1]): {ema.iloc[-1]}")

    # Check if NaN
    if pd.isna(ema.iloc[-1]):
        print("RESULT: Last value is NaN (Insufficient data)")
        # Find first valid index
        valid_idx = ema.first_valid_index()
        print(f"First valid index is: {valid_idx}")
    else:
        print("RESULT: Last value is VALID")


if __name__ == "__main__":
    test_ema_warmup()
