"""
Multi-Market Quantitative Scanner (`MultiMarketScanner`).

Expands BinanceAgent beyond a single venue by aggregating real-time public signals across:
  1. Binance USDⓈ-M Perpetual Futures (`fapi.binance.com`) — CEX institutional flow & funding
  2. Hyperliquid L1 Perpetual DEX (`api.hyperliquid.xyz/info`) — On-chain perp funding & open interest
     to detect CEX-vs-DEX funding arbitrage spreads and retail crowding divergences
  3. Polymarket CLOB / Gamma (`gamma-api.polymarket.com`) — Implied real-money probabilities on
     crypto & macro catalysts.

All public endpoints are read-only, zero-auth, and fail-safe (timeouts do not block trading).
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import logging
from typing import Any, Callable
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

HYPERLIQUID_INFO_URL = "https://api.hyperliquid.xyz/info"
POLYMARKET_GAMMA_URL = "https://gamma-api.polymarket.com/public-search"


@dataclass(frozen=True)
class CrossVenueArbSignal:
    coin: str                           # e.g., "SOL", "BTC", "ETH"
    binance_symbol: str                 # e.g., "SOLUSDT"
    binance_funding_8h_pct: float       # e.g., +0.0100 (%)
    hyperliquid_funding_8h_pct: float   # normalized to 8h (%)
    funding_spread_8h_pct: float        # binance - hyperliquid (%)
    annualized_carry_apy_pct: float     # |spread| * 3 * 365
    recommended_arb: str                # "SHORT_BINANCE_LONG_HL" | "LONG_BINANCE_SHORT_HL" | "DIRECTIONAL_ONLY"
    directional_bias_bps: float         # Additive bps adjustment for Binance Futures signal

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PolymarketMacroSignal:
    query: str
    event_title: str
    question: str
    yes_prob_pct: float
    no_prob_pct: float
    volume_usd: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _http_post_json(url: str, payload: dict, timeout: float = 4.0) -> Any:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "BinanceAgent-Quant/2.0"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_get_json(url: str, timeout: float = 4.0) -> Any:
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "BinanceAgent-Quant/2.0"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


class MultiMarketScanner:
    """
    Scans CEX (Binance Futures), DEX (Hyperliquid), and Prediction Markets (Polymarket)
    to extract cross-market alpha and funding arbitrage opportunities.
    """

    def __init__(
        self,
        hl_fetcher: Callable[[], Any] | None = None,
        poly_fetcher: Callable[[str], Any] | None = None,
    ):
        self._hl_fetcher = hl_fetcher
        self._poly_fetcher = poly_fetcher

    def fetch_hyperliquid_funding_map(self) -> dict[str, float]:
        """
        Queries Hyperliquid's `metaAndAssetCtxs` endpoint and returns a dict mapping
        coin ticker (e.g. 'SOL', 'BTC') -> normalized 8-hour funding rate in percent (%).
        Note: Hyperliquid settles funding hourly (1/8th of an 8h rate), so we multiply
        the hourly decimal rate by 8 * 100 to get the equivalent 8h percentage rate.
        """
        try:
            raw = (
                self._hl_fetcher()
                if self._hl_fetcher is not None
                else _http_post_json(HYPERLIQUID_INFO_URL, {"type": "metaAndAssetCtxs"})
            )
            if not isinstance(raw, list) or len(raw) < 2:
                return {}
            universe = raw[0].get("universe", [])
            ctxs = raw[1]
            out: dict[str, float] = {}
            for meta, ctx in zip(universe, ctxs):
                name = str(meta.get("name", "")).upper()
                if not name:
                    continue
                raw_rate = ctx.get("funding")
                if raw_rate is None or raw_rate == "":
                    continue
                hourly_rate = float(raw_rate)
                # Convert hourly decimal (e.g. 0.0000125) -> 8h percentage (e.g. 0.01%)
                out[name] = round(hourly_rate * 8.0 * 100.0, 5)
            return out
        except Exception as exc:
            logger.debug("Hyperliquid funding fetch skipped: %s", exc)
            return {}

    def compute_cross_venue_signal(
        self,
        symbol: str,
        binance_funding_decimal: float,
        hl_funding_8h_map: dict[str, float] | None = None,
    ) -> CrossVenueArbSignal:
        """
        Compares Binance USDⓈ-M 8h funding rate against Hyperliquid 8h-equivalent funding rate.
        - If Hyperliquid longs are paying much more than Binance (`hl_funding >> binance_funding`),
          on-chain retail is aggressively long or Binance is lagging -> bullish lead or
          `LONG_BINANCE_SHORT_HL` carry arb.
        - If Binance funding is much higher than Hyperliquid (`binance_funding >> hl_funding`),
          Binance longs are crowded -> `SHORT_BINANCE_LONG_HL` carry arb / bearish squeeze warning.
        """
        sym = symbol.upper()
        coin = sym[:-4] if sym.endswith("USDT") else sym
        bin_pct = round(float(binance_funding_decimal) * 100.0, 5)
        hl_map = hl_funding_8h_map if hl_funding_8h_map is not None else self.fetch_hyperliquid_funding_map()
        hl_pct = float(hl_map.get(coin, bin_pct))

        spread_8h_pct = round(bin_pct - hl_pct, 5)
        apy_pct = round(abs(spread_8h_pct) * 3.0 * 365.0, 2)

        recommended_arb = "DIRECTIONAL_ONLY"
        bias_bps = 0.0
        # Spread >= 0.015% per 8h (~16.4% APY net) triggers cross-venue arb classification
        if spread_8h_pct >= 0.015:
            recommended_arb = "SHORT_BINANCE_LONG_HL"
            # Binance longs over-crowded relative to DEX -> favors SHORT on Binance
            bias_bps = -min(spread_8h_pct * 200.0, 10.0)
        elif spread_8h_pct <= -0.015:
            recommended_arb = "LONG_BINANCE_SHORT_HL"
            # On-chain perps leading higher while Binance funding is still cheap -> favors LONG on Binance
            bias_bps = min(abs(spread_8h_pct) * 200.0, 10.0)

        return CrossVenueArbSignal(
            coin=coin,
            binance_symbol=f"{coin}USDT",
            binance_funding_8h_pct=bin_pct,
            hyperliquid_funding_8h_pct=hl_pct,
            funding_spread_8h_pct=spread_8h_pct,
            annualized_carry_apy_pct=apy_pct,
            recommended_arb=recommended_arb,
            directional_bias_bps=round(bias_bps, 2),
        )

    def fetch_polymarket_crypto_odds(self, query: str = "Bitcoin", limit: int = 3) -> list[PolymarketMacroSignal]:
        """
        Queries Polymarket's public Gamma API to extract real-money implied probabilities
        for crypto/macro events.
        """
        try:
            if self._poly_fetcher is not None:
                data = self._poly_fetcher(query)
            else:
                encoded = urllib.parse.quote(query)
                url = f"{POLYMARKET_GAMMA_URL}?q={encoded}&limit_per_type={int(limit)}"
                data = _http_get_json(url)

            events = data.get("events", []) if isinstance(data, dict) else []
            signals: list[PolymarketMacroSignal] = []
            for ev in events:
                title = str(ev.get("title", ""))
                for mkt in ev.get("markets", []) or []:
                    raw_prices = mkt.get("outcomePrices", "[]")
                    prices = json.loads(raw_prices) if isinstance(raw_prices, str) else raw_prices
                    if not prices or len(prices) < 2:
                        continue
                    yes_p = round(float(prices[0]) * 100.0, 2)
                    no_p = round(float(prices[1]) * 100.0, 2)
                    vol = float(mkt.get("volumeNum", mkt.get("volume", 0.0)) or 0.0)
                    signals.append(
                        PolymarketMacroSignal(
                            query=query,
                            event_title=title,
                            question=str(mkt.get("question", title)),
                            yes_prob_pct=yes_p,
                            no_prob_pct=no_p,
                            volume_usd=round(vol, 2),
                        )
                    )
                    if len(signals) >= limit:
                        return signals
            return signals
        except Exception as exc:
            logger.debug("Polymarket query skipped (%s): %s", query, exc)
            return []
