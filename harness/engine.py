"""Event-driven backtest engine (numpy-fast).

- ENTRIES come from the REAL strategy code (backend.strategies.smart_scalper),
  so we validate exactly what production runs. Lateral-market gate replicated
  from bot_logic._run_strategies (lateral blocks entry before scoring).
- EXITS replicate base_strategy.check_standard_exits precedence:
    1) Stop Loss             (intrabar LOW touch)
    2) Trailing / profit-step (ALWAYS on once price > entry; trail below peak)
    3) Take Profit           (intrabar HIGH touch)
  Within a bar, worst-case ordering = losses first (SL/trail before TP).
- Fees + slippage from costs.CostModel on BOTH sides.
- One position at a time per symbol (matches the bot). Cooldown enforced.

Indicators are vectorized once over the full series to match
backend.indicators.calculate_indicators semantics, then read per-bar from
numpy arrays for speed.
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
from harness.costs import CostModel  # noqa: E402

DEFAULT_SETTINGS = {
    "buy_rsi": 38.0, "sell_rsi": 70.0, "smart_scalper_entry_score": 52.0,
    "stop_loss_pct": 1.5, "take_profit_pct": 1.5, "cooldown_minutes": 3,
    "enable_trend_filter": False, "enable_fast_ema": False,
    "rsi_trailing_pct": 0.8, "trailing_enabled": False,
    "adaptive_trailing_enabled": False,
    "ema_length": 200, "fast_ema_len": 7,
    "macd_fast": 12, "macd_slow": 26, "macd_signal": 9, "timeframe": "5m",
}

BAR_MINUTES = 5
WARMUP = 250


def prepare(df: pd.DataFrame, settings: dict) -> pd.DataFrame:
    d = df.copy().reset_index(drop=True)
    d["rsi"] = ta.rsi(d["close"], length=14)
    macd = ta.macd(d["close"], fast=settings["macd_fast"], slow=settings["macd_slow"], signal=settings["macd_signal"])
    hist_col = next((c for c in macd.columns if c.startswith("MACDh_")), None)
    d["macd_hist"] = macd[hist_col]
    d["trend_ema"] = ta.ema(d["close"], length=settings["ema_length"])
    d["fast_ema"] = ta.ema(d["close"], length=settings["fast_ema_len"])
    adx = ta.adx(d["high"], d["low"], d["close"], length=14)
    d["adx"] = adx["ADX_14"]
    d["atr"] = ta.atr(d["high"], d["low"], d["close"], length=14)
    d["vol_sma"] = d["volume"].rolling(20).mean()
    avg_size = (d["high"] - d["low"]).rolling(20).mean()
    d["fluctuation_factor"] = avg_size / (d["close"] * 0.0002)
    d["is_lateral"] = (d["fluctuation_factor"] < 0.5) | (d["adx"] < 20)
    return d.fillna({"rsi": 50, "macd_hist": 0, "trend_ema": 0, "fast_ema": 0,
                     "adx": 0, "atr": 0, "vol_sma": 0,
                     "fluctuation_factor": 0, "is_lateral": False})


def to_arrays(d: pd.DataFrame) -> dict:
    return {
        "close": d["close"].to_numpy(float),
        "high": d["high"].to_numpy(float),
        "low": d["low"].to_numpy(float),
        "vol": d["volume"].to_numpy(float),
        "time": d["open_time"].to_numpy(),  # datetime64[ns]
        "rsi": d["rsi"].to_numpy(float),
        "macd_hist": d["macd_hist"].to_numpy(float),
        "trend_ema": d["trend_ema"].to_numpy(float),
        "fast_ema": d["fast_ema"].to_numpy(float),
        "adx": d["adx"].to_numpy(float),
        "vol_sma": d["vol_sma"].to_numpy(float),
        "is_lateral": d["is_lateral"].to_numpy(bool),
    }


def _simulate(arr: dict, symbol: str, settings: dict, costs: CostModel,
              entry_decider: Callable, initial_equity: float, trade_qty: float,
              start_idx: int, end_idx: int, build_curve: bool = True):
    close, high, low, tarr = arr["close"], arr["high"], arr["low"], arr["time"]
    sl_pct = settings["stop_loss_pct"]
    tp_pct = settings["take_profit_pct"]
    trail_pct = settings["rsi_trailing_pct"]
    cooldown_bars = max(1, int(settings["cooldown_minutes"] / BAR_MINUTES))

    cash = initial_equity
    qty = 0.0
    entry_price = 0.0
    entry_basis = 0.0
    entry_t = None
    entry_score = 0.0
    highest = 0.0
    cooldown_until = -1

    trades: list[dict] = []
    curve_t: list = []
    curve_e: list = []

    for i in range(start_idx, end_idx):
        c = close[i]
        if qty > 0.0:
            h, lo = high[i], low[i]
            if h > highest:
                highest = h
            exit_mid = 0.0
            reason = ""
            sl_price = entry_price * (1 - sl_pct / 100.0)
            if sl_pct > 0 and lo <= sl_price:
                exit_mid, reason = sl_price, "SL"
            else:
                if highest > entry_price:
                    trail_price = highest * (1 - trail_pct / 100.0)
                    if lo <= trail_price and trail_price > sl_price:
                        exit_mid, reason = trail_price, "TRAIL"
                if not reason and tp_pct > 0:
                    tp_price = entry_price * (1 + tp_pct / 100.0)
                    if h >= tp_price:
                        exit_mid, reason = tp_price, "TP"
            if reason:
                fill = costs.fill_price(symbol, exit_mid, "SELL", qty * exit_mid)
                proceeds = qty * fill - costs.fee(qty * fill)
                net = proceeds - entry_basis
                cash += proceeds
                trades.append({
                    "symbol": symbol, "entry_time": entry_t, "exit_time": tarr[i],
                    "entry_price": entry_price, "exit_price": fill, "net_pnl": net,
                    "net_return_pct": net / entry_basis * 100.0 if entry_basis > 0 else 0.0,
                    "reason": reason, "score": entry_score,
                })
                qty = 0.0
                highest = 0.0
                cooldown_until = i + cooldown_bars
        elif i >= cooldown_until:
            ok, score = entry_decider(i)
            if ok:
                notional = trade_qty if trade_qty < cash else cash
                if notional > 1.0:
                    fill = costs.fill_price(symbol, c, "BUY", notional)
                    entry_basis = notional + costs.fee(notional)
                    qty = notional / fill
                    entry_price = fill
                    cash -= entry_basis
                    entry_t = tarr[i]
                    entry_score = score
                    highest = high[i]

        if build_curve:
            curve_t.append(tarr[i])
            curve_e.append(cash + qty * c)

    if qty > 0.0:
        j = end_idx - 1
        fill = costs.fill_price(symbol, close[j], "SELL", qty * close[j])
        proceeds = qty * fill - costs.fee(qty * fill)
        net = proceeds - entry_basis
        trades.append({
            "symbol": symbol, "entry_time": entry_t, "exit_time": tarr[j],
            "entry_price": entry_price, "exit_price": fill, "net_pnl": net,
            "net_return_pct": net / entry_basis * 100.0 if entry_basis > 0 else 0.0,
            "reason": "EOD", "score": entry_score,
        })

    curve = [{"time": t, "equity": e} for t, e in zip(curve_t, curve_e)]
    return trades, curve


def strategy_decider(arr: dict, settings: dict) -> Callable:
    strat = SmartScalperStrategy()
    min_score = settings["smart_scalper_entry_score"]
    rsi, mh, te, fe = arr["rsi"], arr["macd_hist"], arr["trend_ema"], arr["fast_ema"]
    adx, vs, vol, lat = arr["adx"], arr["vol_sma"], arr["vol"], arr["is_lateral"]
    close = arr["close"]

    def decide(i):
        if lat[i]:
            return False, 0.0
        ind = {"rsi": rsi[i], "macd_hist": mh[i], "macd_signal": 0.0,
               "trend_ema": te[i], "fast_ema": fe[i], "is_lateral": bool(lat[i]),
               "adx": adx[i], "current_vol": vol[i], "vol_sma": vs[i]}
        score, _ = strat.score_buy_setup(ind, settings, {"current_price": close[i]})
        return (score >= min_score), float(score)

    return decide


def run_strategy(arr: dict, symbol: str, settings: dict, costs: CostModel,
                 initial_equity: float = 1000.0, trade_qty: float = 12.0,
                 start_idx: int | None = None, end_idx: int | None = None,
                 build_curve: bool = True):
    start_idx = WARMUP if start_idx is None else max(start_idx, WARMUP)
    end_idx = len(arr["close"]) if end_idx is None else end_idx
    decider = strategy_decider(arr, settings)
    return _simulate(arr, symbol, settings, costs, decider, initial_equity,
                     trade_qty, start_idx, end_idx, build_curve)
