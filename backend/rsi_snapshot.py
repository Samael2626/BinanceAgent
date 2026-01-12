"""
RSI Snapshot Module
Calculates RSI for multiple trading pairs with caching for performance optimization.
Uses pandas_ta for consistency with bot core indicators.
"""
import time
from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd
import pandas_ta as ta


class RSISnapshotCache:
    """Simple cache to avoid recalculating RSI on every request."""

    def __init__(self, ttl_seconds: int = 10):
        self.cache: Dict[str, Dict] = {}
        self.ttl = ttl_seconds

    def get(self, key: str) -> Optional[Dict]:
        """Get cached value if not expired."""
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry['timestamp'] < self.ttl:
                return entry['data']
        return None

    def set(self, key: str, data: Dict):
        """Store value with timestamp."""
        self.cache[key] = {
            'data': data,
            'timestamp': time.time()
        }


# Global cache instance
_rsi_cache = RSISnapshotCache(ttl_seconds=10)


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> Optional[float]:
    """
    Calculate RSI indicator using pandas_ta (same method as bot core).

    Args:
        df: DataFrame with OHLCV data
        period: RSI period (default 14)

    Returns:
        RSI value or None if calculation fails
    """
    try:
        if df is None or df.empty or len(df) < period + 1:
            return None

        # Use pandas_ta for consistency with bot's main indicators
        rsi_series = df.ta.rsi(length=period)

        if rsi_series is None or rsi_series.empty:
            return None

        # Return last value
        last_rsi = float(rsi_series.iloc[-1])
        return last_rsi if not pd.isna(last_rsi) else None
    except Exception as e:
        print(f"Error calculating RSI: {e}")
        return None


def calculate_rsi_snapshot(symbols: List[str], client, timeframe: str = "1m") -> List[Dict[str, any]]:
    """
    Calculate RSI for multiple symbols.

    Args:
        symbols: List of trading pairs (e.g., ['BTCUSDT', 'SOLUSDT'])
        client: BinanceWrapper instance
        timeframe: Timeframe for RSI calculation (default '1m')

    Returns:
        List of dicts with 'symbol' and 'rsi' keys
    """
    results = []

    for symbol in symbols:
        try:
            # Check cache first
            cache_key = f"{symbol}_{timeframe}"
            cached = _rsi_cache.get(cache_key)

            if cached is not None:
                results.append(cached)
                continue

            # Fetch data and calculate RSI (using same limit as bot: 1000)
            df = client.get_historical_klines(symbol, timeframe, limit=1000)

            if df is None or df.empty:
                print(f"[RSI Snapshot] No data for {symbol}")
                continue

            rsi_value = calculate_rsi(df)

            if rsi_value is not None:
                snapshot = {
                    "symbol": symbol,
                    "rsi": round(rsi_value, 1)
                }
                results.append(snapshot)
                _rsi_cache.set(cache_key, snapshot)
                print(f"[RSI Snapshot] {symbol}: RSI={rsi_value:.1f}")
            else:
                print(f"[RSI Snapshot] Failed to calculate RSI for {symbol}")

        except Exception as e:
            print(f"[RSI Snapshot] Error processing {symbol}: {e}")
            continue

    return results


def get_default_symbols() -> List[str]:
    """Returns default list of symbols to monitor."""
    return [
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT",
        "BNBUSDT",
        "ADAUSDT",
        "XRPUSDT",
        "DOGEUSDT",
        "MATICUSDT"
    ]
