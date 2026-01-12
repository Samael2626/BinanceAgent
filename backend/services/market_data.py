"""
Market Data Service Module.
Handles all market data ingestion, storage, and retrieval with smart caching.
"""
import logging
import time
from typing import Dict, List

import pandas as pd

from backend.binance_wrapper import BinanceWrapper

logger = logging.getLogger(__name__)


class MarketDataService:
    """
    The Eyes of the System.
    Handles all market data ingestion, storage, and retrieval.
    Implements Smart Caching to satisfy 'Velocidad Extrema' requirement.
    """

    def __init__(self, wrapper: BinanceWrapper):
        self.wrapper = wrapper
        self.price_cache: Dict[str, float] = {}
        self.last_price_update: Dict[str, float] = {}
        self.klines_cache: Dict[str, pd.DataFrame] = {}
        self.cache_ttl = 0.5  # 500ms cache validity for prices

    def get_current_price(self, symbol: str) -> float:
        """
        Returns the current price with low-latency caching.
        """
        now = time.time()

        # Check Cache
        if symbol in self.price_cache:
            if now - self.last_price_update.get(symbol, 0) < self.cache_ttl:
                return self.price_cache[symbol]

        # Fetch fresh if cache expired (Fallback to REST if socket lagging)
        try:
            price = float(self.wrapper.client.get_symbol_ticker(
                symbol=symbol)['price'])

            self.price_cache[symbol] = price
            self.last_price_update[symbol] = now
            return price
        except Exception as ex:
            logger.error("Error fetching price for %s: %s", symbol, ex)
            return self.price_cache.get(symbol, 0.0)

    def update_price_stream(self, msg):
        """Callback for WebSocket price updates."""
        try:
            symbol = msg['s']
            # 'c' is usually close price in mini-ticker
            price = float(msg['c'])
            self.price_cache[symbol] = price
            self.last_price_update[symbol] = time.time()
        except (KeyError, ValueError, TypeError):
            # Silent fail for speed in stream
            pass

    def get_historical_data(self, symbol: str, interval: str, limit: int = 100) -> pd.DataFrame:
        """
        Fetches or returns cached historical kline data.
        """
        # We could implement DataFrame caching here too
        # For now, direct fetch with error handling
        try:
            return self.wrapper.get_historical_klines(symbol, interval, limit)
        except Exception as ex:
            logger.error("Failed to get klines for %s: %s", symbol, ex)
            return pd.DataFrame()

    def start_data_stream(self, symbols: List[str]):
        """Starts WebSocket streams for list of symbols."""
        logger.info("Starting data stream for %d symbols...", len(symbols))
        # Implementation would use wrapper.start_ticker_socket or similar
        # TODO: Implement WebSocket stream initialization
