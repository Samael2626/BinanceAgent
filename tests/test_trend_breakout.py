import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from harness.costs import CostModel
from harness.spot_data import SpotBar
from harness.trend_breakout import BreakoutConfig, BreakoutPortfolio, SYMBOLS, indicators


def _frames():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    frames = {}
    for symbol in SYMBOLS:
        bars = []
        for index in range(225):
            opened, high, low, close = 100.0, 100.5, 99.5, 100.0
            if symbol == "BTCUSDT" and index == 210:
                opened, high, low, close = 100.0, 102.0, 99.5, 102.0
            if symbol == "BTCUSDT" and index == 211:
                opened, high, low, close = 102.0, 103.0, 101.9, 102.5
            bars.append(SpotBar(start + timedelta(hours=4 * index), opened, high, low, close, 10.0))
        frames[symbol] = indicators(bars)
    return frames


def test_breakout_enters_on_next_bar_with_one_position():
    frames = _frames()
    portfolio = BreakoutPortfolio(BreakoutConfig(), CostModel.stress())
    trades, curve = portfolio.run(frames, frames["BTCUSDT"].index[200].to_pydatetime(),
                                  frames["BTCUSDT"].index[-1].to_pydatetime())
    assert trades
    assert all(trade["symbol"] == "BTCUSDT" for trade in trades)
    assert trades[0]["entry_time"] == frames["BTCUSDT"].index[211].to_pydatetime()
    assert curve


def test_breakout_skips_orders_below_minimum():
    frames = _frames()
    portfolio = BreakoutPortfolio(BreakoutConfig(initial_cash=9.0), CostModel.stress())
    trades, _ = portfolio.run(frames, frames["BTCUSDT"].index[200].to_pydatetime(),
                              frames["BTCUSDT"].index[-1].to_pydatetime())
    assert not trades


if __name__ == "__main__":
    test_breakout_enters_on_next_bar_with_one_position()
    test_breakout_skips_orders_below_minimum()
    print("trend breakout tests ok")
