import os
import sys

sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'backend')))

from scanner import (
    RotationCandidate,
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


if __name__ == "__main__":
    test_parse_rotation_watchlist_normalizes_symbols()
    test_score_rotation_candidate_rewards_trend_and_penalizes_lateral()
    test_should_switch_rotation_candidate_requires_edge_and_threshold()
    print("scanner tests ok")
