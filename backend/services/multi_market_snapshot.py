"""Snapshot publico de funding y eventos para el panel PAPER Futuros."""
from datetime import datetime, timezone
from threading import Lock
import math
import time

from .multi_market_scanner import MultiMarketScanner, _http_get_json

SYMBOLS = ("SOLUSDT", "XRPUSDT", "ADAUSDT", "LINKUSDT", "AVAXUSDT", "BNBUSDT")


def _binance_funding(symbol):
    data = _http_get_json(f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol}")
    return data.get("lastFundingRate")


class MultiMarketSnapshot:
    def __init__(self, scanner=None, binance_fetcher=None, clock=None):
        self.scanner = scanner or MultiMarketScanner()
        self.binance_fetcher = binance_fetcher or _binance_funding
        self.clock = clock or time.monotonic
        self.lock = Lock()
        self.cached = None
        self.expires_at = 0

    def get(self):
        with self.lock:
            if self.cached is not None and self.clock() < self.expires_at:
                return self.cached
            result = self._scan()
            self.cached = result
            self.expires_at = self.clock() + 60
            return result

    def _scan(self):
        try:
            hl_map = self.scanner.fetch_hyperliquid_funding_map()
        except Exception:
            hl_map = {}
        funding = []
        for symbol in SYMBOLS:
            binance_pct = None
            try:
                raw = self.binance_fetcher(symbol)
                if raw is not None and math.isfinite(float(raw)):
                    binance_pct = round(float(raw) * 100, 5)
            except Exception:
                pass
            hl_pct = hl_map.get(symbol.removesuffix("USDT"))
            try:
                hl_pct = float(hl_pct) if hl_pct is not None and math.isfinite(float(hl_pct)) else None
            except (TypeError, ValueError, OverflowError):
                hl_pct = None
            available = binance_pct is not None and hl_pct is not None
            spread = round(binance_pct - hl_pct, 5) if available else None
            funding.append({
                "symbol": symbol,
                "binance_8h_pct": binance_pct,
                "hyperliquid_8h_pct": hl_pct,
                "spread_8h_pct": spread,
                "annualized_gross_indicative_pct": round(abs(spread) * 3 * 365, 2) if available else None,
                "status": "available" if available else "partial" if binance_pct is not None or hl_pct is not None else "unavailable",
            })
        events = []
        successful_queries = 0
        for query in ("Bitcoin", "Ethereum"):
            try:
                found = self.scanner.fetch_polymarket_crypto_odds(query)
                valid = [item.to_dict() for item in found if item.question and 0 <= item.yes_prob_pct <= 100 and 0 <= item.no_prob_pct <= 100]
                events.extend(valid)
                if valid:
                    successful_queries += 1
            except Exception:
                pass
        poly_status = "available" if successful_queries == 2 else "partial" if events else "unavailable"
        return {"queried_at": datetime.now(timezone.utc).isoformat(), "funding": funding,
                "polymarket": {"status": poly_status, "events": events}}
