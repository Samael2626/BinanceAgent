"""Backtest engine for the maker/1h variant.

Hypothesis under test
---------------------
Strategy: SmartScalper signals on 1h bars, entries via LIMIT order (maker),
SL via MARKET (taker), TP via LIMIT (maker). SL/TP sized from ATR(14) of 1h.

Key differences vs engine.py (5m taker)
-----------------------------------------
1. BAR_MINUTES = 60 (1h bars).
2. Indicators recalculated on 1h data.
3. SL/TP from ATR(14) * multiplier, NOT fixed pct.
4. LIMIT ENTRY MODEL:
   - On signal bar i, post limit_price = close[i] * (1 - offset_bps/10000).
   - Scan bars i+1 .. i+expiry_bars: first bar where low <= limit_price fills.
   - If no fill within expiry_bars -> trade does NOT execute (no-fill).
   - NO-FILL cost: 0 USDT but opportunity cost is real (we missed the bar).
5. SL exit: intrabar low touch, fills at sl_fill_price (market/taker slippage).
6. TP exit: intrabar high touch, fills at tp_fill_price (limit/maker slippage).
7. TRAIL exit: kept from base engine (profit-step trail), exits as taker (market).

SUPUESTOS (legibles por el auditor)
-------------------------------------
A) Limit price posted at close[i] * (1 - offset_bps/10000). Base = 5 bps below,
   Stress = 10 bps below. These are ASSUMPTIONS -- no real orderbook data.
B) Fill condition: low[j] <= limit_price for j in [i+1, i+expiry_bars]. This
   assumes the limit order is in the book and active. In practice there could be
   partial fills or queue position issues. Model assumes full fill at limit_price.
C) Entry slippage = 0 bps base, 1 bps stress. Conservative since we post the price.
D) SL slippage = same as taker model (2/5 bps base, 4/10 bps stress). Realistic
   since SL fires as market order.
E) TP slippage = 0 bps base, 1 bps stress. TP as limit order, favorable.
F) expiry_bars = 3 base (3 hours), 2 stress. ASSUMPTION: real Binance GTC orders
   would stay open longer, so 3 bars is conservative (we cancel early). However,
   if price bounced off our limit and ran without us, 3 bars gives enough time to
   capture a natural pullback.
G) ATR multipliers: SL = 1.5 * ATR_pct, TP = 2.5 * ATR_pct (asymmetric, R:R ~1.67).
   Rationale: 1h ATR(14) on majors is typically 1.5-3% of price. A 1.5x multiplier
   gives SL ~2.25-4.5% -- enough room for noise without being too wide. TP at 2.5x
   gives ~3.75-7.5% -- meaningful move, not rubbish.
   SUPUESTO: these multipliers were chosen BEFORE seeing results. Do not tune to green.
H) ATR floor/ceil: ATR_pct is capped at [0.5%, 8.0%] to avoid degenerate behavior in
   very low-volatility or crash bars. Floor 0.5% ensures minimum SL. Ceil 8% ensures
   we don't hold through catastrophic moves.
I) Trail is kept with trail_pct = 1.0% (vs 0.8% in 5m) on 1h bars. SUPUESTO:
   wider trail to avoid premature exits on 1h noise.
J) Cooldown: 2 bars (2 hours) after exit. Much less aggressive than 5m (1 bar = 5m).
K) Fees: 0.10%/side maker and taker (VIP0 base). NO BNB discount. Fee benefit of
   maker vs taker at VIP0 = 0% (same rate). Edge comes ONLY from no-spread-crossing.
L) This model does NOT have a lateral gate. SUPUESTO: 1h bars are less prone to
   false lateral signals from the 5m fluctuation_factor; the ATR-based SL naturally
   absorbs noise. The auditor should check if adding a lateral/ADX gate changes results.

POTENTIAL OPTIMISM FLAGS (for the auditor)
------------------------------------------
- No-fill model is binary (fill or expire). Real limit orders can partially fill.
  Model is pessimistic on partial fills (all-or-nothing), but optimistic in that it
  assumes the limit is always in the queue (no queue position modeling).
- ATR multipliers could still be IS-tuned if quant re-runs with different values.
  The gate is: multipliers fixed BEFORE quant runs. Quant must not change them after
  seeing OOS results.
- limit_offset_bps gives us a BETTER entry price than close. This is mildly optimistic
  because it improves E/trade vs a taker who buys at market. The stress scenario
  (10 bps deeper) has LOWER fill rate which partly offsets the better price.
- We do not model spread explicitly. On 1h bars with ~12 USDT notional, spread impact
  on majors is ~0.5-1 bps. Included implicitly in entry_slip_bps stress scenario.
"""
from __future__ import annotations

