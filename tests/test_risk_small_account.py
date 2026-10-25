import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.risk import calculate_futures_position_size
from backend.scanner import build_scanner_decision, score_rotation_candidate


def test_small_account_47_usdt_futures_sizing():
    # With 47 USDT equity, 0.75% risk per trade = 0.3525 USDT risk budget.
    # At 1.5% SL, risk-based notional = 0.3525 / 0.015 = 23.50 USDT.
    # At 2x leverage and 35% max margin (16.45 USDT margin -> 32.90 USDT notional cap),
    # SOLUSDT (min_notional = 5.0 USDT) receives 23.50 USDT notional (11.75 USDT margin).
    notional_sol = calculate_futures_position_size(
        equity=47.0,
        current_price=150.0,
        stop_loss_pct=1.5,
        atr=1.5,
        risk_per_trade_pct=0.75,
        atr_stop_mult=1.2,
        leverage=2,
        min_notional=5.0,
        max_margin_pct=35.0,
    )
    assert 15.0 <= notional_sol <= 24.0

    # BTCUSDT contract requiring 100 USDT min_notional must fail closed (0.0) on 47 USDT account
    notional_btc = calculate_futures_position_size(
        equity=47.0,
        current_price=90000.0,
        stop_loss_pct=1.5,
        atr=900.0,
        risk_per_trade_pct=0.75,
        atr_stop_mult=1.2,
        leverage=2,
        min_notional=100.0,
        max_margin_pct=35.0,
    )
    assert notional_btc == 0.0

    # Leverage > 3x must fail closed
    assert calculate_futures_position_size(
        equity=47.0,
        current_price=150.0,
        stop_loss_pct=1.5,
        atr=1.5,
        risk_per_trade_pct=0.75,
        atr_stop_mult=1.2,
        leverage=5,
        min_notional=5.0,
    ) == 0.0

    # Stop loss too wide relative to liquidation distance (e.g. 12% SL at 3x -> 36% >= 32.8% liq dist) must fail closed
    assert calculate_futures_position_size(
        equity=47.0,
        current_price=150.0,
        stop_loss_pct=12.0,
        atr=1.5,
        risk_per_trade_pct=0.75,
        atr_stop_mult=1.2,
        leverage=3,
        min_notional=5.0,
    ) == 0.0


def test_scanner_blocks_unreachable_min_notional_and_ranks_kronos():
    dec_blocked = build_scanner_decision(
        "BTCUSDT",
        candidate_score=80.0,
        min_candidate_score=55.0,
        candle_count=200,
        min_notional=100.0,
        max_affordable_notional=23.5,
    )
    assert dec_blocked["allowed"] is False
    assert dec_blocked["reason"] == "min_notional_exceeds_budget"

    base_pred = {"market_score": 60, "breakout_prob": 50, "trend_strength": {"score": 60}, "rvol": 1.3}
    ind = {"rsi": 48, "macd_hist": 0.2, "is_lateral": False}
    s_no_kronos = score_rotation_candidate(base_pred, ind)
    s_high_kronos = score_rotation_candidate(
        {**base_pred, "kronos_forecast": {"rank_score": 92.0}, "ev_bps": 22.0},
        ind,
    )
    assert s_high_kronos > s_no_kronos


if __name__ == "__main__":
    test_small_account_47_usdt_futures_sizing()
    test_scanner_blocks_unreachable_min_notional_and_ranks_kronos()
    print("risk small account tests ok")
