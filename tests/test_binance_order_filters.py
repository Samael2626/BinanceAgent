import os
import sys
import threading

from unittest import TestCase
from requests.exceptions import Timeout

sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..')))

from backend.binance_wrapper import BinanceWrapper, OrderStatusUnknown
from backend.bot_logic import BinanceBot


def _wrapper_with_info(info):
    wrapper = BinanceWrapper.__new__(BinanceWrapper)
    wrapper.get_symbol_info = lambda symbol: info
    return wrapper


def test_normalize_quantity_respects_non_integer_step_size():
    wrapper = _wrapper_with_info({
        "filters": [
            {"filterType": "LOT_SIZE", "minQty": "0.001", "maxQty": "100", "stepSize": "0.001"}
        ]
    })

    assert wrapper.normalize_quantity("BTCUSDT", 0.123456) == 0.123


def test_validate_order_rejects_step_size_mismatch():
    wrapper = _wrapper_with_info({
        "filters": [
            {"filterType": "LOT_SIZE", "minQty": "0.001", "maxQty": "100", "stepSize": "0.001"},
            {"filterType": "MIN_NOTIONAL", "minNotional": "5"},
        ]
    })

    ok, reason = wrapper.validate_order("BTCUSDT", 0.123456, 100.0)

    assert ok is False
    assert reason.startswith("step_size_failed:")
    assert "stepSize" in reason


def test_quote_order_rejects_below_min_notional():
    wrapper = _wrapper_with_info({
        "filters": [
            {"filterType": "MARKET_LOT_SIZE", "minQty": "0", "maxQty": "100", "stepSize": "0.000001"},
            {"filterType": "MIN_NOTIONAL", "minNotional": "10"},
        ]
    })

    ok, reason = wrapper.validate_order("SOLUSDT", 8.0, 100.0, is_quote_qty=True)

    assert ok is False
    assert reason.startswith("min_notional_failed:") or "mínimo" in reason or "mÃ­nimo" in reason
    assert "10" in reason


def test_quote_order_accepts_notional_12_when_symbol_allows_it():
    wrapper = _wrapper_with_info({
        "filters": [
            {"filterType": "MARKET_LOT_SIZE", "minQty": "0", "maxQty": "100", "stepSize": "0.000001"},
            {"filterType": "MIN_NOTIONAL", "minNotional": "10"},
        ]
    })

    ok, reason = wrapper.validate_order("SOLUSDT", 12.0, 100.0, is_quote_qty=True)

    assert ok is True
    assert reason == "OK"


def test_quote_order_rejects_when_min_notional_exceeds_12():
    wrapper = _wrapper_with_info({
        "filters": [
            {"filterType": "MARKET_LOT_SIZE", "minQty": "0", "maxQty": "100", "stepSize": "0.000001"},
            {"filterType": "MIN_NOTIONAL", "minNotional": "15"},
        ]
    })

    ok, reason = wrapper.validate_order("SOLUSDT", 12.0, 100.0, is_quote_qty=True)

    assert ok is False
    assert reason.startswith("min_notional_failed:")
    assert "15" in reason


def test_symbol_info_cache_avoids_repeated_exchange_info_calls():
    wrapper = BinanceWrapper.__new__(BinanceWrapper)
    calls = {"count": 0}

    class FakeClient:
        def get_symbol_info(self, symbol):
            calls["count"] += 1
            return {"symbol": symbol, "filters": []}

    wrapper.client = FakeClient()
    wrapper._symbol_info_cache = {}

    first = wrapper.get_symbol_info("SOLUSDT")
    second = wrapper.get_symbol_info("SOLUSDT")

    assert first == second
    assert calls["count"] == 1


def test_place_order_surfaces_api_errors_without_hiding_them():
    wrapper = BinanceWrapper.__new__(BinanceWrapper)
    wrapper.testnet = True
    wrapper.normalize_quantity = lambda symbol, quantity: quantity

    class FakeClient:
        def create_order(self, **params):
            raise RuntimeError("HTTP 429 rate limit")

    wrapper.client = FakeClient()

    try:
        wrapper.place_order("SOLUSDT", "BUY", 12.0, quote_order_qty=12.0)
    except RuntimeError as exc:
        assert "HTTP 429" in str(exc)
    else:
        raise AssertionError("place_order should surface API/runtime errors")


def test_timeout_recovers_order_by_same_client_id_without_resubmitting():
    wrapper = BinanceWrapper.__new__(BinanceWrapper)
    wrapper.testnet = True
    calls = []

    class FakeClient:
        def create_order(self, **params):
            calls.append(("create", params))
            raise Timeout()

        def get_order(self, **params):
            calls.append(("query", params))
            return {"status": "FILLED", "executedQty": "0.1"}

    wrapper.client = FakeClient()
    order = wrapper.place_order("SOLUSDT", "BUY", 12.0, quote_order_qty=12.0)

    assert order["status"] == "FILLED"
    assert [kind for kind, _ in calls] == ["create", "query"]
    assert calls[1][1]["origClientOrderId"] == calls[0][1]["newClientOrderId"]
    assert calls[0][1]["newOrderRespType"] == "FULL"


