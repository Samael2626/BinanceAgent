import os
import sys

sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'backend')))

from decision_trace import decision_reason_code, format_decision_trace
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
        "smart_scalper_entry_score": 58.0,
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
        "smart_scalper_entry_score": 58.0,
    }
    state = {"current_price": 98.0}

    assert strategy.check_buy_signal(indicators, settings, state) is False


def test_smart_scalper_buy_with_current_52_threshold_and_disabled_filters():
    strategy = SmartScalperStrategy()
    indicators = {
        "rsi": 42.0,
        "macd_hist": 0.2,
        "trend_ema": 120.0,
        "fast_ema": 120.0,
    }
    settings = {
        "buy_rsi": 38.0,
        "enable_trend_filter": False,
        "enable_fast_ema": False,
        "smart_scalper_entry_score": 52.0,
    }
    state = {"current_price": 100.0}

    score, reasons = strategy.score_buy_setup(indicators, settings, state)

    assert score >= 52.0
    assert "RSI near buy zone 42.0" in reasons
    assert "MACD momentum positive" in reasons
    assert "trend filter disabled" in reasons
    assert "fast EMA filter disabled" in reasons
    assert strategy.check_buy_signal(indicators, settings, state) is True


def test_entry_decision_trace_is_structured():
    line = format_decision_trace(
        "ENTRY_DECISION",
        symbol="SOLUSDT",
        signal="BUY",
        score=76.0,
        threshold=52,
        market_score=34,
        allowed=False,
        reason="lateral_market",
        detail="score passed before bot gate",
    )

    assert line.startswith("ENTRY_DECISION ")
    assert "symbol=SOLUSDT" in line
    assert "allowed=false" in line
    assert "reason=lateral_market" in line
    assert 'detail="score passed before bot gate"' in line
    assert decision_reason_code("cooldown activo (12s)") == "cooldown_active"


if __name__ == "__main__":
    test_smart_scalper_uses_entry_score_instead_of_perfect_conditions()
    test_smart_scalper_blocks_when_score_is_too_low()
    test_smart_scalper_buy_with_current_52_threshold_and_disabled_filters()
    test_entry_decision_trace_is_structured()
    print("smart scalper entry tests ok")
