import os
import sys

sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'backend')))

from binance_wrapper import BinanceWrapper


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


if __name__ == "__main__":
    test_normalize_quantity_respects_non_integer_step_size()
    test_validate_order_rejects_step_size_mismatch()
    test_quote_order_rejects_below_min_notional()
    test_quote_order_accepts_notional_12_when_symbol_allows_it()
    test_quote_order_rejects_when_min_notional_exceeds_12()
    test_symbol_info_cache_avoids_repeated_exchange_info_calls()
    test_place_order_surfaces_api_errors_without_hiding_them()
    print("binance order filter tests ok")