import os
import sys
from typing import Callable

import numpy as np
import pandas as pd
import pandas_ta as ta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.strategies.smart_scalper import SmartScalperStrategy  # noqa: E402
from harness.costs import MakerCostModel  # noqa: E402

BAR_MINUTES = 60   # 1h bars
WARMUP = 250       # same warmup bar count as 5m engine (enough for EMA200 on 1h)

# ATR multipliers -- fixed here, NOT tunable after OOS is seen. (Supuesto G)
ATR_SL_MULT = 1.5   # SL = entry_price * (1 - ATR_pct * ATR_SL_MULT)
ATR_TP_MULT = 2.5   # TP = entry_price * (1 + ATR_pct * ATR_TP_MULT)
ATR_PCT_FLOOR = 0.5 / 100.0   # 0.5% minimum ATR_pct  (Supuesto H)
ATR_PCT_CEIL  = 8.0 / 100.0   # 8.0% maximum ATR_pct  (Supuesto H)
TRAIL_PCT_1H  = 1.0            # % trailing stop on 1h (Supuesto I)

DEFAULT_SETTINGS_1H = {
    "buy_rsi": 38.0, "sell_rsi": 70.0, "smart_scalper_entry_score": 52.0,
    # SL/TP pct are IGNORED in maker engine -- ATR multipliers above are used instead.
    # Kept for score_buy_setup compatibility (it doesn't use them).
    "stop_loss_pct": 0.0, "take_profit_pct": 0.0,
    "cooldown_minutes": 120,   # 2 bars @ 1h (Supuesto J)
    "enable_trend_filter": False, "enable_fast_ema": False,
    "rsi_trailing_pct": TRAIL_PCT_1H,
    "trailing_enabled": False, "adaptive_trailing_enabled": False,
    "ema_length": 200, "fast_ema_len": 7,
    "macd_fast": 12, "macd_slow": 26, "macd_signal": 9,
    "timeframe": "1h",
}


def prepare_1h(df: pd.DataFrame, settings: dict) -> pd.DataFrame:
    """Compute indicators on 1h dataframe. Same indicator set as engine.py prepare()."""
    d = df.copy().reset_index(drop=True)
    d["rsi"] = ta.rsi(d["close"], length=14)
    macd = ta.macd(d["close"],
                   fast=settings["macd_fast"],
                   slow=settings["macd_slow"],
                   signal=settings["macd_signal"])
    hist_col = next((c for c in macd.columns if c.startswith("MACDh_")), None)
    d["macd_hist"] = macd[hist_col]
    d["trend_ema"] = ta.ema(d["close"], length=settings["ema_length"])
    d["fast_ema"]  = ta.ema(d["close"], length=settings["fast_ema_len"])
    adx = ta.adx(d["high"], d["low"], d["close"], length=14)
    d["adx"] = adx["ADX_14"]
    # ATR in price terms (not pct yet -- converted per-bar in simulate)
    d["atr"] = ta.atr(d["high"], d["low"], d["close"], length=14)
    d["vol_sma"] = d["volume"].rolling(20).mean()
    avg_size = (d["high"] - d["low"]).rolling(20).mean()
    d["fluctuation_factor"] = avg_size / (d["close"] * 0.0002)
    d["is_lateral"] = (d["fluctuation_factor"] < 0.5) | (d["adx"] < 20)
    return d.fillna({
        "rsi": 50, "macd_hist": 0, "trend_ema": 0, "fast_ema": 0,
        "adx": 0, "atr": 0, "vol_sma": 0,
        "fluctuation_factor": 0, "is_lateral": False,
    })


def to_arrays_1h(d: pd.DataFrame) -> dict:
    return {
        "close":  d["close"].to_numpy(float),
        "high":   d["high"].to_numpy(float),
        "low":    d["low"].to_numpy(float),
        "vol":    d["volume"].to_numpy(float),
        "time":   d["open_time"].to_numpy(),
        "rsi":    d["rsi"].to_numpy(float),
        "macd_hist":  d["macd_hist"].to_numpy(float),
        "trend_ema":  d["trend_ema"].to_numpy(float),
        "fast_ema":   d["fast_ema"].to_numpy(float),
        "adx":        d["adx"].to_numpy(float),
        "vol_sma":    d["vol_sma"].to_numpy(float),
        "atr":        d["atr"].to_numpy(float),
        "is_lateral": d["is_lateral"].to_numpy(bool),
    }


