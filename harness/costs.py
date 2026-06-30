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

MAKER COST MODEL (MakerCostModel):
    Entry via LIMIT order. Fee = same 0.10%/side (Binance VIP0: maker == taker).
    NOTE: There is NO fee advantage for maker at VIP0. The benefit is avoiding
    spread crossing (0 slippage on entry, vs 2-5 bps taker slippage).

    SUPUESTO: maker_slip_entry_bps = 0.0 (base) or 1.0 (stress).
        Rationale base: limit order posts at OUR price => 0 adverse slippage.
        Rationale stress: partial fills or price improvement of 1 bps (still favorable
        vs 2-5 bps taker, but conservatively non-zero).

    SL exit: MARKET/taker (realistic -- SL fires on bar cross, not placeable as limit).
        Slippage: same taker adversity as CostModel.
    TP exit: LIMIT/maker => 0 slip (base) or 1 bps (stress) at TP price.

    NO-FILL RISK: modeled via expiry_bars (N). If LOW of no bar within N subsequent
    bars touches the limit price, the order expires unfilled. That bar and its
    potential profit are NOT captured. This is the critical honesty constraint.
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


@dataclass(frozen=True)
class MakerCostModel:
    """Cost model for limit-entry (maker) + market-SL / limit-TP exit variant.

    Parameters
    ----------
    fee_pct : float
        Fee per side in percent. VIP0 Binance spot: 0.10% maker == taker.
        SUPUESTO: no BNB discount applied.
    entry_slip_bps : float
        Slippage on maker entry. Base = 0 (we post the price), Stress = 1 bps
        (conservative: tick rounding / partial fill at slightly worse price).
    sl_slip_bps_majors / sl_slip_bps_alts : float
        Slippage on SL (market / taker). Same as CostModel taker slippage.
        Base: 2/5 bps. Stress: 4/10 bps.
    tp_slip_bps : float
        Slippage on TP (limit / maker). Base = 0, Stress = 1 bps.
    limit_offset_bps : float
        SUPUESTO: how far below the signal close we post the limit buy.
        We post at close * (1 - limit_offset_bps/10000). This gives us
        a better fill price (favorable) but increases no-fill probability.
        Base = 5 bps (conservative: small discount, higher fill rate).
        Stress = 10 bps (larger discount => worse fill rate but better price).
    expiry_bars : int
        SUPUESTO: limit order expires after this many bars without fill.
        Base = 3 bars. With 1h bars this is 3 hours to fill.
        Stress = 2 bars (stricter: if not filled in 2h, cancel).
        Rationale: avoids chasing a move that already ran without us.
    """
    fee_pct: float = 0.10
    entry_slip_bps: float = 0.0
    sl_slip_bps_majors: float = 2.0
    sl_slip_bps_alts: float = 5.0
    tp_slip_bps: float = 0.0
    limit_offset_bps: float = 5.0
    expiry_bars: int = 3

    @staticmethod
    def base() -> "MakerCostModel":
        """Base: 0 entry slip, taker SL 2/5 bps, 0 TP slip, 5bps offset, 3-bar expiry."""
        return MakerCostModel(
            fee_pct=0.10,
            entry_slip_bps=0.0,
            sl_slip_bps_majors=2.0,
            sl_slip_bps_alts=5.0,
            tp_slip_bps=0.0,
            limit_offset_bps=5.0,
            expiry_bars=3,
        )

    @staticmethod
    def stress() -> "MakerCostModel":
        """Stress: 1bps entry slip, taker SL 4/10 bps, 1bps TP slip, 10bps offset, 2-bar expiry."""
        return MakerCostModel(
            fee_pct=0.10,
            entry_slip_bps=1.0,
            sl_slip_bps_majors=4.0,
            sl_slip_bps_alts=10.0,
            tp_slip_bps=1.0,
            limit_offset_bps=10.0,
            expiry_bars=2,
        )

    def limit_price(self, signal_close: float) -> float:
        """Price at which we post the buy limit order.

        Posted below signal close by limit_offset_bps. Better price than close
        but only fills if a subsequent bar has low <= this price.
        """
        return signal_close * (1.0 - self.limit_offset_bps / 10_000.0)

    def fee(self, notional: float) -> float:
        return notional * self.fee_pct / 100.0

    def entry_fill_price(self, limit_p: float) -> float:
        """Effective fill price on entry. Limit fills at our price +/- entry_slip."""
        # entry_slip_bps is modeled as favorable or neutral (we set the price).
        # Using it as a small adverse adjustment to be conservative.
        return limit_p * (1.0 + self.entry_slip_bps / 10_000.0)

    def sl_fill_price(self, symbol: str, sl_price: float) -> float:
        """SL is MARKET. Fills below sl_price (adverse)."""
        bps = self.sl_slip_bps_majors if symbol in MAJORS else self.sl_slip_bps_alts
        return sl_price * (1.0 - bps / 10_000.0)

    def tp_fill_price(self, tp_price: float) -> float:
        """TP is LIMIT/maker. Fills at tp_price - tp_slip (conservative; often fills exactly)."""
        return tp_price * (1.0 - self.tp_slip_bps / 10_000.0)
