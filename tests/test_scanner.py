import os
import sys

sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'backend')))

from scanner import (
    RotationCandidate,
    build_scanner_decision,
    parse_rotation_watchlist,
    score_rotation_candidate,
    should_switch_rotation_candidate,
)


def test_parse_rotation_watchlist_normalizes_symbols():
    symbols = parse_rotation_watchlist("btc, ethusdt, sol")
    assert symbols == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]


def test_score_rotation_candidate_rewards_trend_and_penalizes_lateral():
    prediction = {
        "market_score": 70,
        "breakout_prob": 60,
        "trend_strength": {"score": 80},
        "rvol": 1.8,
    }
    indicators = {"rsi": 55, "macd_hist": 1.5, "is_lateral": False}
    score = score_rotation_candidate(prediction, indicators)
    assert score > 60


def test_should_switch_rotation_candidate_requires_edge_and_threshold():
    best = RotationCandidate(
        symbol="SOLUSDT",
        score=68.0,
        market_score=65.0,
        breakout_prob=60.0,
        trend_strength=70.0,
        rsi=54.0,
        is_lateral=False,
    )
    assert should_switch_rotation_candidate("BTCUSDT", 60.0, best, 55.0) is True
    assert should_switch_rotation_candidate("BTCUSDT", 66.0, best, 55.0) is False
    assert should_switch_rotation_candidate("SOLUSDT", 60.0, best, 55.0) is False


def test_scanner_decision_reports_rejection_reasons():
    decision = build_scanner_decision(
        "SOLUSDT",
        candidate_score=21.0,
        min_candidate_score=52.0,
        prediction={
            "market_score": 30,
            "trend_strength": {"score": 20},
            "rvol": 0.2,
        },
        indicators={"is_lateral": True},
        candle_count=12,
        min_market_score=35.0,
        spread_bps=40,
        max_spread_bps=25,
    )

    assert decision["allowed"] is False
    assert decision["reason"] == "below_rotation_score"
    assert "insufficient_candles" in decision["reasons"]
    assert "low_volume" in decision["reasons"]
    assert "spread_too_wide" in decision["reasons"]
    assert "low_market_score" in decision["reasons"]
    assert "weak_trend" in decision["reasons"]


def test_scanner_decision_accepts_candidate_at_market_score_28():
    prediction = {
        "market_score": 28,
        "breakout_prob": 90,
        "trend_strength": {"score": 95},
        "rvol": 2.2,
    }
    indicators = {"rsi": 48, "macd_hist": 2.0, "is_lateral": False}
    score = score_rotation_candidate(prediction, indicators)
    decision = build_scanner_decision(
        "LINKUSDT",
        candidate_score=score,
        min_candidate_score=52.0,
        prediction=prediction,
        indicators=indicators,
        candle_count=300,
        min_market_score=28.0,
    )

    assert score >= 52.0
    assert decision["allowed"] is True
    assert decision["reason"] == "candidate_ok"
    assert "low_market_score" not in decision["reasons"]


def test_scanner_decision_handles_incomplete_candles():
    decision = build_scanner_decision(
        "ADAUSDT",
        candidate_score=None,
        min_candidate_score=52.0,
        candle_count=1,
    )

    assert decision["allowed"] is False
    assert decision["reason"] == "insufficient_candles"
    assert "insufficient_candles" in decision["reasons"]


if __name__ == "__main__":
    test_parse_rotation_watchlist_normalizes_symbols()
    test_score_rotation_candidate_rewards_trend_and_penalizes_lateral()
    test_should_switch_rotation_candidate_requires_edge_and_threshold()
    test_scanner_decision_reports_rejection_reasons()
    test_scanner_decision_accepts_candidate_at_market_score_28()
    test_scanner_decision_handles_incomplete_candles()
    print("scanner tests ok")
