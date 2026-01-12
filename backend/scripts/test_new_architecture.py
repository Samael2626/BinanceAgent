from backend.services.order_manager import OrderManager
from backend.binance_wrapper import BinanceWrapper
from backend.services.market_data import MarketDataService
from backend.core.engine import TradingEngine
from backend.utils.logger import logger
import sys
import os
import time

# Add root to load path
sys.path.append(os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../..')))


def test_architecture():
    logger.info("🧪 Starting Architecture Smoke Test...")

    try:
        # 1. Test Logger
        logger.debug("Logger debug test")

        # 2. Test Engine Instantiation
        engine = TradingEngine(user_id=123)
        assert engine.user_id == 123
        logger.info("✅ TradingEngine instantiated")

        # 3. Test Singleton Property
        engine2 = TradingEngine(user_id=999)  # Should return same instance
        assert engine2.user_id == 123
        logger.info("✅ TradingEngine Singleton Verified")

        # 4. Test MarketDataService Instantiation
        class MockWrapper:
            client = None
            def adjust_to_min_notional(self, s, q, p): return True

            def place_order(self, s, side, q, order_type='MARKET',
                            quote_order_qty=None): return {'orderId': 1}

        mock_wrapper = MockWrapper()
        service = MarketDataService(wrapper=mock_wrapper)
        assert service.price_cache == {}
        logger.info("✅ MarketDataService instantiated")

        # 5. Test OrderManager
        om = OrderManager(wrapper=mock_wrapper)
        assert om.get_position("BTCUSDT") is None
        logger.info("✅ OrderManager instantiated")

        # Test fake buy flow
        om.execute_buy("BTCUSDT", 0.001, 50000)
        assert om.get_position("BTCUSDT")['in_position'] == True
        logger.info("✅ OrderManager Buy Logic Verified")

        om.execute_sell("BTCUSDT", 0.001)
        assert om.get_position("BTCUSDT") is None
        logger.info("✅ OrderManager Sell/Reset Logic Verified")

        logger.info("🏆 ALL SMOKE TESTS PASSED")

    except Exception as e:
        logger.error(f"❌ Test Failed: {e}")
        # traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    test_architecture()
