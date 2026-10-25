"""
Tests for Step 1: Real-time Force Order Tracker (RAM buffer) and Smart Post-Only GTX Execution.
"""

from decimal import Decimal
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.microstructure import ForceOrderWindowTracker, MicrostructureAnalyzer
from backend.futures_paper_broker import FuturesPaperBroker


class MockDB:
    def __init__(self):
        self._state = {}
        self._settings = {
            "paper_initial_usdt": "47",
            "futures_leverage": "2",
            "futures_maker_fee_pct": "0.02",
            "futures_taker_fee_pct": "0.05",
            "paper_latency_bps": "2",
            "futures_maint_margin_rate": "0.005",
        }

    def get_state(self, key, default=None, is_json=False, user_id=None):
        return self._state.get(key, default)

    def save_state(self, key, value, user_id=None):
        self._state[key] = value

    def get_setting(self, key, default=None, user_id=None):
        return self._settings.get(key, default)

    def save_setting(self, key, value, user_id=None):
        self._settings[key] = str(value)


class MockMarket:
    def __init__(self):
        self.client = None
        self.testnet = True

    def get_futures_symbol_info(self, symbol: str):
        return {
            "symbol": symbol,
            "status": "TRADING",
            "filters": [
                {"filterType": "LOT_SIZE", "minQty": "0.01", "maxQty": "1000", "stepSize": "0.01"},
                {"filterType": "PRICE_FILTER", "tickSize": "0.01"},
                {"filterType": "MIN_NOTIONAL", "notional": "5.0"},
            ],
        }

    def get_futures_order_book(self, symbol: str, limit: int = 20):
        return {
            "bids": [["150.00", "50.0"], ["149.95", "40.0"]],
            "asks": [["150.05", "45.0"], ["150.10", "60.0"]],
            "lastUpdateId": 99999,
        }

    def validate_futures_order(self, symbol: str, quantity: float, price: float):
        return (True, "OK") if quantity * price >= 5.0 else (False, "below min notional")

    def _quantize_to_step(self, val: float, step: str, rounding=None):
        step_dec = Decimal(str(step))
        val_dec = Decimal(str(val))
        return float((val_dec // step_dec) * step_dec)


def test_force_order_window_tracker_ram_limits_and_purging():
    tracker = ForceOrderWindowTracker(maxlen=10, default_window_sec=60)
    now_ms = 1_000_000_000

    # Record 5 events 100 seconds ago (expired)
    for i in range(5):
        tracker.record_event("SOLUSDT", "SELL", 150.0, 10.0, timestamp_ms=now_ms - 100_000 + i * 10)

    # Record 4 events inside the 60s window
    tracker.record_event("SOLUSDT", "SELL", 150.0, 20.0, timestamp_ms=now_ms - 20_000)
    tracker.record_event("SOLUSDT", "SELL", 150.0, 30.0, timestamp_ms=now_ms - 10_000)
    tracker.record_event("SOLUSDT", "BUY", 150.0, 10.0, timestamp_ms=now_ms - 5_000)
    tracker.record_event("BTCUSDT", "SELL", 60000.0, 1.0, timestamp_ms=now_ms - 2_000)

    stats = tracker.get_window_stats("SOLUSDT", window_sec=60, now_ms=now_ms)
    assert stats["event_count"] == 3
    assert stats["long_forced_close_usdt"] == (20.0 + 30.0) * 150.0  # 7500 USDT
    assert stats["short_forced_close_usdt"] == 10.0 * 150.0           # 1500 USDT
    assert stats["total_forced_close_usdt"] == 9000.0
    assert stats["forced_close_imbalance"] < 0  # more longs liquidated than shorts


def test_microstructure_incorporates_force_order_absorption_edge():
    analyzer = MicrostructureAnalyzer()
    book = {
        "bids": [["150.00", "100.0"], ["149.95", "80.0"]],
        "asks": [["150.05", "20.0"], ["150.10", "15.0"]],
    }

    # Baseline with no forced-close absorption
    base_snap = analyzer.analyze("SOLUSDT", book=book, funding_rate=0.0001)

    # Spike in long forced closes (long liquidation cascade absorbed by strong bid book)
    absorbed_snap = analyzer.analyze(
        "SOLUSDT",
        book=book,
        funding_rate=0.0001,
        long_forced_close_usdt=50_000.0,
        short_forced_close_usdt=2_000.0,
    )

    assert absorbed_snap.long_edge_bps_adj > base_snap.long_edge_bps_adj
    assert absorbed_snap.long_forced_close_usdt == 50_000.0


def test_smart_maker_order_gtx_execution():
    db = MockDB()
    market = MockMarket()
    broker = FuturesPaperBroker(db=db, user_id=1, market=market)

    # Open position with Smart Post-Only GTX Maker
    order = broker.place_smart_maker_order("SOLUSDT", "BUY", quantity=0.1, max_reprice_attempts=2)
    assert order["status"] == "FILLED"
    assert order["timeInForce"] == "GTX"
    assert order["postOnly"] is True
    assert order["executionStyle"] == "SMART_GTX_PEG"
    assert float(order["price"]) == 150.0  # best bid
    assert float(order["feePct"]) == 0.02  # Maker fee!

    # Close position with Smart Post-Only GTX Maker
    close_order = broker.place_smart_maker_order("SOLUSDT", "SELL", quantity=0.1, reduce_only=True)
    assert close_order["status"] == "FILLED"
    assert close_order["timeInForce"] == "GTX"
    assert close_order["postOnly"] is True
    assert float(close_order["price"]) == 150.05  # best ask
    assert float(close_order["feePct"]) == 0.02  # Maker fee!


if __name__ == "__main__":
    test_force_order_window_tracker_ram_limits_and_purging()
    test_microstructure_incorporates_force_order_absorption_edge()
    test_smart_maker_order_gtx_execution()
    print("ALL STEP 1 TESTS PASSED SUCCESSFULLY!")
