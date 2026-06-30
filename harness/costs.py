"""Cost model: fees + slippage. Pure functions, explicit math.

FEES (Binance spot, taker, MARKET orders):
    fee per side = notional * fee_pct/100
    Default base: 0.10%/side  -> round-trip 0.20%
    (BNB tier 0.075%/side -> 0.15% round-trip; not used by default per decision.)

SLIPPAGE (modeled, NOT measured -- no order book history available):
    slip per side (bps) = base_bps[symbol_class] + impact
    impact = k * (notional / liquidity_ref)   # ~0 at 12 USDT on liquid pairs
    Applied as adverse price move: buys fill higher, sells fill lower.

    base profile     | majors (BTC/ETH/SOL/BNB) | alts (XRP/ADA/AVAX/LINK)
    -----------------|--------------------------|------------------------
    base (per side)  | 2 bps                    | 5 bps
    stress (x2)      | 4 bps                    | 10 bps
"""
from __future__ import annotations

from dataclasses import dataclass

MAJORS = {"BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"}


@dataclass(frozen=True)
class CostModel:
    fee_pct: float = 0.10            # per side, percent
    slip_majors_bps: float = 2.0     # per side, basis points
    slip_alts_bps: float = 5.0
    impact_k: float = 0.0            # linear size impact coeff (bps per unit ratio)
    liquidity_ref: float = 50_000.0  # USDT notional reference for impact

    @staticmethod
    def base() -> "CostModel":
        return CostModel(0.10, 2.0, 5.0)

    @staticmethod
    def stress() -> "CostModel":
        return CostModel(0.10, 4.0, 10.0)

    def slip_bps(self, symbol: str, notional: float) -> float:
        base = self.slip_majors_bps if symbol in MAJORS else self.slip_alts_bps
        impact = self.impact_k * (notional / self.liquidity_ref) if self.liquidity_ref > 0 else 0.0
        return base + impact

    def fee(self, notional: float) -> float:
        return notional * self.fee_pct / 100.0

    def fill_price(self, symbol: str, mid_price: float, side: str, notional: float) -> float:
        """Adverse slippage: buy fills above, sell fills below mid."""
        s = self.slip_bps(symbol, notional) / 10_000.0
        if side == "BUY":
            return mid_price * (1.0 + s)
        return mid_price * (1.0 - s)