def _atr_pct(atr_price: float, close: float) -> float:
    """ATR as fraction of close, clamped to [floor, ceil]. (Supuesto H)"""
    if close <= 0:
        return ATR_PCT_FLOOR
    raw = atr_price / close
    return max(ATR_PCT_FLOOR, min(ATR_PCT_CEIL, raw))


def _simulate_maker(arr: dict, symbol: str, settings: dict, costs: MakerCostModel,
                    entry_decider: Callable, initial_equity: float, trade_qty: float,
                    start_idx: int, end_idx: int, build_curve: bool = True):
    """Core simulation loop for maker/1h variant.

    State machine
    -------------
    FLAT  -> signal bar i -> post limit at limit_price
    PENDING_FILL -> scan bars [i+1, i+expiry_bars]:
        - bar j has low <= limit_price: FILL -> IN_POSITION
        - all expiry_bars pass without fill: EXPIRE -> FLAT (no-fill)
    IN_POSITION -> check SL/TRAIL/TP on each bar:
        - SL: low <= sl_price -> exit at sl_fill_price (market/taker)
        - TRAIL: trailing stop activated if high > entry; market exit
        - TP: high >= tp_price -> exit at tp_fill_price (limit/maker)
    -> FLAT + cooldown
    """
    close_arr = arr["close"]
    high_arr  = arr["high"]
    low_arr   = arr["low"]
    atr_arr   = arr["atr"]
    tarr      = arr["time"]

    trail_pct   = settings.get("rsi_trailing_pct", TRAIL_PCT_1H)
    cooldown_bars = max(1, int(settings["cooldown_minutes"] / BAR_MINUTES))

    # State
    cash        = initial_equity
    qty         = 0.0
    entry_price = 0.0        # actual fill price (after entry_slip)
    entry_basis = 0.0        # cash committed (notional + entry fee)
    entry_t     = None
    entry_score = 0.0
    sl_price    = 0.0
    tp_price    = 0.0
    highest     = 0.0
    cooldown_until = -1

    # Pending limit state
    pending      = False
    limit_price  = 0.0
    expire_at    = -1        # bar index at which the limit expires (exclusive)
    pending_score = 0.0
    pending_t    = None

    trades:  list[dict] = []
    curve_t: list = []
    curve_e: list = []

    n = len(close_arr)

    for i in range(start_idx, end_idx):
        c = close_arr[i]

        # -- IN POSITION: check exits -------------------------------------------
        if qty > 0.0:
            h, lo = high_arr[i], low_arr[i]
            if h > highest:
                highest = h

            exit_mid = 0.0
            reason   = ""

            # 1) SL (MARKET/taker, fills below sl_price)
            if lo <= sl_price:
                fill_p = costs.sl_fill_price(symbol, sl_price)
                exit_mid, reason = fill_p, "SL"
            else:
                # 2) Trail (market/taker): once in profit, trail below peak
                if highest > entry_price:
                    trail_floor = highest * (1.0 - trail_pct / 100.0)
                    if lo <= trail_floor and trail_floor > sl_price:
                        # Treat trail exit as taker (market)
                        # fill_p = taker slippage on trail_floor
                        bps = costs.sl_slip_bps_majors if symbol in _MAJORS else costs.sl_slip_bps_alts
                        fill_p = trail_floor * (1.0 - bps / 10_000.0)
                        exit_mid, reason = fill_p, "TRAIL"
                # 3) TP (LIMIT/maker)
                if not reason and h >= tp_price:
                    fill_p = costs.tp_fill_price(tp_price)
                    exit_mid, reason = fill_p, "TP"

            if reason:
                proceeds = qty * exit_mid - costs.fee(qty * exit_mid)
                net = proceeds - entry_basis
                cash += proceeds
                trades.append({
                    "symbol": symbol, "entry_time": entry_t, "exit_time": tarr[i],
                    "entry_price": entry_price, "exit_price": exit_mid,
                    "net_pnl": net,
                    "net_return_pct": net / entry_basis * 100.0 if entry_basis > 0 else 0.0,
                    "reason": reason, "score": entry_score,
                })
                qty       = 0.0
                highest   = 0.0
                cooldown_until = i + cooldown_bars

        # -- PENDING LIMIT: check for fill or expiry ----------------------------
        elif pending:
            lo = low_arr[i]
            if lo <= limit_price:
                # FILL: entry at limit_price + entry_slip (Supuesto B, C)
                fill_p  = costs.entry_fill_price(limit_price)
                notional = trade_qty if trade_qty < cash else cash
                if notional > 1.0:
                    entry_basis = notional + costs.fee(notional)
                    qty         = notional / fill_p
                    entry_price = fill_p
                    cash       -= entry_basis
                    entry_t     = tarr[i]
                    entry_score = pending_score
                    highest     = high_arr[i]

                    atr_p   = atr_arr[i] if atr_arr[i] > 0 else atr_arr[max(0, i-1)]
                    atr_frac = _atr_pct(atr_p, fill_p)
                    sl_price = entry_price * (1.0 - ATR_SL_MULT * atr_frac)
                    tp_price = entry_price * (1.0 + ATR_TP_MULT * atr_frac)
                pending = False
            elif i >= expire_at:
                # EXPIRY: limit cancelled, no-fill. Opportunity cost not counted
                # in PnL (correctly -- we never entered, so no capital at risk).
                # NO-FILL is logged only via missing trades, which reduces trade
                # count and expectancy denominator (honest).
                pending = False

        # -- FLAT + no pending: check for new signal ----------------------------
        elif i >= cooldown_until and not pending:
            ok, score = entry_decider(i)
            if ok and cash > 1.0:
                # Post limit order (Supuesto A, F)
                lp = costs.limit_price(c)
                pending       = True
                limit_price   = lp
                expire_at     = i + costs.expiry_bars  # exclusive: bars i+1..i+expiry_bars
                pending_score = score
                pending_t     = tarr[i]

        if build_curve:
            curve_t.append(tarr[i])
            curve_e.append(cash + qty * c)

    # End-of-data: close any open position at last close (EOD)
    if qty > 0.0:
        j = end_idx - 1
        ep = close_arr[j]
        bps = costs.sl_slip_bps_majors if symbol in _MAJORS else costs.sl_slip_bps_alts
        fill_p = ep * (1.0 - bps / 10_000.0)  # treat as market exit
        proceeds = qty * fill_p - costs.fee(qty * fill_p)
        net = proceeds - entry_basis
        trades.append({
            "symbol": symbol, "entry_time": entry_t, "exit_time": tarr[j],
            "entry_price": entry_price, "exit_price": fill_p,
            "net_pnl": net,
            "net_return_pct": net / entry_basis * 100.0 if entry_basis > 0 else 0.0,
            "reason": "EOD", "score": entry_score,
        })

    curve = [{"time": t, "equity": e} for t, e in zip(curve_t, curve_e)]
    return trades, curve


