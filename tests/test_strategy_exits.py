import os
import sys

sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'backend')))

from strategies.base_strategy import BaseStrategy


class DummyStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("dummy")

    def get_required_indicators(self) -> list:
        return []

    def check_buy_signal(self, indicators, settings, state) -> bool:
        return False

    def check_sell_signal(self, indicators, settings, state) -> bool:
        return self.check_standard_exits(indicators, settings, state)


def test_adaptive_trailing_exits_when_price_loses_atr_band():
    strategy = DummyStrategy()
    indicators = {"rsi": 55, "atr": 2.0}
    settings = {
        "stop_loss_pct": 3.2,
        "sell_rsi": 75,
        "trailing_enabled": False,
        "rsi_trailing_pct": 0.8,
        "adaptive_trailing_enabled": True,
        "adaptive_trailing_atr_mult": 1.25,
        "adaptive_trailing_min_pct": 0.35,
        "adaptive_trailing_max_pct": 1.8,
        "take_profit_pct": 0,
    }
    state = {
        "current_price": 104.0,
        "entry_price": 100.0,
        "highest_price": 107.0,
    }
    assert strategy.check_sell_signal(indicators, settings, state) is True


if __name__ == "__main__":
    test_adaptive_trailing_exits_when_price_loses_atr_band()
    print("strategy exit tests ok")
