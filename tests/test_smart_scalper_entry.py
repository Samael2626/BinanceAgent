import os
import sys

sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'backend')))

from strategies.smart_scalper import SmartScalperStrategy


def test_smart_scalper_uses_entry_score_instead_of_perfect_conditions():
    strategy = SmartScalperStrategy()
    indicators = {
        "rsi": 38.0,
        "macd_hist": -0.1,
        "trend_ema": 100.0,
        "fast_ema": 101.0,
    }
    settings = {
        "buy_rsi": 38.0,
        "enable_trend_filter": True,
        "enable_fast_ema": True,
        "smart_scalper_entry_score": 68.0,
    }
    state = {"current_price": 100.9}

    score, reasons = strategy.score_buy_setup(indicators, settings, state)

    assert score >= 68.0
    assert any("RSI" in reason for reason in reasons)
    assert strategy.check_buy_signal(indicators, settings, state) is True


def test_smart_scalper_blocks_when_score_is_too_low():
    strategy = SmartScalperStrategy()
    indicators = {
        "rsi": 46.0,
        "macd_hist": -1.2,
        "trend_ema": 100.0,
        "fast_ema": 100.0,
    }
    settings = {
        "buy_rsi": 38.0,
        "enable_trend_filter": True,
        "enable_fast_ema": True,
        "smart_scalper_entry_score": 68.0,
    }
    state = {"current_price": 98.0}

    assert strategy.check_buy_signal(indicators, settings, state) is False


if __name__ == "__main__":
    test_smart_scalper_uses_entry_score_instead_of_perfect_conditions()
    test_smart_scalper_blocks_when_score_is_too_low()
    print("smart scalper entry tests ok")
