import os
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.binance_wrapper import BinanceWrapper
from backend.services.market_data import closed_klines


def test_incomplete_kline_never_reaches_indicators():
    wrapper = BinanceWrapper.__new__(BinanceWrapper)

    class FakeClient:
        def get_klines(self, **kwargs):
            return [
                [1735689600000, "10", "11", "9", "10", "2", 1735689659999, 0, 0, 0, 0, 0],
                [1735689660000, "10", "20", "9", "19", "2", 1735689719999, 0, 0, 0, 0, 0],
            ]

    wrapper.client = FakeClient()
    frame = wrapper.get_historical_klines("BTCUSDT", "1m", limit=2)
    closed = closed_klines(frame, pd.Timestamp("2025-01-01T00:01:30Z"))
    assert len(closed) == 1
    assert closed.iloc[-1]["close"] == 10


if __name__ == "__main__":
    test_incomplete_kline_never_reaches_indicators()
    print("closed klines tests ok")
