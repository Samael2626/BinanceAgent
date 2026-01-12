from backend.utils.logger import logger
from backend.bot_logic import BinanceBot
import sys
import os
import threading
import time

# Add root to load path
sys.path.append(os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../..')))


def verify_bot_integration():
    logger.info("🤖 Verifying BinanceBot Integration...")

    try:
        # Mocking DatabaseManager internal calls if possible,
        # but BinanceBot uses real DB connection.
        # We assume the environment has access to the DB (sqlite file).

        # Instantiate Bot (User ID 1 is usually valid or safe for test)
        bot = BinanceBot(user_id=1)
        logger.info("✅ BinanceBot Instantiated")

        # Check if MarketDataService is present (initially None)
        assert bot.market_data_service is None
        logger.info("✅ MarketDataService attribute exists")

        # We can't easily test full connection without credentials,
        # ensuring the import works and class structure is valid is the main goal here.

        logger.info("🏆 Bot Integration Logic Verified")

    except Exception as e:
        logger.error(f"❌ Integration Verification Failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    verify_bot_integration()
