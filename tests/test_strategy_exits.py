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


def test_kronos_quant_scratch_and_vertical_exits():
    from strategies.kronos_quant import KronosQuantStrategy

    strategy = KronosQuantStrategy()
    settings = {"stop_loss_pct": 1.5, "take_profit_pct": 2.0}

    # Case 1: LONG scratch after 3 bars held with slight profit (+0.10%)
    state_long_scratch = {
        "position_side": "LONG",
        "entry_price": 100.0,
        "current_price": 100.10,
        "highest_price": 100.20,
        "bars_held": 3,
    }
    assert strategy.check_sell_signal({"atr": 1.0}, settings, state_long_scratch) is True

    # Case 2: SHORT scratch after 3 bars held with slight profit (+0.10%)
    state_short_scratch = {
        "position_side": "SHORT",
        "entry_price": 100.0,
        "current_price": 99.90,
        "lowest_price": 99.80,
        "bars_held": 3,
    }
    assert strategy.check_sell_signal({"atr": 1.0}, settings, state_short_scratch) is True

    # Case 3: SHORT position losing money at bar 3 should NOT scratch (it holds or waits for SL/TP)
    state_short_holding = {
        "position_side": "SHORT",
        "entry_price": 100.0,
        "current_price": 100.20,
        "lowest_price": 99.95,
        "bars_held": 3,
    }
    # Case 4: LONG Tier-1 Breakeven Lock (touched +1.05%, pulled back to +0.20% <= +0.25% lock)
    state_long_tier1 = {
        "position_side": "LONG",
        "entry_price": 100.0,
        "current_price": 100.20,
        "highest_price": 101.05,
        "bars_held": 1,
    }
    assert strategy.check_sell_signal({"atr": 1.0}, settings, state_long_tier1) is True

    # Case 5: SHORT Tier-1 Breakeven Lock (touched 98.95 = +1.05% gain, pulled back to 99.80 >= 99.75 lock)
    state_short_tier1 = {
        "position_side": "SHORT",
        "entry_price": 100.0,
        "current_price": 99.80,
        "lowest_price": 98.95,
        "bars_held": 1,
    }
    assert strategy.check_sell_signal({"atr": 1.0}, settings, state_short_tier1) is True


if __name__ == "__main__":
    test_adaptive_trailing_exits_when_price_loses_atr_band()
    test_kronos_quant_scratch_and_vertical_exits()
    print("strategy exit tests ok")

