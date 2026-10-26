import base64
import hashlib
import logging
import sqlite3
import tempfile
import threading
import unittest
from logging.handlers import RotatingFileHandler
from pathlib import Path
from unittest.mock import MagicMock, patch

from cryptography.fernet import Fernet

from backend.binance_wrapper import BinanceWrapper
from backend.bot_logic import BinanceBot, _bot_logger
from backend.database import DatabaseManager
from backend.strategies.kronos_quant import KronosQuantStrategy


class StateDB:
    def __init__(self):
        self.values = {}

    def save_state(self, key, value, user_id=1):
        self.values[key] = value

    def get_state(self, key, default=None, user_id=1):
        return self.values.get(key, default)


def make_bot():
    bot = object.__new__(BinanceBot)
    bot.user_id = 1
    bot.symbol = "ETHUSDT"
    bot.market_type = "FUTURES"
    bot.is_paper = False
    bot.is_testnet = True
    bot.order_execution_style = "MARKET"
    bot.position_side = "LONG"
    bot.pending_order = {}
    bot._order_lock = threading.RLock()
    bot.db = StateDB()
    bot.client = MagicMock()
    bot.client.get_futures_open_positions.return_value = []
    bot.client.get_futures_open_entry_orders.return_value = []
    bot.client.get_futures_account_balance.return_value = {"available": 47.0, "total": 47.0}
    bot._handle_trade_execution = MagicMock(return_value={"status": "FILLED"})
    bot._reset_position_state = MagicMock()
    bot._log = MagicMock()
    bot.is_running = True
    bot.enable_buying = True
    return bot


