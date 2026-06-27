import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from risk import (
    calculate_position_quote_size,
    sanitize_timeframe,
    should_halt_buying,
    should_trigger_portfolio_kill_switch,
)


def test_sanitize_timeframe():
    assert sanitize_timeframe("15m") == "15m"
    assert sanitize_timeframe("off") == "15m"


def test_calculate_position_quote_size_caps_to_equity():
    size = calculate_position_quote_size(
        equity=1000.0,
        current_price=100.0,
        stop_loss_pct=3.0,
        atr=2.5,
        risk_per_trade_pct=1.0,
        atr_stop_mult=1.5,
        min_order_quote=10.0,
        max_position_pct=25.0,
    )
    assert 10.0 <= size <= 250.0


def test_calculate_position_quote_size_returns_zero_when_balance_below_minimum():
    size = calculate_position_quote_size(
        equity=8.0,
        current_price=100.0,
        stop_loss_pct=3.0,
        atr=1.0,
        risk_per_trade_pct=1.0,
        atr_stop_mult=1.5,
        min_order_quote=10.0,
        max_position_pct=25.0,
    )
    assert size == 0.0


def test_should_halt_buying_on_loss_guard():
    blocked, reason = should_halt_buying(
        daily_pnl=-60.0,
        baseline_equity=1000.0,
        max_daily_loss_pct=5.0,
        consecutive_losses=0,
        max_consecutive_losses=3,
        trading_halt_until=0.0,
        market_score=55.0,
        min_market_score_to_buy=45.0,
    )
    assert blocked is True
    assert "limite de perdida diaria" in reason


def test_should_trigger_portfolio_kill_switch():
    blocked, reason = should_trigger_portfolio_kill_switch(
        equity=860.0,
        baseline_equity=1000.0,
        max_drawdown_pct=12.0,
    )
    assert blocked is True
    assert "drawdown global" in reason


if __name__ == "__main__":
    test_sanitize_timeframe()
    test_calculate_position_quote_size_caps_to_equity()
    test_calculate_position_quote_size_returns_zero_when_balance_below_minimum()
    test_should_halt_buying_on_loss_guard()
    test_should_trigger_portfolio_kill_switch()
    print("risk tests ok")
