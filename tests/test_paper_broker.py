import os
import sys
import tempfile
import gc
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.paper_broker import PaperBroker, fill_from_book
from backend.bot_logic import BinanceBot
from backend.database import DatabaseManager


class FakeDb:
    def __init__(self):
        self.state = {}

    def get_state(self, key, default=None, is_json=False, user_id=1):
        return self.state.get(key, default)

    def save_state(self, key, value, user_id=1):
        self.state[key] = value

    def get_setting(self, key, default=None, user_id=1):
        return default

    def save_trade(self, trade, user_id=1):
        self.state.setdefault("trades", []).append(trade)


class FakeClient:
    def __init__(self):
        self.calls = 0
        self.book = {"lastUpdateId": 123, "asks": [["101", "1"]],
                     "bids": [["99", "1"]]}

    def get_order_book(self, **kwargs):
        self.calls += 1
        return self.book

    def create_order(self, **kwargs):
        raise AssertionError("PAPER must not call create_order")


class FakeMarket:
    def __init__(self):
        self.client = FakeClient()
        self.valid = True

    def get_symbol_info(self, symbol):
        return {"symbol": symbol, "filters": []}

    def validate_order(self, *args, **kwargs):
        return self.valid, "filter rejected" if not self.valid else "OK"


def test_spread_fees_and_persistent_wallet():
    db = FakeDb()
    market = FakeMarket()
    broker = PaperBroker(db, 1, market)
    assert broker.get_account_balance("USDT") == 47
    buy = broker.place_order("BTCUSDT", "BUY", 12, quote_order_qty=12,
                             client_order_id="buy1")
    assert market.client.calls == 1
    assert buy["status"] == "FILLED"
    assert Decimal(buy["fills"][0]["price"]) > Decimal("101")
    assert buy["fills"][0]["commissionAsset"] == "BTC"
    assert Decimal(broker.account["quote"]) < Decimal("47")
    assert broker.get_account_balance("BTC") < float(buy["executedQty"])
    assert broker.place_order("BTCUSDT", "BUY", 12, quote_order_qty=12,
                              client_order_id="buy1") == buy
    assert market.client.calls == 1

    restarted = PaperBroker(db, 1, market)
    assert restarted.get_order_by_client_id("BTCUSDT", "buy1") == buy
    amount = restarted.get_account_balance("BTC")
    sell = restarted.place_order("BTCUSDT", "SELL", amount, client_order_id="sell1")
    assert Decimal(sell["fills"][0]["price"]) < Decimal("99")
    assert sell["fills"][0]["commissionAsset"] == "USDT"
    assert restarted.get_account_balance("USDT") < 47
    assert restarted.get_account_balance("BTC") == 0
    report = restarted.report()
    assert report["mode"] == "PAPER"
    assert report["order_count"] == 2
    assert Decimal(report["fees_paid_usdt"]) > 0
    assert report["orders"][0]["bestAsk"] == "101"
    assert report["orders"][0]["bookUpdateId"] == 123


def test_insufficient_depth_and_filters_leave_wallet_untouched():
    db = FakeDb()
    market = FakeMarket()
    broker = PaperBroker(db, 1, market)
    market.client.book["asks"] = [["101", "0.01"]]
    try:
        broker.place_order("BTCUSDT", "BUY", 12, quote_order_qty=12)
    except ValueError as exc:
        assert "profundidad" in str(exc)
    else:
        raise AssertionError("order must be rejected")
    assert broker.get_account_balance("USDT") == 47
    assert broker.account["orders"] == {}

    market.client.book["asks"] = [["101", "1"]]
    market.valid = False
    try:
        broker.place_order("BTCUSDT", "BUY", 12, quote_order_qty=12)
    except ValueError as exc:
        assert "filter rejected" in str(exc)
    else:
        raise AssertionError("order must be rejected")
    assert broker.account["orders"] == {}


def test_book_fill_requires_full_liquidity():
    book = {"asks": [["100", "0.1"], ["101", "0.1"]]}
    filled, notional, levels = fill_from_book(
        book, "BUY", Decimal("0.15"), None, Decimal("0"))
    assert filled == Decimal("0.15")
    assert notional == Decimal("15.05")
    assert len(levels) == 2
    try:
        fill_from_book(book, "BUY", Decimal("0.3"), None, Decimal("0"))
    except ValueError as exc:
        assert "profundidad" in str(exc)
    else:
        raise AssertionError("depth check failed")


def test_sqlite_restart_preserves_virtual_balances_and_journal():
    with tempfile.TemporaryDirectory() as directory:
        path = str(Path(directory) / "paper.db")
        db = DatabaseManager(path)
        user_id = db.create_user("paper", "", "", True)
        db.save_setting("paper_initial_usdt", "47", user_id=user_id)
        broker = PaperBroker(db, user_id, FakeMarket())
        order = broker.place_order("BTCUSDT", "BUY", 12, quote_order_qty=12,
                                   client_order_id="restart-buy")
        reloaded = PaperBroker(DatabaseManager(path), user_id, FakeMarket())
        assert reloaded.get_order_by_client_id("BTCUSDT", "restart-buy") == order
        assert reloaded.get_account_balance("USDT") == broker.get_account_balance("USDT")
        assert reloaded.get_account_balance("BTC") == broker.get_account_balance("BTC")
        del reloaded, broker, db
        gc.collect()


def test_bot_pnl_matches_virtual_wallet_after_fees():
    db = FakeDb()
    broker = PaperBroker(db, 1, FakeMarket())
    bot = BinanceBot.__new__(BinanceBot)
    bot.db = db
    bot.user_id = 1
    bot.is_paper = True
    bot.is_testnet = True
    bot.symbol = "BTCUSDT"
    bot.entry_price = 0.0
    bot.accumulated_qty = 0.0
    bot.position_orders = 0
    bot.open_position = False
    bot.highest_price = 0.0
    bot.last_buy_price = 0.0
    bot._consecutive_losses = 0
    bot.max_consecutive_losses = 3
    bot.cooldown_minutes = 3
    bot.rsi = 50.0
    bot.trades = []
    bot._log = lambda *args: None
    bot._get_scoped_key = lambda key: key
    bot._reset_position_state = lambda: None
    bot._update_account_balances = lambda: None
    bot._send_trade_notification = lambda trade: None
    bot._print_state_snapshot = lambda: None

    buy = broker.place_order("BTCUSDT", "BUY", 12, quote_order_qty=12,
                             client_order_id="integration-buy")
    bot._handle_trade_execution(buy, "BUY", "PAPER", 12, 101)
    assert bot.accumulated_qty == broker.get_account_balance("BTC")
    assert bot.entry_price > 101

    sell = broker.place_order("BTCUSDT", "SELL", broker.get_account_balance("BTC"),
                              client_order_id="integration-sell")
    bot._handle_trade_execution(sell, "SELL", "PAPER", float(sell["executedQty"]), 99)
    wallet_pnl = broker.get_account_balance("USDT") - 47
    assert abs(bot.trades[0]["pnl"] - wallet_pnl) < 0.00001
    assert bot.trades[0]["commission"] > 0
    assert bot.trades[1]["commission"] > 0


if __name__ == "__main__":
    test_spread_fees_and_persistent_wallet()
    test_insufficient_depth_and_filters_leave_wallet_untouched()
    test_book_fill_requires_full_liquidity()
    test_sqlite_restart_preserves_virtual_balances_and_journal()
    test_bot_pnl_matches_virtual_wallet_after_fees()
    print("paper broker tests ok")
