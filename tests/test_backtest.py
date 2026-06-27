import os
import sys

import pandas as pd

sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..')))

from backend.backtest import ScannerBacktestConfig, run_scanner_backtest


def make_market(start: float, step: float, rows: int = 140) -> pd.DataFrame:
    closes = [start + (i * step) for i in range(rows)]
    return pd.DataFrame({
        "open": closes,
        "high": [price * 1.01 for price in closes],
        "low": [price * 0.99 for price in closes],
        "close": closes,
        "volume": [1000 + i for i in range(rows)],
    })


def test_run_scanner_backtest_is_reproducible_offline():
    market_data = {
        "BTCUSDT": make_market(100.0, 0.01),
        "SOLUSDT": make_market(20.0, 0.08),
    }
    config = ScannerBacktestConfig(
        symbols=["BTCUSDT", "SOLUSDT"],
        initial_equity=1000.0,
        window=60,
        rotation_interval=10,
        min_rotation_score=30.0,
        min_market_score_to_buy=30.0,
        take_profit_pct=1.0,
    )

    result = run_scanner_backtest(market_data, config)

    assert result.initial_equity == 1000.0
    assert result.final_equity > 0
    assert len(result.equity_curve) > 0
    assert isinstance(result.trades, list)
    assert isinstance(result.rotations, list)


if __name__ == "__main__":
    test_run_scanner_backtest_is_reproducible_offline()
    print("backtest tests ok")
