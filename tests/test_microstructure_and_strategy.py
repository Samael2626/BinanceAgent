import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.microstructure import MicrostructureAnalyzer, classify_oi_regime, compute_order_book_imbalance
from backend.strategies.kronos_quant import KronosQuantStrategy


def test_microstructure_obi_and_regimes():
    book = {
        "bids": [["100.00", "30.0"], ["99.95", "20.0"]],
        "asks": [["100.02", "10.0"], ["100.05", "10.0"]],
    }
    obi_l1, obi_l5, spread_bps = compute_order_book_imbalance(book, levels=5)
    assert obi_l1 == 0.5
    assert obi_l5 > 0.4
    assert 1.5 <= spread_bps <= 2.5

    assert classify_oi_regime(0.8, 1.5) == "LONG_BUILDUP"
    assert classify_oi_regime(-0.9, 2.0) == "SHORT_BUILDUP"
    assert classify_oi_regime(0.7, -1.2) == "SHORT_COVERING"
    assert classify_oi_regime(-0.8, -1.5) == "LONG_LIQUIDATION"

    analyzer = MicrostructureAnalyzer()
    snap = analyzer.analyze(
        "SOLUSDT",
        book=book,
        funding_rate=-0.0004,  # -0.04% per 8h (crowded shorts -> bullish squeeze)
        mark_price=100.01,
        index_price=100.00,
        oi_change_pct=1.8,
        price_change_pct=0.6,
    )
    assert snap.oi_regime == "LONG_BUILDUP"
    assert snap.long_edge_bps_adj > 8.0
    assert snap.short_edge_bps_adj < -5.0


def test_kronos_quant_meta_labeling_long_short_and_gate():
    strat = KronosQuantStrategy()
    base_settings = {
        "market_type": "FUTURES",
        "futures_allow_short": True,
        "order_execution_style": "LIMIT_MAKER",
        "stop_loss_pct": 1.0,
        "take_profit_pct": 2.0,
        "kronos_min_ev_bps": 12.0,
        "kronos_min_rr_ratio": 1.8,
        "smart_scalper_entry_score": 65.0,
    }
    indicators = {
        "rsi": 48.0,
        "macd_hist": 0.25,
        "macd_signal": 0.1,
        "trend_ema": 99.0,
        "fast_ema": 99.8,
        "atr": 0.8,
        "adx": 28.0,
    }

    # 1. High-conviction LONG setup
    state_long = {
        "current_price": 100.0,
        "kronos_forecast": {
            "prob_up_net": 0.62,
            "prob_down_net": 0.25,
            "expected_return_pct": 1.4,
            "volatility_amp": 1.15,
            "rank_score": 78.0,
        },
        "microstructure": {
            "long_edge_bps_adj": 6.0,
            "short_edge_bps_adj": -5.0,
            "oi_regime": "LONG_BUILDUP",
            "spread_bps": 1.5,
        },
    }
    ev_long = strat.evaluate_setup(indicators, base_settings, state_long)
    assert ev_long["side"] == "LONG"
    assert ev_long["ev_bps"] >= 12.0
    assert strat.check_buy_signal(indicators, base_settings, state_long) is True

    # 2. High-conviction SHORT setup in FUTURES mode
    indicators_short = {**indicators, "rsi": 58.0, "macd_hist": -0.3, "trend_ema": 102.0}
    state_short = {
        "current_price": 100.0,
        "kronos_forecast": {
            "prob_up_net": 0.22,
            "prob_down_net": 0.65,
            "expected_return_pct": -1.6,
            "volatility_amp": 1.2,
            "rank_score": 82.0,
        },
        "microstructure": {
            "long_edge_bps_adj": -7.0,
            "short_edge_bps_adj": 8.0,
            "oi_regime": "SHORT_BUILDUP",
            "spread_bps": 1.5,
        },
    }
    ev_short = strat.evaluate_setup(indicators_short, base_settings, state_short)
    assert ev_short["side"] == "SHORT"
    assert ev_short["ev_bps"] >= 12.0
    assert strat.check_buy_signal(indicators_short, base_settings, state_short) is True

    # 3. Low-conviction noisy setup must be blocked by EV gate
    state_noise = {
        "current_price": 100.0,
        "kronos_forecast": {
            "prob_up_net": 0.35,
            "prob_down_net": 0.35,
            "expected_return_pct": 0.01,
            "volatility_amp": 0.4,
            "rank_score": 45.0,
        },
        "microstructure": {"long_edge_bps_adj": 0.0, "short_edge_bps_adj": 0.0, "spread_bps": 5.0},
    }
    ev_noise = strat.evaluate_setup(indicators, base_settings, state_noise)
    assert ev_noise["side"] == "NONE"
    assert strat.check_buy_signal(indicators, base_settings, state_noise) is False


if __name__ == "__main__":
    test_microstructure_obi_and_regimes()
    test_kronos_quant_meta_labeling_long_short_and_gate()
    print("microstructure and strategy tests ok")