class TestFuturesRemediation(unittest.TestCase):
    def setUp(self):
        self.wrapper = object.__new__(BinanceWrapper)
        self.wrapper.client = MagicMock()
        self.wrapper.get_futures_symbol_info = MagicMock(return_value={
            "symbol": "ETHUSDT", "status": "TRADING", "filters": [
                {"filterType": "LOT_SIZE", "minQty": "0.001", "maxQty": "1000", "stepSize": "0.001"},
                {"filterType": "MARKET_LOT_SIZE", "minQty": "0.001", "maxQty": "1000", "stepSize": "0.001"},
                {"filterType": "MIN_NOTIONAL", "notional": "5"},
                {"filterType": "PRICE_FILTER", "minPrice": "0.01", "maxPrice": "100000", "tickSize": "0.01"},
            ],
        })

    def test_futures_filters_and_normalization(self):
        self.assertEqual(self.wrapper.normalize_futures_quantity("ETHUSDT", 0.0129), 0.012)
        self.assertEqual(self.wrapper.normalize_futures_price("ETHUSDT", 2500.019), 2500.01)
        self.assertFalse(self.wrapper.validate_futures_order("ETHUSDT", 0.0129, 2500.0)[0])
        self.assertFalse(self.wrapper.validate_futures_order("ETHUSDT", 0.012, 2500.015, "STOP_MARKET")[0])
        self.assertTrue(self.wrapper.validate_futures_order("ETHUSDT", 0.012, 2500.01)[0])

    def test_account_position_lookup_fails_closed(self):
        self.wrapper.client.futures_position_information.side_effect = TimeoutError("API timeout")
        with self.assertRaises(TimeoutError):
            self.wrapper.get_futures_open_positions()

    def test_setup_requires_one_way_isolated_two_x(self):
        self.wrapper.client.futures_get_position_mode.return_value = {"dualSidePosition": False}
        self.wrapper.client.futures_change_leverage.return_value = {"leverage": 2}
        self.assertTrue(self.wrapper.setup_futures_symbol("ETHUSDT", 2, "ISOLATED"))
        self.wrapper.client.futures_change_margin_type.assert_called_once_with(
            symbol="ETHUSDT", marginType="ISOLATED"
        )
        with self.assertRaises(ValueError):
            self.wrapper.setup_futures_symbol("ETHUSDT", 3, "ISOLATED")
        self.wrapper.client.futures_get_position_mode.return_value = {"dualSidePosition": True}
        with self.assertRaises(RuntimeError):
            self.wrapper.setup_futures_symbol("ETHUSDT", 2, "ISOLATED")

    def test_entry_and_stop_use_distinct_fapi_endpoints(self):
        self.wrapper.client.futures_create_order.return_value = {"status": "FILLED"}
        self.wrapper.place_futures_order("ETHUSDT", "BUY", 0.012)
        self.wrapper.client.futures_create_order.assert_called_once()
        self.wrapper.client.futures_create_algo_order.return_value = {
            "algoStatus": "NEW", "clientAlgoId": "stop_test"
        }
        stop = self.wrapper.place_futures_stop_market(
            "ETHUSDT", "SELL", 2462.019, client_order_id="stop_test"
        )
        self.assertEqual(stop["clientAlgoId"], "stop_test")
        params = self.wrapper.client.futures_create_algo_order.call_args.kwargs
        self.assertEqual(params["algoType"], "CONDITIONAL")
        self.assertEqual(params["type"], "STOP_MARKET")
        self.assertEqual(params["triggerPrice"], "2462.01")
        self.assertEqual(params["closePosition"], "true")
        self.assertEqual(params["workingType"], "CONTRACT_PRICE")
        self.assertNotIn("quantity", params)
        self.assertNotIn("stopPrice", params)

    def test_global_mutex_blocks_before_order_and_pending_state(self):
        bot = make_bot()
        bot.client.get_futures_open_positions.return_value = [{"symbol": "SOLUSDT", "positionAmt": "1"}]
        with self.assertRaises(RuntimeError):
            bot._submit_order("ETHUSDT", "BUY", 0.008, 2500.0, "KRONOS", position_side="LONG")
        bot.client.place_futures_order.assert_not_called()
        self.assertEqual(bot.pending_order, {})
        bot.client.get_futures_open_positions.side_effect = TimeoutError("API timeout")
        with self.assertRaises(TimeoutError):
            bot._submit_order("ETHUSDT", "BUY", 0.008, 2500.0, "KRONOS", position_side="LONG")
        bot.client.place_futures_order.assert_not_called()

    def test_entry_notional_cap_blocks_manual_oversize(self):
        bot = make_bot()
        with self.assertRaisesRegex(RuntimeError, "exceeds 20 USDT"):
            bot._submit_order("ETHUSDT", "BUY", 0.009, 2500.0, "MANUAL", position_side="LONG")
        bot.client.place_futures_order.assert_not_called()
        self.assertEqual(bot.pending_order, {})

    def test_exchange_flat_reconciles_local_position(self):
        bot = make_bot()
        bot.accumulated_qty = 0.008
        bot.db.save_state("stop_client_id_ETHUSDT", "stop_test")
        bot._reconcile_futures_position()
        bot.client.cancel_futures_stop.assert_called_once_with("ETHUSDT", "stop_test")
        bot._reset_position_state.assert_called_once()
        self.assertEqual(bot.db.values["stop_client_id_ETHUSDT"], "")

    def test_exchange_qty_mismatch_halts(self):
        bot = make_bot()
        bot.accumulated_qty = 0.008
        bot.client.get_futures_open_positions.return_value = [{"symbol": "ETHUSDT", "positionAmt": "-0.008"}]
        bot._reconcile_futures_position()
        self.assertFalse(bot.is_running)
        self.assertFalse(bot.enable_buying)
        self.assertEqual(bot.db.values["is_running"], False)

    def test_stop_failure_closes_and_halts_for_review(self):
        bot = make_bot()
        bot.client.place_futures_order.side_effect = [
            {"status": "FILLED", "executedQty": "0.008", "avgPrice": "2501", "cumQuote": "20.008"},
            {"status": "FILLED", "executedQty": "0.008", "avgPrice": "2500"},
        ]
        bot._place_exchange_stop_protection = MagicMock(side_effect=RuntimeError("stop rejected"))
        with self.assertRaisesRegex(RuntimeError, "FAIL_LOUD_STOP_FAILED"):
            bot._submit_order("ETHUSDT", "BUY", 0.008, 2500.0, "KRONOS", position_side="LONG")
        bot._place_exchange_stop_protection.assert_called_once_with("ETHUSDT", "BUY", 0.008, 2501.0)
        self.assertTrue(bot.client.place_futures_order.call_args.kwargs["reduce_only"])
        bot._handle_trade_execution.assert_not_called()
        bot._reset_position_state.assert_called_once()
        self.assertFalse(bot.is_running)
        self.assertTrue(bot.pending_order)

    def test_unconfirmed_emergency_close_retains_pending_review(self):
        bot = make_bot()
        bot.client.place_futures_order.side_effect = [
            {"status": "FILLED", "executedQty": "0.008", "avgPrice": "2501"},
            TimeoutError("emergency close uncertain"),
        ]
        bot._place_exchange_stop_protection = MagicMock(side_effect=RuntimeError("stop rejected"))
        with self.assertRaises(TimeoutError):
            bot._submit_order("ETHUSDT", "BUY", 0.008, 2500.0, "KRONOS", position_side="LONG")
        self.assertFalse(bot.is_running)
        self.assertTrue(bot.pending_order)

    def test_closed_bar_counter_and_intrabar_extremes(self):
        bot = make_bot()
        bot.accumulated_qty = 0.008
        bot.last_closed_bar_time = 100
        bot.bars_held = 0
        bot.highest_price = 2500.0
        bot.lowest_price = 2500.0
        bot.current_price = 2500.0
        bot.history = []
        bot.lock = threading.Lock()
        bot._record_closed_bar(200, 2502.0, 2498.0)
        bot._record_closed_bar(200, 2502.0, 2498.0)
        self.assertEqual(bot.bars_held, 1)
        bot._on_kline_msg({"s": "ETHUSDT", "k": {"c": "2500", "h": "2505", "l": "2495", "x": False}})
        self.assertEqual((bot.highest_price, bot.lowest_price), (2505.0, 2495.0))
        self.assertEqual(bot.db.values["highest_price_ETHUSDT"], 2505.0)

    def test_prefilter_rejects_weak_rvol(self):
        indicators = {"rvol": 1.2, "candle_close_pct": 0.9, "rsi": 60,
                      "adx": 30, "trend_ema": 2400, "fast_ema": 2450,
                      "ema_50": 2450, "donchian_high_36": 2490,
                      "donchian_low_36": 2200, "return_z_score": 0}
        result = KronosQuantStrategy.classify_entry_prefilter(
            indicators, {"current_price": 2500, "macro_lead": {"trend": "NEUTRAL"}}
        )
        self.assertFalse(any(result.values()))
        indicators["rvol"] = 2.0
        self.assertTrue(KronosQuantStrategy.classify_entry_prefilter(
            indicators, {"current_price": 2500, "macro_lead": {"trend": "NEUTRAL"}}
        )["bull_breakout"])

    def test_credentials_purged_and_master_key_migrates_legacy(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.dict(
            "os.environ", {"BINANCE_DB_FERNET_KEY": Fernet.generate_key().decode()}
        ):
            db_path = str(Path(temp_dir) / "bot.db")
            db = DatabaseManager(db_path)
            user_id = db.create_user("sample", "test_api_key", "test_api_secret", True)
            with db._get_connection() as conn:
                conn.execute("INSERT INTO state (user_id, key, value) VALUES (?, 'credentials', 'legacy_plaintext')", (user_id,))
                legacy = Fernet(base64.urlsafe_b64encode(hashlib.sha256(
                    f"{user_id}_encryption_salt".encode()
                ).digest()))
                conn.execute("UPDATE users SET api_key_encrypted = ? WHERE id = ?", (
                    legacy.encrypt(b"test_api_key").decode(), user_id
                ))
            migrated = DatabaseManager(db_path)
            self.assertIsNone(migrated.get_state("credentials", user_id=user_id))
            self.assertEqual(migrated.get_user_by_id(user_id)["api_key"], "test_api_key")
            with self.assertRaises(ValueError):
                migrated.save_state("credentials", {"api_key": "bad"}, user_id=user_id)

    def test_rotating_logger(self):
        handlers = [h for h in _bot_logger.handlers if isinstance(h, RotatingFileHandler)]
        self.assertEqual(len(handlers), 1)
        self.assertEqual((handlers[0].maxBytes, handlers[0].backupCount), (5_000_000, 3))


if __name__ == "__main__":
    unittest.main()
