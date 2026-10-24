import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from harness.replay_spot import SpotReplay, normalize_settings
from harness.spot_data import SpotBar


SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT"]


def _snapshot():
    return {
        "settings": {
            "active_strategy": "smart_scalping", "timeframe": "1m",
            "symbol": "BTCUSDT", "rotation_watchlist": ",".join(SYMBOLS),
            "auto_asset_rotation": "False", "enable_fast_ema": "False",
            "enable_trend_filter": "False", "enable_buying": "True",
            "smart_scalper_entry_score": "0", "min_market_score_to_buy": "0",
            "auto_position_sizing": "True", "risk_per_trade_pct": "0.75",
            "stop_loss_pct": "1.5", "take_profit_pct": "1.5",
        },
        "state": {"enable_buying": "True", "enable_selling": "True"},
    }


def _market(count):
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    for index in range(count):
        now = start + timedelta(minutes=index)
        yield {symbol: SpotBar(now, 100.0, 100.1, 99.9, 100.0, 10.0)
               for symbol in SYMBOLS}


def test_snapshot_flags_are_real_booleans():
    normalized = normalize_settings(_snapshot())
    assert normalized["enable_trend_filter"] is False
    assert normalized["enable_fast_ema"] is False
    assert normalized["auto_asset_rotation"] is False


def test_replay_never_fills_before_next_bar_and_uses_one_wallet():
    replay = SpotReplay(_snapshot())
    start = datetime(2026, 9, 1, tzinfo=timezone.utc) + timedelta(minutes=1000)
    end = start + timedelta(minutes=4)
    trades, curve = replay.run(_market(1004), start, end)
    assert curve
    assert len(trades) == 1
    assert trades[0]["entry_time"] == start + timedelta(minutes=1)
    assert all(point["equity"] <= 47.2 for point in curve)


if __name__ == "__main__":
    test_snapshot_flags_are_real_booleans()
    test_replay_never_fills_before_next_bar_and_uses_one_wallet()
    print("spot replay tests ok")