# Module-level set for fast symbol lookup in _simulate_maker
_MAJORS = {"BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"}


def strategy_decider_1h(arr: dict, settings: dict) -> Callable:
    """Same SmartScalper scorer as engine.py, on 1h arrays.

    No lateral gate applied here -- see Supuesto L for rationale.
    Quant may want to run a gated variant (easy: add 'if lat[i]: return False, 0.0').
    """
    strat    = SmartScalperStrategy()
    min_score = settings["smart_scalper_entry_score"]
    rsi  = arr["rsi"]
    mh   = arr["macd_hist"]
    te   = arr["trend_ema"]
    fe   = arr["fast_ema"]
    adx  = arr["adx"]
    vs   = arr["vol_sma"]
    vol  = arr["vol"]
    close = arr["close"]

    def decide(i):
        ind = {
            "rsi": rsi[i], "macd_hist": mh[i], "macd_signal": 0.0,
            "trend_ema": te[i], "fast_ema": fe[i], "is_lateral": False,
            "adx": adx[i], "current_vol": vol[i], "vol_sma": vs[i],
        }
        score, _ = strat.score_buy_setup(ind, settings, {"current_price": close[i]})
        return (score >= min_score), float(score)

    return decide


def run_strategy_maker(arr: dict, symbol: str, settings: dict, costs: MakerCostModel,
                       initial_equity: float = 1000.0, trade_qty: float = 12.0,
                       start_idx: int | None = None, end_idx: int | None = None,
                       build_curve: bool = True):
    """Public entry point. API mirrors engine.run_strategy for drop-in use in run_maker.py."""
    start_idx = WARMUP if start_idx is None else max(start_idx, WARMUP)
    end_idx   = len(arr["close"]) if end_idx is None else end_idx
    decider   = strategy_decider_1h(arr, settings)
    return _simulate_maker(arr, symbol, settings, costs, decider, initial_equity,
                           trade_qty, start_idx, end_idx, build_curve)


