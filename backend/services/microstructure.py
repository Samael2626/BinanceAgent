"""
Perpetual Futures & Spot Microstructure Analyzer.

Computes real-time market microstructure signals that complement Kronos K-line
forecasts:
  1. Order Book Imbalance (OBI L1 and L5):
       OBI = (sum(V_bid) - sum(V_ask)) / (sum(V_bid) + sum(V_ask)) in [-1, +1]
  2. Price + Open Interest (OI) Regime:
       - LONG_BUILDUP      (price_change > 0, oi_change > 0) -> Bullish institutional flow
       - SHORT_BUILDUP     (price_change < 0, oi_change > 0) -> Bearish institutional flow
       - SHORT_COVERING    (price_change > 0, oi_change < 0) -> Squeeze / weak continuation
       - LONG_LIQUIDATION  (price_change < 0, oi_change < 0) -> Flush / capitulation
  3. Funding Rate & Mark-Index Basis Pressure:
       - Penalizes paying high funding against position direction
       - Identifies crowded-long / crowded-short squeeze setups
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, asdict
import threading
import time
from typing import Any


@dataclass(frozen=True)
class ForceOrderEvent:
    symbol: str
    side: str          # "BUY" (forced close of SHORT) or "SELL" (forced close of LONG)
    price: float
    qty: float
    notional_usdt: float
    timestamp_ms: int


class ForceOrderWindowTracker:
    """
    Ultra-lightweight circular RAM buffer (`collections.deque(maxlen=2000)`)
    that tracks Binance Futures `!forceOrder@arr` forced-close events over a
    rolling 5-minute (`300s`) window. Zero disk I/O, < 10 MB RAM.
    """

    def __init__(self, maxlen: int = 2000, default_window_sec: int = 300):
        self.maxlen = max(100, int(maxlen))
        self.default_window_sec = max(10, int(default_window_sec))
        self._events: deque[ForceOrderEvent] = deque(maxlen=self.maxlen)
        self._lock = threading.RLock()

    def _purge_expired(self, now_ms: int, window_sec: int) -> None:
        cutoff_ms = now_ms - int(window_sec * 1000)
        while self._events and self._events[0].timestamp_ms < cutoff_ms:
            self._events.popleft()

    def record_raw_ws_message(self, msg: dict[str, Any], now_ms: int | None = None) -> ForceOrderEvent | None:
        """
        Parses a raw `!forceOrder@arr` payload (`{"e": "forceOrder", "o": {...}}` or direct `o` dict)
        and appends it to the circular RAM buffer.
        """
        if not isinstance(msg, dict):
            return None
        order = msg.get("o") if isinstance(msg.get("o"), dict) else msg
        symbol = str(order.get("s", "") or "").upper()
        side = str(order.get("S", "") or "").upper()
        if not symbol or side not in {"BUY", "SELL"}:
            return None
        try:
            price = float(order.get("ap") or order.get("p") or 0.0)
            qty = float(order.get("q") or order.get("l") or 0.0)
            ts_ms = int(order.get("T") or msg.get("E") or now_ms or int(time.time() * 1000))
        except (ValueError, TypeError):
            return None
        if price <= 0 or qty <= 0:
            return None
        return self.record_event(symbol, side, price, qty, ts_ms)

    def record_event(
        self,
        symbol: str,
        side: str,
        price: float,
        qty: float,
        timestamp_ms: int | None = None,
    ) -> ForceOrderEvent:
        now_ms = int(timestamp_ms if timestamp_ms is not None else time.time() * 1000)
        ev = ForceOrderEvent(
            symbol=symbol.upper(),
            side=side.upper(),
            price=float(price),
            qty=float(qty),
            notional_usdt=round(float(price) * float(qty), 4),
            timestamp_ms=now_ms,
        )
        with self._lock:
            self._purge_expired(now_ms, self.default_window_sec)
            self._events.append(ev)
        return ev

    def get_window_stats(
        self,
        symbol: str,
        window_sec: int | None = None,
        now_ms: int | None = None,
    ) -> dict[str, float]:
        """
        Returns 5-minute forced-close volume breakdown for `symbol`:
          - `long_forced_close_usdt`: SELL force orders (longs forced to sell)
          - `short_forced_close_usdt`: BUY force orders (shorts forced to buy)
          - `imbalance`: (short_closed - long_closed) / total in [-1, +1]
        """
        win_sec = int(window_sec or self.default_window_sec)
        ref_ms = int(now_ms if now_ms is not None else time.time() * 1000)
        cutoff_ms = ref_ms - win_sec * 1000
        sym = symbol.upper()

        long_closed_usdt = 0.0
        short_closed_usdt = 0.0
        count = 0

        with self._lock:
            self._purge_expired(ref_ms, max(win_sec, self.default_window_sec))
            for ev in self._events:
                if ev.timestamp_ms < cutoff_ms or ev.symbol != sym:
                    continue
                count += 1
                if ev.side == "SELL":
                    long_closed_usdt += ev.notional_usdt
                elif ev.side == "BUY":
                    short_closed_usdt += ev.notional_usdt

        total = long_closed_usdt + short_closed_usdt
        imbalance = (short_closed_usdt - long_closed_usdt) / total if total > 0 else 0.0
        return {
            "long_forced_close_usdt": round(long_closed_usdt, 2),
            "short_forced_close_usdt": round(short_closed_usdt, 2),
            "total_forced_close_usdt": round(total, 2),
            "forced_close_imbalance": round(imbalance, 4),
            "event_count": float(count),
        }


@dataclass(frozen=True)
class MicrostructureSnapshot:
    symbol: str
    obi_l1: float
    obi_l5: float
    spread_bps: float
    funding_rate_pct: float      # e.g., +0.01 means +0.01% per 8h
    basis_bps: float             # (mark_price - index_price) / index_price * 10000
    oi_change_pct: float
    price_change_pct: float
    oi_regime: str               # LONG_BUILDUP | SHORT_BUILDUP | SHORT_COVERING | LONG_LIQUIDATION | NEUTRAL
    long_edge_bps_adj: float     # Additive adjustment (bps) for LONG expected value
    short_edge_bps_adj: float    # Additive adjustment (bps) for SHORT expected value
    long_forced_close_usdt: float = 0.0
    short_forced_close_usdt: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_order_book_imbalance(book: dict | None, levels: int = 5) -> tuple[float, float, float]:
    """
    Returns (obi_l1, obi_lN, spread_bps) from a Binance order book dict
    with 'bids' and 'asks' as [[price_str, qty_str], ...].
    """
    if not book:
        return 0.0, 0.0, 0.0
    bids = book.get("bids") or []
    asks = book.get("asks") or []
    if not bids or not asks:
        return 0.0, 0.0, 0.0

    try:
        best_bid_p, best_bid_q = float(bids[0][0]), float(bids[0][1])
        best_ask_p, best_ask_q = float(asks[0][0]), float(asks[0][1])
    except (ValueError, TypeError, IndexError):
        return 0.0, 0.0, 0.0

    mid = (best_bid_p + best_ask_p) / 2.0
    spread_bps = ((best_ask_p - best_bid_p) / mid) * 10000.0 if mid > 0 and best_ask_p >= best_bid_p else 0.0

    denom_l1 = best_bid_q + best_ask_q
    obi_l1 = (best_bid_q - best_ask_q) / denom_l1 if denom_l1 > 0 else 0.0

    n = max(1, int(levels))
    bid_vol = 0.0
    ask_vol = 0.0
    for row in bids[:n]:
        bid_vol += max(float(row[1]), 0.0)
    for row in asks[:n]:
        ask_vol += max(float(row[1]), 0.0)

    denom_ln = bid_vol + ask_vol
    obi_ln = (bid_vol - ask_vol) / denom_ln if denom_ln > 0 else 0.0

    return round(obi_l1, 4), round(obi_ln, 4), round(spread_bps, 2)


def classify_oi_regime(
    price_change_pct: float,
    oi_change_pct: float,
    min_price_move_pct: float = 0.15,
    min_oi_move_pct: float = 0.30,
) -> str:
    if abs(price_change_pct) < min_price_move_pct or abs(oi_change_pct) < min_oi_move_pct:
        return "NEUTRAL"
    if price_change_pct > 0 and oi_change_pct > 0:
        return "LONG_BUILDUP"
    if price_change_pct < 0 and oi_change_pct > 0:
        return "SHORT_BUILDUP"
    if price_change_pct > 0 and oi_change_pct < 0:
        return "SHORT_COVERING"
    return "LONG_LIQUIDATION"


class MicrostructureAnalyzer:
    """
    Evaluates L2 Order Book, Funding Rate, Basis, and Open Interest flow to
    adjust directional expected value (in basis points).
    """

    def analyze(
        self,
        symbol: str,
        *,
        book: dict | None = None,
        funding_rate: float = 0.0,       # Decimal rate from fapi (e.g. 0.0001 = 0.01%)
        mark_price: float = 0.0,
        index_price: float = 0.0,
        oi_change_pct: float = 0.0,
        price_change_pct: float = 0.0,
        long_forced_close_usdt: float = 0.0,
        short_forced_close_usdt: float = 0.0,
    ) -> MicrostructureSnapshot:
        obi_l1, obi_l5, spread_bps = compute_order_book_imbalance(book, levels=5)
        funding_rate_pct = float(funding_rate) * 100.0  # Convert 0.0001 -> 0.01%
        basis_bps = (
            ((mark_price - index_price) / index_price) * 10000.0
            if mark_price > 0 and index_price > 0
            else 0.0
        )

        oi_regime = classify_oi_regime(price_change_pct, oi_change_pct)

        long_adj = 0.0
        short_adj = 0.0

        # 1. Order Book Imbalance contribution (up to +/- 6 bps)
        blended_obi = 0.4 * obi_l1 + 0.6 * obi_l5
        long_adj += blended_obi * 6.0
        short_adj -= blended_obi * 6.0

        # 2. Open Interest + Price regime contribution
        if oi_regime == "LONG_BUILDUP":
            long_adj += 5.0
            short_adj -= 4.0
        elif oi_regime == "SHORT_BUILDUP":
            short_adj += 5.0
            long_adj -= 4.0
        elif oi_regime == "SHORT_COVERING":
            # Rally driven by shorts closing rather than fresh longs -> weaker continuation
            long_adj += 1.0
        elif oi_regime == "LONG_LIQUIDATION":
            short_adj += 1.0

        # 3. Funding rate carry & squeeze risk (funding_rate_pct in %, e.g. 0.01% = 1 bps)
        funding_bps = funding_rate_pct * 100.0
        # Holding across a funding interval costs/pays funding_bps; extreme funding signals crowding
        if funding_rate_pct > 0.03:
            # Crowded longs (> +0.03% / 8h): penalize LONG, reward SHORT squeeze/carry
            long_adj -= min(funding_bps * 1.5, 15.0)
            short_adj += min(funding_bps * 1.2, 12.0)
        elif funding_rate_pct < -0.03:
            # Crowded shorts (< -0.03% / 8h): penalize SHORT, reward LONG squeeze/carry
            short_adj -= min(abs(funding_bps) * 1.5, 15.0)
            long_adj += min(abs(funding_bps) * 1.2, 12.0)
        else:
            # Mild carry adjustment (half an 8h funding interval expected holding time)
            long_adj -= funding_bps * 0.5
            short_adj += funding_bps * 0.5

        # 4. Real-time Forced-Close Flow (`!forceOrder@arr`) absorption edge (up to +/- 8 bps)
        l_fc = max(0.0, float(long_forced_close_usdt))
        s_fc = max(0.0, float(short_forced_close_usdt))
        if l_fc >= 25_000.0 and blended_obi >= 0.08:
            # Heavy forced long selling absorbed by bid-heavy L2 book -> exhaustion reversal LONG edge
            exhaustion_bonus = min(8.0, (l_fc / 25_000.0) * 2.5)
            long_adj += exhaustion_bonus
            short_adj -= exhaustion_bonus * 0.5
        if s_fc >= 25_000.0 and blended_obi <= -0.08:
            # Heavy forced short buying absorbed by ask-heavy L2 book -> exhaustion reversal SHORT edge
            exhaustion_bonus = min(8.0, (s_fc / 25_000.0) * 2.5)
            short_adj += exhaustion_bonus
            long_adj -= exhaustion_bonus * 0.5

        return MicrostructureSnapshot(
            symbol=symbol.upper(),
            obi_l1=obi_l1,
            obi_l5=obi_l5,
            spread_bps=spread_bps,
            funding_rate_pct=round(funding_rate_pct, 5),
            basis_bps=round(basis_bps, 2),
            oi_change_pct=round(float(oi_change_pct), 3),
            price_change_pct=round(float(price_change_pct), 3),
            oi_regime=oi_regime,
            long_edge_bps_adj=round(long_adj, 2),
            short_edge_bps_adj=round(short_adj, 2),
            long_forced_close_usdt=round(l_fc, 2),
            short_forced_close_usdt=round(s_fc, 2),
        )


def compute_order_flow_imbalance(
    prev_book: dict | None,
    curr_book: dict | None,
) -> float:
    """
    Computes Cont-Kukanov-Stoikov (2014) Order Flow Imbalance (OFI).
    Measures net changes in queue sizes at best bid/ask and top levels.
    Returns normalized OFI in [-1.0, +1.0].
    """
    if not prev_book or not curr_book:
        return 0.0

    p_bids = prev_book.get("bids") or []
    p_asks = prev_book.get("asks") or []
    c_bids = curr_book.get("bids") or []
    c_asks = curr_book.get("asks") or []

    if not p_bids or not p_asks or not c_bids or not c_asks:
        return 0.0

    try:
        p_bid_p, p_bid_q = float(p_bids[0][0]), float(p_bids[0][1])
        p_ask_p, p_ask_q = float(p_asks[0][0]), float(p_asks[0][1])
        c_bid_p, c_bid_q = float(c_bids[0][0]), float(c_bids[0][1])
        c_ask_p, c_ask_q = float(c_asks[0][0]), float(c_asks[0][1])
    except (ValueError, TypeError, IndexError):
        return 0.0

    if c_bid_p > p_bid_p:
        delta_bid = c_bid_q
    elif c_bid_p == p_bid_p:
        delta_bid = c_bid_q - p_bid_q
    else:
        delta_bid = -p_bid_q

    if c_ask_p < p_ask_p:
        delta_ask = c_ask_q
    elif c_ask_p == p_ask_p:
        delta_ask = c_ask_q - p_ask_q
    else:
        delta_ask = -p_ask_q

    raw_ofi = delta_bid - delta_ask
    norm_denom = max(c_bid_q + c_ask_q, 1e-6)
    return max(-1.0, min(1.0, raw_ofi / norm_denom))


@dataclass(frozen=True)
class LeadLagSnapshot:
    anchor_symbol: str          # Usually "BTCUSDT"
    trend: str                  # "BULLISH" | "BEARISH" | "NEUTRAL"
    return_1h_pct: float
    bias_bps: float             # Positive = bullish anchor push, Negative = bearish anchor drag
    confluence_score: float     # 0.0 to 1.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LeadLagAnalyzer:
    """
    Tracks Bitcoin (BTCUSDT) macro directional momentum as the anchor asset
    to guide altcoin execution decisions and eliminate false breakouts.
    """

    def __init__(self, anchor_symbol: str = "BTCUSDT"):
        self.anchor_symbol = anchor_symbol.upper()

    def evaluate(
        self,
        btc_current_price: float,
        btc_ema_fast: float,
        btc_ema_trend: float,
        btc_return_1h_pct: float = 0.0,
    ) -> LeadLagSnapshot:
        if btc_current_price <= 0:
            return LeadLagSnapshot(
                anchor_symbol=self.anchor_symbol,
                trend="NEUTRAL",
                return_1h_pct=0.0,
                bias_bps=0.0,
                confluence_score=0.5,
            )

        is_bullish = (
            btc_current_price >= btc_ema_trend
            and btc_ema_fast >= btc_ema_trend
            and btc_return_1h_pct >= -0.25
        )
        is_bearish = (
            btc_current_price <= btc_ema_trend
            and btc_ema_fast <= btc_ema_trend
            and btc_return_1h_pct <= 0.25
        )

        trend = "BULLISH" if is_bullish else ("BEARISH" if is_bearish else "NEUTRAL")

        bias_bps = 0.0
        if trend == "BULLISH":
            bias_bps = min(18.0, max(6.0, btc_return_1h_pct * 8.0 + 8.0))
        elif trend == "BEARISH":
            bias_bps = max(-18.0, min(-6.0, btc_return_1h_pct * 8.0 - 8.0))

        confluence_score = 0.5 + (bias_bps / 36.0)

        return LeadLagSnapshot(
            anchor_symbol=self.anchor_symbol,
            trend=trend,
            return_1h_pct=round(btc_return_1h_pct, 3),
            bias_bps=round(bias_bps, 2),
            confluence_score=round(confluence_score, 3),
        )