def test_timeout_with_failed_query_keeps_order_status_unknown():
    wrapper = BinanceWrapper.__new__(BinanceWrapper)
    wrapper.testnet = True

    class FakeClient:
        def create_order(self, **params):
            raise Timeout()

        def get_order(self, **params):
            raise Timeout()

    wrapper.client = FakeClient()
    with TestCase().assertRaises(OrderStatusUnknown) as exc:
        wrapper.place_order("SOLUSDT", "BUY", 12.0, quote_order_qty=12.0)
    assert exc.exception.symbol == "SOLUSDT"
    assert exc.exception.client_order_id.startswith("ba")


def test_wrapper_blocks_real_buy_before_api_call():
    wrapper = BinanceWrapper.__new__(BinanceWrapper)
    wrapper.testnet = False

    class FakeClient:
        def create_order(self, **params):
            raise AssertionError("real order should not reach Binance")

    wrapper.client = FakeClient()
    with TestCase().assertRaisesRegex(RuntimeError, "Compras REAL bloqueadas"):
        wrapper.place_order("SOLUSDT", "BUY", 0.1)


def _bot_for_order_test(client):
    class FakeDb:
        def __init__(self):
            self.state = {}

        def save_state(self, key, value, user_id):
            self.state[key] = value

    bot = BinanceBot.__new__(BinanceBot)
    bot.user_id = 1
    bot.db = FakeDb()
    bot.client = client
    bot._order_lock = threading.RLock()
    bot.pending_order = {}
    bot.is_testnet = True
    bot.is_running = True
    bot.enable_buying = True
    bot._log = lambda *args: None
    return bot


def test_unknown_order_persists_and_blocks_resubmission():
    class FakeClient:
        def __init__(self):
            self.calls = 0

        def place_order(self, symbol, side, quantity, **kwargs):
            self.calls += 1
            raise OrderStatusUnknown(symbol, kwargs["client_order_id"])

    client = FakeClient()
    bot = _bot_for_order_test(client)
    with TestCase().assertRaises(OrderStatusUnknown):
        bot._submit_order("SOLUSDT", "BUY", 12.0, 100.0, "AUTO", 12.0)
    assert bot.pending_order["client_order_id"] == bot.db.state["pending_order"]["client_order_id"]
    assert bot.db.state["is_running"] == "False"
    assert bot.db.state["enable_buying"] is False
    with TestCase().assertRaises(OrderStatusUnknown):
        bot._submit_order("SOLUSDT", "BUY", 12.0, 100.0, "AUTO", 12.0)
    assert client.calls == 1


def test_submission_error_keeps_pending_order_until_reconciled():
    class FakeClient:
        def place_order(self, symbol, side, quantity, **kwargs):
            raise RuntimeError("exchange response unavailable")

    bot = _bot_for_order_test(FakeClient())
    with TestCase().assertRaises(RuntimeError):
        bot._submit_order("SOLUSDT", "BUY", 12.0, 100.0, "AUTO", 12.0)
    assert bot.pending_order == bot.db.state["pending_order"]
    assert bot.is_running is False


def test_real_buy_is_blocked_before_submission():
    class FakeClient:
        def place_order(self, *args, **kwargs):
            raise AssertionError("real order should not be submitted")

    bot = _bot_for_order_test(FakeClient())
    bot.is_testnet = False
    with TestCase().assertRaisesRegex(RuntimeError, "Compras REAL bloqueadas"):
        bot._submit_order("SOLUSDT", "BUY", 12.0, 100.0, "AUTO", 12.0)
    assert bot.pending_order == {}
    assert bot.db.state == {}


def test_confirmed_fill_clears_pending_after_position_update():
    class FakeClient:
        def place_order(self, symbol, side, quantity, **kwargs):
            return {"status": "FILLED", "executedQty": "0.1", "clientOrderId": kwargs["client_order_id"]}

    bot = _bot_for_order_test(FakeClient())
    handled = []
    bot._handle_trade_execution = lambda trade, side, strategy, qty, price: handled.append(trade) or trade
    result = bot._submit_order("SOLUSDT", "BUY", 12.0, 100.0, "AUTO", 12.0)
    assert result["status"] == "FILLED"
    assert len(handled) == 1
    assert bot.pending_order == {}
    assert bot.db.state["pending_order"] == {}


if __name__ == "__main__":
    test_normalize_quantity_respects_non_integer_step_size()
    test_validate_order_rejects_step_size_mismatch()
    test_quote_order_rejects_below_min_notional()
    test_quote_order_accepts_notional_12_when_symbol_allows_it()
    test_quote_order_rejects_when_min_notional_exceeds_12()
    test_symbol_info_cache_avoids_repeated_exchange_info_calls()
    test_place_order_surfaces_api_errors_without_hiding_them()
    test_timeout_recovers_order_by_same_client_id_without_resubmitting()
    test_timeout_with_failed_query_keeps_order_status_unknown()
    test_wrapper_blocks_real_buy_before_api_call()
    test_unknown_order_persists_and_blocks_resubmission()
    test_submission_error_keeps_pending_order_until_reconciled()
    test_real_buy_is_blocked_before_submission()
    test_confirmed_fill_clears_pending_after_position_update()
    print("binance order filter tests ok")
