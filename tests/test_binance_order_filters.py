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
    assert "10" in reason


if __name__ == "__main__":
    test_normalize_quantity_respects_non_integer_step_size()
    test_validate_order_rejects_step_size_mismatch()
    test_quote_order_rejects_below_min_notional()
    print("binance order filter tests ok")