def random_montecarlo_maker(arr: dict, symbol: str, settings: dict, costs: MakerCostModel,
                            initial_equity: float, trade_qty: float,
                            start_idx: int, end_idx: int,
                            n_target: int, runs: int = 500, seed: int = 42) -> dict:
    """Monte Carlo random-entry baseline for the maker/1h variant.

    SYMMETRY CONTRACT (auditor checkpoint)
    ---------------------------------------
    The random baseline must use EXACTLY the same execution model as the strategy:
      - Same MakerCostModel (limit-entry + no-fill + expiry, SL taker, TP maker).
      - Same exits: SL/TP by ATR multipliers (ATR_SL_MULT / ATR_TP_MULT), trailing.
      - Same costs on every leg (entry maker fee, SL taker slippage, TP maker slippage).
    The ONLY thing that differs from run_strategy_maker is the entry timing: instead
    of requiring score >= min_score, each eligible bar is entered with probability p
    (drawn uniformly). This isolates whether the entry SIGNAL adds edge above random.

    WHAT WAS WRONG BEFORE (fixed here)
    ------------------------------------
    The old code called baselines.random_montecarlo() which delegates to engine._simulate
    (the 5m motor). engine._simulate reads settings["stop_loss_pct"] and
    settings["take_profit_pct"]. DEFAULT_SETTINGS_1H sets both to 0.0 so that the
    maker engine ignores them (it uses ATR multipliers). But engine._simulate has
    guards `if sl_pct > 0` and `if tp_pct > 0`, so with those fields at 0, SL and TP
    were completely DISABLED for the random run -- only trailing remained active.
    Result: random baseline = solo-trailing taker, strategy = ATR SL+TP+trailing maker.
    That is an exit-asymmetric comparison: pears vs apples. This function fixes it by
    driving _simulate_maker with a random decider, which enforces identical exits.

    Parameters
    ----------
    n_target : int
        Target number of trades to match (controls entry probability p).
    runs : int
        Number of Monte Carlo runs.
    seed : int
        RNG seed for reproducibility.

    Returns
    -------
    dict with keys:
        p                   -- entry probability per bar
        runs_with_trades    -- runs that produced at least one trade
        avg_n_trades        -- mean trades per run
        exp_per_trade_mean  -- mean of per-run mean(net_pnl/trade)
        exp_per_trade_p50   -- 50th percentile of per-run expectancy
        exp_per_trade_p95   -- 95th percentile of per-run expectancy
        net_pnl_mean        -- mean total net PnL across runs
        net_pnl_p95         -- 95th percentile total net PnL
        _exp_dist           -- full numpy array of per-run expectancies (for percentile_of)
        _net_dist           -- full numpy array of per-run net PnLs
    """
    eligible = end_idx - start_idx
    p = min(1.0, n_target / eligible) if eligible > 0 else 0.0
    rng = np.random.default_rng(seed)
    n_bars = len(arr["close"])

    exp_per_trade: list[float] = []
    net_pnls: list[float] = []
    n_trades_list: list[int] = []

    for _ in range(runs):
        draws = rng.random(n_bars)

        # Random decider: enter with probability p at any eligible bar.
        # Score is 0.0 (unused by _simulate_maker exits -- exits are ATR-based).
        def decide(i: int, _draws=draws) -> tuple[bool, float]:
            return (_draws[i] < p), 0.0

        trades, _ = _simulate_maker(
            arr, symbol, settings, costs, decide, initial_equity,
            trade_qty, start_idx, end_idx, build_curve=False,
        )
        if trades:
            pnls = [t["net_pnl"] for t in trades]
            exp_per_trade.append(float(np.mean(pnls)))
            net_pnls.append(float(sum(pnls)))
            n_trades_list.append(len(trades))

    exp_arr = np.array(exp_per_trade) if exp_per_trade else np.array([0.0])
    net_arr = np.array(net_pnls)      if net_pnls      else np.array([0.0])
    return {
        "p":                   p,
        "runs_with_trades":    len(exp_per_trade),
        "avg_n_trades":        float(np.mean(n_trades_list)) if n_trades_list else 0.0,
        "exp_per_trade_mean":  float(exp_arr.mean()),
        "exp_per_trade_p50":   float(np.percentile(exp_arr, 50)),
        "exp_per_trade_p95":   float(np.percentile(exp_arr, 95)),
        "net_pnl_mean":        float(net_arr.mean()),
        "net_pnl_p95":         float(np.percentile(net_arr, 95)),
        "_exp_dist":           exp_arr,
        "_net_dist":           net_arr,
    }
