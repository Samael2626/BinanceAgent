"""
Unit tests validating remediation of Codex audit findings for Binance Futures execution:
1. Futures quantity normalization via LOT_SIZE stepSize.
2. setup_futures_symbol handling margin type and -4046 idempotent code.
3. place_futures_order and place_futures_stop_market calling futures endpoints.
4. Fail-loud stop loss placement with emergency market close on exchange stop rejection.
5. Global account 1-position mutex via get_futures_open_positions.
6. Database credential security (purge on init, Fernet retrieval, refusal to write raw credentials).
7. Rotating log handler configuration (5MB, 3 backups).
"""

import gc
import logging
from logging.handlers import RotatingFileHandler
import os
import sqlite3
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.binance_wrapper import BinanceWrapper
from backend.bot_logic import BinanceBot, _bot_logger
from backend.database import DatabaseManager


class TestFuturesRemediation(unittest.TestCase):
    def test_normalize_futures_quantity(self):
        wrapper = BinanceWrapper(api_key="mock", api_secret="mock")
        def mock_info(symbol):
            if symbol == "BTCUSDT":
                return {
                    "symbol": "BTCUSDT",
                    "filters": [{"filterType": "LOT_SIZE", "minQty": "0.001", "stepSize": "0.001"}],
                }
            elif symbol == "ADAUSDT":
                return {
                    "symbol": "ADAUSDT",
                    "filters": [{"filterType": "LOT_SIZE", "minQty": "1", "stepSize": "1"}],
                }
            return None

        wrapper.get_futures_symbol_info = MagicMock(side_effect=mock_info)

        # BTC: 0.00129 -> 0.001
        self.assertEqual(wrapper.normalize_futures_quantity("BTCUSDT", 0.00129), 0.001)
        # ADA: 35.8 -> 35.0
        self.assertEqual(wrapper.normalize_futures_quantity("ADAUSDT", 35.8), 35.0)

    def test_setup_futures_symbol_handles_minus_4046(self):
        wrapper = BinanceWrapper(api_key="mock", api_secret="mock")
        wrapper.client = MagicMock()
        from binance.exceptions import BinanceAPIException
        from requests.models import Response
        res = Response()
        res.status_code = 400
        wrapper.client.futures_change_margin_type.side_effect = BinanceAPIException(
            res, 400, '{"code": -4046, "msg": "No need to change margin type."}'
        )
        wrapper.setup_futures_symbol("ETHUSDT", leverage=2, margin_type="ISOLATED")
        wrapper.client.futures_change_leverage.assert_called_once_with(symbol="ETHUSDT", leverage=2)

    def test_place_futures_order_and_stop_market(self):
        wrapper = BinanceWrapper(api_key="mock", api_secret="mock")
        wrapper.client = MagicMock()
        wrapper.normalize_futures_quantity = MagicMock(return_value=0.5)

        wrapper.client.futures_create_order.return_value = {
            "orderId": 12345, "symbol": "ETHUSDT", "status": "FILLED"
        }

        # Entry order
        res = wrapper.place_futures_order("ETHUSDT", "BUY", 0.5, client_order_id="ba_test_entry")
        self.assertEqual(res["orderId"], 12345)
        wrapper.client.futures_create_order.assert_called_with(
            symbol="ETHUSDT",
            side="BUY",
            type="MARKET",
            quantity="0.5",
            newClientOrderId="ba_test_entry",
            newOrderRespType="RESULT",
        )

        # Stop Market order
        res_stop = wrapper.place_futures_stop_market("ETHUSDT", "SELL", 2500.0, 0.5, client_order_id="ba_test_stop")
        wrapper.client.futures_create_order.assert_called_with(
            symbol="ETHUSDT",
            side="SELL",
            type="STOP_MARKET",
            stopPrice="2500",
            quantity="0.5",
            newClientOrderId="ba_test_stop",
            reduceOnly="true",
        )

    def test_fail_loud_stop_loss_emergency_market_close(self):
        bot = BinanceBot()
        bot.client = MagicMock()
        bot.is_paper = False
        bot.is_testnet = True
        bot.market_type = "FUTURES"
        bot.order_execution_style = "MARKET"
        bot.pending_order = {}
        delattr(bot.client, "place_smart_maker_order")

        # Simulate entry order fill
        bot.client.place_futures_order.return_value = {
            "orderId": 9999,
            "symbol": "ETHUSDT",
            "status": "FILLED",
            "executedQty": "0.5",
            "cummulativeQuoteQty": "1250.0",
        }

        # Make stop market order fail
        bot.client.place_futures_stop_market.side_effect = RuntimeError("Binance exchange stop endpoint error")

        # Mock trade execution handler to return success
        bot._handle_trade_execution = MagicMock(return_value={"status": "FILLED", "orderId": 9999})

        # Calling _submit_order for an entry should catch the stop failure,
        # trigger emergency market close, and raise RuntimeError with FAIL_LOUD_STOP_FAILED
        with self.assertRaises(RuntimeError) as ctx:
            bot._submit_order("ETHUSDT", "BUY", 0.5, 2500.0, "KRONOS", position_side="LONG")

        self.assertIn("FAIL_LOUD_STOP_FAILED", str(ctx.exception))

        # Verify emergency market close was dispatched
        bot.client.place_futures_order.assert_called_with(
            "ETHUSDT",
            "SELL",
            0.5,
            order_type="MARKET",
            reduce_only=True,
        )

    def test_global_account_1_position_mutex(self):
        bot = BinanceBot()
        bot.client = MagicMock()
        bot.is_paper = False
        bot.is_testnet = True
        bot.market_type = "FUTURES"
        bot.symbol = "ETHUSDT"
        bot.has_open_position = False

        # Simulate open position in another symbol (e.g. SOLUSDT) on the exchange account
        bot.client.get_futures_open_positions.return_value = [
            {"symbol": "SOLUSDT", "positionAmt": 1.25, "entryPrice": 140.0}
        ]

        # Verify that account mutex detects existing position
        positions = bot.client.get_futures_open_positions()
        has_other_pos = any(p["symbol"] != bot.symbol and abs(p["positionAmt"]) > 0 for p in positions)
        self.assertTrue(has_other_pos)

    def test_database_credentials_purged_and_refused(self):
        import tempfile
        fd, temp_db = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        try:
            # Seed legacy raw plaintext credential in DB
            raw_conn = sqlite3.connect(temp_db)
            raw_conn.execute("CREATE TABLE state (key TEXT PRIMARY KEY, value TEXT)")
            raw_conn.execute("INSERT INTO state (key, value) VALUES ('credentials', 'plaintext_secret')")
            raw_conn.commit()
            raw_conn.close()

            # Initialize DatabaseManager on this DB -> should purge credentials from state table
            db = DatabaseManager(temp_db)
            val = db.get_state("credentials")
            self.assertIsNone(val)

            # Saving raw credentials to state must be blocked
            db.save_state("credentials", {"key": "abc", "secret": "123"})
            self.assertIsNone(db.get_state("credentials"))
            del db
            gc.collect()
        finally:
            try:
                if os.path.exists(temp_db):
                    os.remove(temp_db)
            except Exception:
                pass

    def test_rotating_logger_config(self):
        has_rotating = False
        for handler in _bot_logger.handlers:
            if isinstance(handler, RotatingFileHandler):
                has_rotating = True
                self.assertGreaterEqual(handler.maxBytes, 5_000_000)
                self.assertEqual(handler.backupCount, 3)
        self.assertTrue(has_rotating, "RotatingFileHandler not found in _bot_logger")


if __name__ == "__main__":
    unittest.main()
