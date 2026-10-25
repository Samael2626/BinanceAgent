import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.futures_paper_broker import (
    FuturesPaperBroker,
    compute_isolated_liquidation_price,
)


class FakeDb:
    def __init__(self, initial_usdt="47", leverage="2"):
        self.state = {}
        self.settings = {
            "paper_initial_usdt": initial_usdt,
            "futures_leverage": leverage,
            "futures_maker_fee_pct": "0.02",
            "futures_taker_fee_pct": "0.05",
            "paper_latency_bps": "2",
            "futures_maint_margin_rate": "0.005",
        }

    def get_state(self, key, default=None, is_json=False, user_id=1):
        return self.state.get(key, default)

    def save_state(self, key, value, user_id=1):
        self.state[key] = value

    def get_setting(self, key, default=None, user_id=1):
        return self.settings.get(key, default)

    def save_setting(self, key, value, user_id=1):
        self.settings[key] = value


class FakeFuturesMarket:
    def __init__(self):
        self.client = None
        self.book = {
            "lastUpdateId": 777,
            "bids": [["100.00", "50.0"], ["99.90", "50.0"]],
            "asks": [["100.10", "50.0"], ["100.20", "50.0"]],
        }
        self.mark_price = 100.05
        self.min_notional = 5.0

    def get_futures_symbol_info(self, symbol):
        return {
            "symbol": symbol,
            "status": "TRADING",
            "filters": [
                {"filterType": "LOT_SIZE", "minQty": "0.01", "maxQty": "10000", "stepSize": "0.01"},
                {"filterType": "MIN_NOTIONAL", "notional": str(self.min_notional)},
            ],
        }

    def get_futures_order_book(self, symbol, limit=20):
        return self.book

    def get_futures_mark_price_and_funding(self, symbol):
        return {
            "symbol": symbol,
            "markPrice": self.mark_price,
            "indexPrice": 100.00,
            "lastFundingRate": 0.0001,
            "nextFundingTime": 1700000000000,
        }

    @staticmethod
    def _quantize_to_step(value, step_size, rounding):
        step = Decimal(str(step_size))
        val = Decimal(str(value))
        units = (val / step).to_integral_value(rounding=rounding)
        return float(units * step)

    def validate_futures_order(self, symbol, quantity, price):
        if quantity * price < self.min_notional:
            return False, f"min_notional_failed: {quantity * price:.2f} < {self.min_notional}"
        return True, "OK"


def test_long_and_short_lifecycle_with_maker_and_taker_fees():
    db = FakeDb(initial_usdt="47", leverage="2")
    market = FakeFuturesMarket()
    broker = FuturesPaperBroker(db, 1, market)

    assert broker.get_account_balance("USDT") == 47.0
    # 1. Open LONG with LIMIT_MAKER (0.02% fee, rests at best_bid=100.00)
    open_long = broker.place_order(
        "SOLUSDT",
        "BUY",
        order_type="LIMIT_MAKER",
        quote_order_qty=12.0,
        client_order_id="long_open_1",
    )
    assert open_long["status"] == "FILLED"
    assert Decimal(open_long["avgPrice"]) == Decimal("100.00")
    assert Decimal(open_long["feePct"]) == Decimal("0.02")
    # Idempotency check
    assert broker.place_order(
        "SOLUSDT",
        "BUY",
        order_type="LIMIT_MAKER",
        quote_order_qty=12.0,
        client_order_id="long_open_1",
    ) == open_long

    pos = broker.get_position()
    assert pos is not None
    assert pos["side"] == "LONG"
    assert Decimal(pos["isolated_margin"]) == Decimal("6.00")
    # Wallet balance should be 47 - 6.00 margin - 0.0024 fee = 40.9976
    assert Decimal("40.99") < Decimal(broker.account["wallet_balance"]) < Decimal("41.00")

    # 2. Apply positive funding (+0.02%): LONG pays funding
    f_rec = broker.apply_funding_if_due(Decimal("0.0002"), 1700000000000, mark_price=Decimal("100.00"))
    assert f_rec is not None
    assert Decimal(f_rec["cashflowUsdt"]) < Decimal("0")
    # Duplicate funding timestamp must be ignored
    assert broker.apply_funding_if_due(Decimal("0.0002"), 1700000000000, mark_price=Decimal("100.00")) is None

    # 3. Close LONG at higher price (profit)
    market.book["bids"] = [["105.00", "50.0"]]
    market.book["asks"] = [["105.10", "50.0"]]
    close_long = broker.place_order("SOLUSDT", "SELL", order_type="MARKET", client_order_id="long_close_1")
    assert close_long["status"] == "FILLED"
    assert broker.get_position() is None
    assert broker.get_account_balance("USDT") > 47.0

    # 4. Open SHORT with MARKET order (0.05% fee)
    open_short = broker.place_order(
        "SOLUSDT",
        "SELL",
        order_type="MARKET",
        quote_order_qty=12.0,
        client_order_id="short_open_1",
    )
    pos_short = broker.get_position()
    assert pos_short is not None
    assert pos_short["side"] == "SHORT"
    assert Decimal(open_short["feePct"]) == Decimal("0.05")

    # Positive funding (+0.02%): SHORT receives funding
    f_short = broker.apply_funding_if_due(Decimal("0.0002"), 1700028800000, mark_price=Decimal("105.00"))
    assert f_short is not None
    assert Decimal(f_short["cashflowUsdt"]) > Decimal("0")

    # Price drops to 98.0 -> close SHORT for profit
    market.book["bids"] = [["97.90", "50.0"]]
    market.book["asks"] = [["98.00", "50.0"]]
    close_short = broker.place_order("SOLUSDT", "BUY", order_type="LIMIT_MAKER", client_order_id="short_close_1")
    assert Decimal(close_short["realizedPnl"]) > Decimal("0")
    assert broker.get_position() is None


def test_isolated_liquidation_and_leverage_bounds():
    db = FakeDb(initial_usdt="47", leverage="3")
    market = FakeFuturesMarket()
    broker = FuturesPaperBroker(db, 1, market)

    # Reject > 3x leverage
    try:
        broker.set_leverage(5)
    except ValueError as exc:
        assert "apalancamiento" in str(exc)
    else:
        raise AssertionError("Leverage > 3x should be rejected")

    # Open LONG at ~100 with 3x leverage
    broker.place_order("SOLUSDT", "BUY", order_type="LIMIT_MAKER", quote_order_qty=15.0)
    pos = broker.get_position()
    assert pos is not None
    liq_price = Decimal(pos["liquidation_price"])
    assert Decimal("60") < liq_price < Decimal("70")

    # Mark price above liquidation -> no liquidation
    assert broker.check_mark_and_liquidate(mark_price=Decimal("80.0")) is None
    assert broker.get_position() is not None

    # Mark price breaches liquidation -> forced liquidation zeroes isolated position
    liq_event = broker.check_mark_and_liquidate(mark_price=liq_price - Decimal("0.5"))
    assert liq_event is not None
    assert broker.get_position() is None
    rep = broker.report()
    assert rep["liquidation_count"] == 1


if __name__ == "__main__":
    test_long_and_short_lifecycle_with_maker_and_taker_fees()
    test_isolated_liquidation_and_leverage_bounds()
    print("futures paper broker tests ok")
