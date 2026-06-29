import os
import sys

import pandas as pd

sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..')))

from backend.backtest import ScannerBacktestConfig, run_scanner_backtest


class FakePredictiveEngine:
    def analyze(self, df: pd.DataFrame, current_price: float) -> dict:
        return {
            "market_score": 60,
            "breakout_prob": 45,
            "trend_strength": {"score": 55},
            "rvol": 1.25,
        }


def fake_indicators(df: pd.DataFrame, settings: dict) -> dict:
    return {
        "rsi": 42.0,
        "macd_hist": 0.08,
        "is_lateral": False,
    }


def make_market(start: float, step: float, rows: int = 70) -> pd.DataFrame:
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
        window=20,
        rotation_interval=5,
        min_rotation_score=30.0,
        min_market_score_to_buy=30.0,
        take_profit_pct=1.0,
        max_iterations=25,
    )

    result = run_scanner_backtest(
        market_data,
        config,
        predictive_engine=FakePredictiveEngine(),
        indicator_fn=fake_indicators,
    )

    assert result.initial_equity == 1000.0
    assert result.final_equity > 0
    assert 0 < len(result.equity_curve) <= config.max_iterations
    assert isinstance(result.trades, list)
    assert isinstance(result.rotations, list)
    assert isinstance(result.win_rate, float)
    assert isinstance(result.profit_factor, float)
    assert isinstance(result.max_drawdown_pct, float)
    assert isinstance(result.net_pnl, float)
    assert isinstance(result.return_pct, float)
    assert isinstance(result.total_trades, int)
    assert result.total_trades == len(result.trades)


if __name__ == "__main__":
    test_run_scanner_backtest_is_reproducible_offline()
    print("backtest tests ok")
