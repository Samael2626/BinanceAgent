"""
Harness de validación OOS para `KronosQuantStrategy` en Futuros USDⓈ-M y Spot
para cuentas pequeñas (< 50 USDT, capital base 47 USDT, nocional 12 USDT a 2x aislado).

Evalúa:
  1. Costes reales de Futuros USDⓈ-M:
     - Maker (`LIMIT_MAKER`): 0.02% por lado + 1 bp de deslizamiento adverso
     - Stress Taker (`MARKET`): 0.05% por lado + 4 bps de deslizamiento adverso
     - Liquidación de Funding Rate cada 8 horas (00:00, 08:00, 16:00 UTC)
  2. Operación bidireccional (`LONG` y `SHORT`) con Stop Loss y Take Profit por ATR
     y filtro de Valor Esperado Neto (Meta-Labeling).
  3. Verificación contra el Gate (`harness.gate.assess_backtest`):
     - >= 30 operaciones OOS
     - Expectancy neta > 0 USDT/trade
     - Profit Factor > 1.0
     - Max Drawdown <= 8.0%
     - Expectancy neta > percentil 95 de entradas aleatorias simétricas (`LONG`/`SHORT`)
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.kronos_adapter import DEFAULT_KRONOS_MODEL, KronosAdapter
from backend.services.microstructure import LeadLagAnalyzer
from backend.strategies.kronos_quant import KronosQuantStrategy
from harness import data_loader, engine, gate, metrics, splits


@dataclass(frozen=True)
class FuturesCostModel:
    fee_pct_per_side: float      # e.g., 0.02 for Maker, 0.05 for Taker
    slippage_bps_per_side: float  # e.g., 1.0 for Maker, 4.0 for Stress
    funding_rate_8h_pct: float = 0.01  # 0.01% per 8h standard baseline funding

    @classmethod
    def maker_base(cls) -> "FuturesCostModel":
        return cls(fee_pct_per_side=0.02, slippage_bps_per_side=1.0, funding_rate_8h_pct=0.01)

    @classmethod
    def taker_base(cls) -> "FuturesCostModel":
        return cls(fee_pct_per_side=0.05, slippage_bps_per_side=1.0, funding_rate_8h_pct=0.01)

    @classmethod
    def taker_stress(cls) -> "FuturesCostModel":
        return cls(fee_pct_per_side=0.05, slippage_bps_per_side=4.0, funding_rate_8h_pct=0.01)

    def fill_price(self, mid_price: float, side: str) -> float:
        mult = 1.0 + (self.slippage_bps_per_side / 10000.0) * (1.0 if side == "BUY" else -1.0)
        return mid_price * mult

    def fee_usdt(self, notional: float) -> float:
        return notional * (self.fee_pct_per_side / 100.0)


def simulate_futures_kronos(
    df: pd.DataFrame,
    symbol: str,
    cost_model: FuturesCostModel,
    *,
    initial_equity: float = 47.0,
    notional_per_trade: float = 20.0,
    leverage: int = 2,
    start_idx: int = 250,
    end_idx: int | None = None,
    min_ev_bps: float = 12.0,
    d_btc: pd.DataFrame | None = None,
) -> tuple[list[dict], list[dict]]:
    """
    Simulates `KronosQuantStrategy` on 1h closed bars with isolated margin,
    worst-case intrabar exit ordering (SL before TP), and 8h funding settlements.
    Uses institutional asymmetric fat-tail capture (wide 2.2x ATR Chandelier stop
    + EMA50 regime-breakdown exit + 5.0% structural TP) so winning trends compound
    enough to absorb both Maker (4 bps) and Stress Taker (18 bps) round-trip costs.
    """
    settings = {
        **engine.DEFAULT_SETTINGS,
        "timeframe": "1h",
        "market_type": "FUTURES",
        "futures_leverage": leverage,
        "futures_allow_short": True,
        "order_execution_style": "MARKET",
        "stop_loss_pct": 1.5,
        "take_profit_pct": 2.0,
        "atr_stop_mult": 1.6,
        "atr_tp_multiplier": 2.2,
        "kronos_min_ev_bps": min_ev_bps,
        "kronos_min_rr_ratio": 1.3,
        "smart_scalper_entry_score": 68.0,
        "kronos_min_prob_win": 0.52,
    }
    prep = engine.prepare(df, settings)
    end_idx = len(prep) if end_idx is None else min(end_idx, len(prep))
    start_idx = max(start_idx, 250)

    btc_prep = None
    btc_time_to_idx: dict[pd.Timestamp, int] = {}
    lead_analyzer = None
    if d_btc is not None:
        try:
            btc_prep = engine.prepare(d_btc, settings)
            btc_times = pd.to_datetime(btc_prep["open_time"], utc=True).to_list()
            btc_closes = btc_prep["close"].to_numpy(float)
            btc_f_ema = btc_prep["fast_ema"].to_numpy(float)
            btc_t_ema = btc_prep["trend_ema"].to_numpy(float)
            btc_time_to_idx = {t: idx for idx, t in enumerate(btc_times)}
            lead_analyzer = LeadLagAnalyzer("BTCUSDT")
        except Exception:
            btc_prep = None

    closes = prep["close"].to_numpy(float)
    opens = prep["open"].to_numpy(float)
    highs = prep["high"].to_numpy(float)
    lows = prep["low"].to_numpy(float)
    vols = prep["volume"].to_numpy(float)
    vol_sma = prep["vol_sma"].to_numpy(float)
    times = pd.to_datetime(prep["open_time"], utc=True).to_list()
    rsis = prep["rsi"].to_numpy(float)
    macd_h = prep["macd_hist"].to_numpy(float)
    t_ema = prep["trend_ema"].to_numpy(float)
    f_ema = prep["fast_ema"].to_numpy(float)
    adxs = prep["adx"].to_numpy(float)
    atrs = prep["atr"].to_numpy(float)
    lats = prep["is_lateral"].to_numpy(bool)

    # Precompute institutional regime triggers (strictly causal: uses bars up to i)
    s_high = pd.Series(highs)
    s_low = pd.Series(lows)
    s_close = pd.Series(closes)
    ema_50 = s_close.ewm(span=50, adjust=False).mean().to_numpy(float)
    # 36-bar Donchian high/low (1.5 days structural breakout, shifted by 1 so strictly causal)
    donchian_high_36 = s_high.shift(1).rolling(36).max().fillna(0.0).to_numpy(float)
    donchian_low_36 = s_low.shift(1).rolling(36).min().fillna(1e18).to_numpy(float)
    # Rolling 24-bar return Z-score to detect Liquidation Cascades (capitulation flushes)
    ret_1b = s_close.pct_change().fillna(0.0)
    ret_mean = ret_1b.rolling(24).mean().fillna(0.0)
    ret_std = ret_1b.rolling(24).std().replace(0, 1e-6).fillna(1e-6)
    z_score_arr = ((ret_1b - ret_mean) / ret_std).to_numpy(float)

    adapter = KronosAdapter(model_id=DEFAULT_KRONOS_MODEL)
    strat = KronosQuantStrategy()

    wallet = initial_equity
    pos_side = ""      # "LONG" or "SHORT"
    pos_qty = 0.0
    entry_price = 0.0
    peak_price = 0.0
    stop_price = 0.0
    entry_bar_idx = 0
    iso_margin = 0.0
    entry_fee = 0.0
    funding_accrued = 0.0
    entry_time = None
    tp_pct = 2.0
    sl_pct = 1.5
    cooldown_until = -1
    be_locked = False

    trades: list[dict] = []
    curve: list[dict] = []

    for i in range(start_idx, end_idx):
        c = closes[i]
        h = highs[i]
        lo = lows[i]
        t = times[i]

        if pos_qty > 0.0:
            # 8h funding settlement at 00:00, 08:00, 16:00 UTC
            if t.hour in {0, 8, 16} and t.minute == 0:
                notional_mark = pos_qty * c
                rate = cost_model.funding_rate_8h_pct / 100.0
                cashflow = (-notional_mark * rate) if pos_side == "LONG" else (notional_mark * rate)
                wallet += cashflow
                funding_accrued += cashflow

            exit_mid = 0.0
            reason = ""
            atr_now = max(atrs[i], entry_price * 0.005)
            if pos_side == "LONG":
                # Confirmed closed-bar profit protection:
                if not be_locked and i > entry_bar_idx and closes[i - 1] >= entry_price * 1.0100:
                    stop_price = max(stop_price, entry_price * 1.0025)
                    be_locked = True
                elif be_locked and i > entry_bar_idx and closes[i - 1] >= entry_price * 1.0145:
                    stop_price = max(stop_price, entry_price * 1.0060)

                tp_p = entry_price * (1.0 + tp_pct / 100.0)
                if lo <= stop_price:
                    exit_mid = min(opens[i], stop_price)
                    reason = "PROFIT_LOCK_LONG" if stop_price >= entry_price * 1.0050 else ("TRAIL_LONG" if stop_price > entry_price else "SL_LONG")
                elif h >= tp_p:
                    exit_mid, reason = tp_p, "TP_LONG"
                else:
                    peak_price = max(peak_price, h)
                    # Institutional 2.4x ATR Chandelier stop
                    stop_price = max(stop_price, peak_price - 2.4 * atr_now)
                    if c < ema_50[i] and peak_price >= entry_price * 1.012:
                        exit_mid, reason = c, "EMA50_EXIT_LONG"
                    elif (i - entry_bar_idx) >= 8 and c >= entry_price * 1.0020:
                        exit_mid, reason = c, "TIME_EXIT_LONG"
                    elif (i - entry_bar_idx) >= 3 and c >= entry_price * 1.0006:
                        exit_mid, reason = c, "SCRATCH_LONG"
            else:
                # Confirmed closed-bar profit protection:
                if not be_locked and i > entry_bar_idx and closes[i - 1] <= entry_price * 0.9900:
                    stop_price = min(stop_price, entry_price * 0.9975)
                    be_locked = True
                elif be_locked and i > entry_bar_idx and closes[i - 1] <= entry_price * 0.9855:
                    stop_price = min(stop_price, entry_price * 0.9940)

                tp_p = entry_price * (1.0 - tp_pct / 100.0)
                if h >= stop_price:
                    exit_mid = max(opens[i], stop_price)
                    reason = "PROFIT_LOCK_SHORT" if stop_price <= entry_price * 0.9950 else ("TRAIL_SHORT" if stop_price < entry_price else "SL_SHORT")
                elif lo <= tp_p:
                    exit_mid, reason = tp_p, "TP_SHORT"
                else:
                    peak_price = min(peak_price, lo) if peak_price > 0 else lo
                    stop_price = min(stop_price, peak_price + 2.4 * atr_now)
                    if c > ema_50[i] and peak_price <= entry_price * 0.988:
                        exit_mid, reason = c, "EMA50_EXIT_SHORT"
                    elif (i - entry_bar_idx) >= 8 and c <= entry_price * 0.9980:
                        exit_mid, reason = c, "TIME_EXIT_SHORT"
                    elif (i - entry_bar_idx) >= 3 and c <= entry_price * 0.9994:
                        exit_mid, reason = c, "SCRATCH_SHORT"

            if reason:
                close_order_side = "SELL" if pos_side == "LONG" else "BUY"
                fill = cost_model.fill_price(exit_mid, close_order_side)
                exit_notional = pos_qty * fill
                exit_fee = cost_model.fee_usdt(exit_notional)
                gross_pnl = (
                    (fill - entry_price) * pos_qty
                    if pos_side == "LONG"
                    else (entry_price - fill) * pos_qty
                )
                net_pnl = gross_pnl - entry_fee - exit_fee + funding_accrued
                wallet += iso_margin + gross_pnl - exit_fee
                trades.append({
                    "symbol": symbol,
                    "side": pos_side,
                    "entry_time": entry_time,
                    "exit_time": t,
                    "entry_price": entry_price,
                    "exit_price": fill,
                    "net_pnl": net_pnl,
                    "net_return_pct": (net_pnl / max(iso_margin, 1e-9)) * 100.0,
                    "reason": reason,
                })
                pos_qty = 0.0
                pos_side = ""
                peak_price = 0.0
                stop_price = 0.0
                iso_margin = 0.0
                funding_accrued = 0.0
                be_locked = False
                cooldown_until = i + 6

        elif i >= cooldown_until and i + 1 < end_idx and not lats[i]:
            # Evaluate BTC anchor snapshot
            macro_lead: dict[str, Any] = {}
            btc_trend = "NEUTRAL"
            if lead_analyzer is not None and btc_prep is not None and t in btc_time_to_idx:
                b_idx = btc_time_to_idx[t]
                btc_c = btc_closes[b_idx]
                btc_ret1 = (btc_c / btc_closes[b_idx - 1] - 1.0) * 100.0 if b_idx > 0 else 0.0
                snap = lead_analyzer.evaluate(
                    btc_current_price=btc_c,
                    btc_ema_fast=btc_f_ema[b_idx],
                    btc_ema_trend=btc_t_ema[b_idx],
                    btc_return_1h_pct=btc_ret1,
                )
                macro_lead = snap.to_dict()
                btc_trend = snap.trend

            # Macro BTC alignment: no alt shorts into a BTC bullish trend (anti-squeeze shield)
            short_allowed = (btc_trend != "BULLISH")

            # High-Conviction Asymmetric Pre-Filter with Anti-Wick Quality Gate
            rvol = vols[i] / max(vol_sma[i], 1e-12)
            bar_range = max(highs[i] - lows[i], 1e-6)
            close_pct_in_bar = (closes[i] - lows[i]) / bar_range
            bull_candle_ok = close_pct_in_bar >= 0.60
            bear_candle_ok = close_pct_in_bar <= 0.40

            prefilter = strat.classify_entry_prefilter({
                "rvol": rvol, "candle_close_pct": close_pct_in_bar,
                "rsi": rsis[i], "adx": adxs[i], "trend_ema": t_ema[i],
                "fast_ema": f_ema[i], "ema_50": ema_50[i],
                "return_z_score": z_score_arr[i],
                "donchian_high_36": donchian_high_36[i],
                "donchian_low_36": donchian_low_36[i],
            }, {"current_price": c, "macro_lead": macro_lead})
            is_long_liq_flush = prefilter["long_liq_flush"]
            is_bull_breakout = prefilter["bull_breakout"]
            is_bear_breakout = prefilter["bear_breakout"]
            is_short_squeeze_flush = prefilter["short_squeeze_flush"]

            if not any(prefilter.values()):
                curve.append({"time": t, "equity": float(wallet)})
                continue

            win_start = max(0, i - 120)
            window_df = pd.DataFrame({
                "open": opens[win_start : i + 1],
                "high": highs[win_start : i + 1],
                "low": lows[win_start : i + 1],
                "close": closes[win_start : i + 1],
                "volume": vols[win_start : i + 1],
                "timestamps": times[win_start : i + 1],
            })
            kf = adapter.forecast(
                window_df,
                symbol=symbol,
                timeframe="1h",
                horizon_bars=8,
                sample_count=14,
                tp_pct=settings["take_profit_pct"],
                sl_pct=settings["stop_loss_pct"],
            )
            ind = {
                "rsi": rsis[i],
                "macd_hist": macd_h[i],
                "macd_signal": 0.0,
                "trend_ema": t_ema[i],
                "fast_ema": f_ema[i],
                "adx": adxs[i],
                "atr": atrs[i],
                "is_lateral": bool(lats[i]),
                "candle_close_pct": close_pct_in_bar,
            }
            # Add microstructure regime bonus for confirmed breakout / flush
            micro_long = 15.0 if (is_long_liq_flush or is_bull_breakout) else -20.0
            micro_short = 15.0 if (is_bear_breakout or is_short_squeeze_flush) else -20.0

            st = {
                "current_price": c,
                "kronos_forecast": kf.to_dict(),
                "macro_lead": macro_lead,
                "microstructure": {
                    "long_edge_bps_adj": micro_long,
                    "short_edge_bps_adj": micro_short,
                    "oi_regime": "LONG_BUILDUP" if micro_long > 0 else "SHORT_BUILDUP",
                    "spread_bps": 1.5,
                },
            }
            setup = strat.evaluate_setup(ind, settings, st)
            min_prob = float(settings.get("kronos_min_prob_win", 0.52) or 0.52)
            if (
                setup["side"] in {"LONG", "SHORT"}
                and setup["score"] >= settings["smart_scalper_entry_score"]
                and setup.get("prob_win", 0.5) >= min_prob
            ):
                notional = min(notional_per_trade, wallet * leverage * 0.35)
                if notional >= 5.0:
                    open_order_side = "BUY" if setup["side"] == "LONG" else "SELL"
                    next_open = opens[i + 1]
                    fill = cost_model.fill_price(next_open, open_order_side)
                    req_margin = notional / float(leverage)
                    fee = cost_model.fee_usdt(notional)
                    if req_margin + fee <= wallet:
                        wallet -= req_margin + fee
                        pos_side = setup["side"]
                        pos_qty = notional / fill
                        entry_price = fill
                        peak_price = fill
                        entry_bar_idx = i + 1
                        atr_init = max(atrs[i], fill * 0.005)
                        stop_dist = max(fill * (setup["sl_pct"] / 100.0), 1.6 * atr_init)
                        stop_price = (fill - stop_dist) if pos_side == "LONG" else (fill + stop_dist)
                        iso_margin = req_margin
                        entry_fee = fee
                        funding_accrued = 0.0
                        entry_time = times[i + 1]
                        tp_pct = 2.0 if pos_side == "LONG" else 1.9
                        sl_pct = 1.5
                        be_locked = False

        unrealized = 0.0
        if pos_qty > 0.0:
            unrealized = (
                (c - entry_price) * pos_qty
                if pos_side == "LONG"
                else (entry_price - c) * pos_qty
            )
        curve.append({"time": t, "equity": float(wallet + iso_margin + unrealized)})

    return trades, curve


def simulate_random_futures_baseline(
    frames_oos: list[tuple[pd.DataFrame, int, int]],
    cost_model: FuturesCostModel,
    *,
    target_trades_per_symbol: int = 55,
    runs: int = 80,
    seed: int = 42,
    notional_per_trade: float = 20.0,
) -> float:
    """
    Computes the 95th percentile (p95) of net expectancy (USDT/trade) across `runs`
    Monte Carlo runs of symmetric random LONG/SHORT entries under the exact same
    calibrated exit mechanics (2.4x ATR Chandelier stop + EMA50 breakdown + TP/SL) and `FuturesCostModel`.
    """
    rng = np.random.default_rng(seed)
    run_expectancies: list[float] = []
    sl_pct = 1.5
    tp_pct = 2.0

    prepped = []
    for d, s_idx, e_idx in frames_oos:
        opens = d["open"].to_numpy(float)
        highs = d["high"].to_numpy(float)
        lows = d["low"].to_numpy(float)
        closes = d["close"].to_numpy(float)
        s_close = pd.Series(closes)
        ema_50 = s_close.ewm(span=50, adjust=False).mean().to_numpy(float)
        prev_c = s_close.shift(1).fillna(s_close)
        tr = np.maximum(highs - lows, np.maximum(np.abs(highs - prev_c), np.abs(lows - prev_c)))
        atrs = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy(float)
        times = pd.to_datetime(d["open_time"], utc=True).to_numpy()
        prepped.append((opens, highs, lows, closes, ema_50, atrs, times, max(250, s_idx), min(len(d) - 24, e_idx - 24)))

    for _ in range(runs):
        candidates: list[tuple[np.datetime64, np.datetime64, float]] = []
        for opens, highs, lows, closes, ema_50, atrs, times, lo_idx, hi_idx in prepped:
            if hi_idx <= lo_idx + 10:
                continue
            entries = sorted(rng.choice(np.arange(lo_idx, hi_idx), size=min(target_trades_per_symbol, (hi_idx - lo_idx) // 4), replace=False))
            next_free = -1
            for idx in entries:
                if idx < next_free:
                    continue
                side = "LONG" if rng.random() >= 0.5 else "SHORT"
                open_side = "BUY" if side == "LONG" else "SELL"
                close_side = "SELL" if side == "LONG" else "BUY"
                entry_fill = cost_model.fill_price(opens[idx + 1], open_side)
                qty = notional_per_trade / entry_fill
                entry_fee = cost_model.fee_usdt(notional_per_trade)
                atr_init = max(atrs[idx], entry_fill * 0.005)
                stop_dist = max(entry_fill * (sl_pct / 100.0), 1.6 * atr_init)
                stop_p = (entry_fill - stop_dist) if side == "LONG" else (entry_fill + stop_dist)
                cur_tp = 2.0 if side == "LONG" else 1.9
                tp_p = entry_fill * (1.0 + cur_tp / 100.0) if side == "LONG" else entry_fill * (1.0 - cur_tp / 100.0)
                peak_p = entry_fill
                exit_mid = closes[len(closes) - 1]
                exit_bar = len(closes) - 1
                rand_locked = False
                for j in range(idx + 1, len(closes)):
                    atr_now = max(atrs[j], entry_fill * 0.005)
                    if side == "LONG":
                        if not rand_locked and j > idx + 1 and closes[j - 1] >= entry_fill * 1.0100:
                            stop_p = max(stop_p, entry_fill * 1.0025)
                            rand_locked = True
                        elif rand_locked and j > idx + 1 and closes[j - 1] >= entry_fill * 1.0145:
                            stop_p = max(stop_p, entry_fill * 1.0060)
                        if lows[j] <= stop_p:
                            exit_mid, exit_bar = min(opens[j], stop_p), j
                            break
                        if highs[j] >= tp_p:
                            exit_mid, exit_bar = tp_p, j
                            break
                        peak_p = max(peak_p, highs[j])
                        stop_p = max(stop_p, peak_p - 2.4 * atr_now)
                        if closes[j] < ema_50[j] and peak_p >= entry_fill * 1.012:
                            exit_mid, exit_bar = closes[j], j
                            break
                        elif (j - (idx + 1)) >= 8 and closes[j] >= entry_fill * 1.0020:
                            exit_mid, exit_bar = closes[j], j
                            break
                        elif (j - (idx + 1)) >= 3 and closes[j] >= entry_fill * 1.0006:
                            exit_mid, exit_bar = closes[j], j
                            break
                    else:
                        if not rand_locked and j > idx + 1 and closes[j - 1] <= entry_fill * 0.9900:
                            stop_p = min(stop_p, entry_fill * 0.9975)
                            rand_locked = True
                        elif rand_locked and j > idx + 1 and closes[j - 1] <= entry_fill * 0.9855:
                            stop_p = min(stop_p, entry_fill * 0.9940)
                        if highs[j] >= stop_p:
                            exit_mid, exit_bar = max(opens[j], stop_p), j
                            break
                        if lows[j] <= tp_p:
                            exit_mid, exit_bar = tp_p, j
                            break
                        peak_p = min(peak_p, lows[j])
                        stop_p = min(stop_p, peak_p + 2.4 * atr_now)
                        if closes[j] > ema_50[j] and peak_p <= entry_fill * 0.988:
                            exit_mid, exit_bar = closes[j], j
                            break
                        elif (j - (idx + 1)) >= 8 and closes[j] <= entry_fill * 0.9980:
                            exit_mid, exit_bar = closes[j], j
                            break
                        elif (j - (idx + 1)) >= 3 and closes[j] <= entry_fill * 0.9994:
                            exit_mid, exit_bar = closes[j], j
                            break
                exit_fill = cost_model.fill_price(exit_mid, close_side)
                exit_fee = cost_model.fee_usdt(qty * exit_fill)
                gross = (exit_fill - entry_fill) * qty if side == "LONG" else (entry_fill - exit_fill) * qty
                funding_periods = max(0, (exit_bar - (idx + 1)) // 8)
                funding_cost = notional_per_trade * (cost_model.funding_rate_8h_pct / 100.0) * funding_periods * (1.0 if side == "LONG" else -1.0)
                candidates.append((times[idx + 1], times[exit_bar], gross - entry_fee - exit_fee - funding_cost))
                next_free = exit_bar + 6
        pnls: list[float] = []
        free_time = None
        wallet = 47.0
        for entry_time, exit_time, pnl in sorted(candidates, key=lambda item: item[0]):
            if (free_time is None or entry_time >= free_time) and wallet >= notional_per_trade / 2 + cost_model.fee_usdt(notional_per_trade):
                pnls.append(pnl)
                wallet += pnl
                free_time = exit_time
        if pnls:
            run_expectancies.append(float(np.mean(pnls)))

    return float(np.percentile(run_expectancies, 95)) if run_expectancies else 0.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "LINKUSDT", "AVAXUSDT", "BNBUSDT"],
    )
    parser.add_argument("--tf", default="1h")
    parser.add_argument("--notional", type=float, default=20.0)
    args = parser.parse_args()

    print("=" * 100)
    print(f"KRONOS QUANT FUTURES HARNESS | TF={args.tf} | Equity=47 USDT | Leverage=2x | Notional={args.notional:.1f} USDT")
    print("=" * 100)

    d_btc = None
    try:
        d_btc = data_loader.load("BTCUSDT", args.tf)
    except Exception as exc:
        print(f"  [warn] BTCUSDT anchor data unavailable: {exc}")

    for label, cm in [
        ("FUTURES TAKER (5bps fee, 1bp slip)", FuturesCostModel.taker_base()),
        ("FUTURES STRESS TAKER (5bps fee, 4bps slip)", FuturesCostModel.taker_stress()),
    ]:
        all_trades = []
        curves = []
        frames_oos = []
        for sym in args.symbols:
            try:
                d = data_loader.load(sym, args.tf)
            except Exception as exc:
                print(f"  [skip {sym}] data unavailable: {exc}")
                continue
            bounds = splits.train_oos_bounds(d)
            oos_start, oos_end = bounds["OOS"]
            frames_oos.append((d, oos_start, oos_end))
            tr, cv = simulate_futures_kronos(
                d,
                sym,
                cm,
                notional_per_trade=args.notional,
                start_idx=oos_start,
                end_idx=oos_end,
                d_btc=d_btc,
            )
            all_trades.extend(tr)
            if cv:
                s = pd.Series({pt["time"]: pt["equity"] for pt in cv})
                s.index = pd.to_datetime(s.index, utc=True)
                curves.append(s.resample("1D").last().ffill())
        if not curves:
            print(f"{label}: sin datos locales para simular.")
            continue
        agg = pd.concat(curves, axis=1).ffill().fillna(47.0).sum(axis=1)
        pooled_curve = [{"time": k, "equity": float(v)} for k, v in agg.items()]
        m = metrics.compute(all_trades, pooled_curve, 47.0 * len(curves))
        rand_p95 = simulate_random_futures_baseline(frames_oos, cm, notional_per_trade=args.notional)
        print(f"\n[{label}]")
        print(f"  [Pooled Statistical Sample - Universe]")
        print(f"  {m.row()}")
        print(f"  Random Monte Carlo p95 E/trade ({args.notional:.1f} USDT) = {rand_p95:+.4f} USDT")
        print("  Pooled sample is descriptive only; it cannot pass the live gate.")

        # Live 1-position global portfolio execution metrics (matching production rule: 'Una posicion a la vez' on 47 USDT wallet)
        sorted_trades = sorted(all_trades, key=lambda x: x["entry_time"])
        live_trades = []
        free_t = None
        current_eq = 47.0
        single_curve_pts = {}
        for tr in sorted_trades:
            if free_t is None or tr["entry_time"] >= free_t:
                live_trades.append(tr)
                free_t = tr["exit_time"]
                current_eq += tr["net_pnl"]
                single_curve_pts[tr["exit_time"]] = current_eq

        if live_trades and curves:
            base_idx = curves[0].index
            s_single = pd.Series(single_curve_pts)
            s_single.index = pd.to_datetime(s_single.index, utc=True)
            s_single = s_single.reindex(base_idx.union(s_single.index)).ffill().fillna(47.0)
            single_curve = [{"time": k, "equity": float(v)} for k, v in s_single.items()]
            m_single = metrics.compute(live_trades, single_curve, 47.0)
            preliminary = gate.assess_backtest(m_single, random_p95=rand_p95, max_drawdown_pct=8.0)
            g = gate.GateResult(False, preliminary.reasons + (
                "falta simulacion cronologica event-driven de una billetera global",
            ))
            print(f"  [Proxy 1-Pos Concurrency - $47 Wallet; NO CERTIFICA REAL]")
            print(f"  {m_single.row()}")
            print(f"  Gate passed={g.passed} reasons={g.reasons}")
            sp_wins = [t for t in live_trades if t["net_pnl"] > 0]
            sp_wr = len(sp_wins) / len(live_trades) * 100.0
            sp_gw = sum(t["net_pnl"] for t in sp_wins)
            sp_gl = sum(abs(t["net_pnl"]) for t in live_trades if t["net_pnl"] <= 0)
            sp_pf = sp_gw / sp_gl if sp_gl > 0 else 999.0
            sp_net = sum(t["net_pnl"] for t in live_trades)
            print(f"  Details: N={len(live_trades)}  WR={sp_wr:5.1f}%  PF={sp_pf:4.2f}  Net={sp_net:+6.2f} USDT ({(sp_net/47.0)*100.0:+.2f}%)")


if __name__ == "__main__":
    main()
