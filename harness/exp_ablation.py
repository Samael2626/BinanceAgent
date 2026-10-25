"""Ablation experiment: is the no-edge caused by 'too many sensors' or is it STRUCTURAL?

Progressively strip sensors off the ENTRY only. Exits/SL/TP/trailing/cooldown/sizing/
costs/symbols/OOS held IDENTICAL across all 4 configs. We change ONLY entry_decider.

Configs (rules fixed BEFORE running, no threshold tuning to force a cross):
  1. RSI-only      : rsi <= buy_rsi+4              (raw oversold incl. near-zone)
  2. RSI+MACD      : (1) AND macd_hist > 0
  3. RSI+MACD+ADX  : (2) AND adx >= 20
  4. FULL (actual) : score_buy_setup(...) >= smart_scalper_entry_score (52)

All inherit the lateral gate (same as production: lateral blocks entry).

VERDICT CRITERION (fixed before results):
  VERDE = expectancy_usdt NET > 0 in OOS (2025-09-23 -> end) under stress slippage,
          pooled 8 symbols. Real edge requires also beating random p95 while random
          itself is not positive.

Run: PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m harness.exp_ablation
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from harness import data_loader, engine, metrics, baselines, splits
from harness.costs import CostModel

COSTS = CostModel.stress()           # ADVERSE: stress slippage, the gate requirement
SY = data_loader.SYMBOLS
SETTINGS = dict(engine.DEFAULT_SETTINGS)   # SL1.5 TP1.5 trail0.8 cooldown3 — held constant
INIT_EQ = 1000.0
TRADE_QTY = 12.0


def make_decider(arr: dict, kind: str):
    """Return entry_decider(i)->(ok, score). Lateral gate applied to all (like prod)."""
    rsi, mh, adx = arr["rsi"], arr["macd_hist"], arr["adx"]
    lat = arr["is_lateral"]
    buy_rsi = float(SETTINGS["buy_rsi"])          # 38.0
    zone = buy_rsi + 4.0                          # near-zone, mirrors real scorer

    if kind == "full":
        return engine.strategy_decider(arr, SETTINGS)

    def decide(i):
        if lat[i]:
            return False, 0.0
        if rsi[i] > zone:
            return False, 0.0
        if kind == "rsi":
            return True, float(rsi[i])
        if mh[i] <= 0:
            return False, 0.0
        if kind == "rsi_macd":
            return True, float(rsi[i])
        # rsi_macd_adx
        if adx[i] < 20.0:
            return False, 0.0
        return True, float(rsi[i])

    return decide


def pooled_oos(kind: str):
    """Run one ablation pooled over 8 symbols on the OOS slice. Returns (metrics, trades, per_sym_n)."""
    all_trades = []
    series = []
    n_eligible_total = 0
    for s in SY:
        d = engine.prepare(data_loader.load(s), SETTINGS)
        arr = engine.to_arrays(d)
        bounds = splits.train_oos_bounds(d)
        oos_start, oos_end = bounds["OOS"]
        oos_start = max(oos_start, engine.WARMUP)
        decider = make_decider(arr, kind)
        trades, curve = engine._simulate(
            arr, s, SETTINGS, COSTS, decider, INIT_EQ, TRADE_QTY,
            oos_start, oos_end, build_curve=True)
        all_trades.extend(trades)
        n_eligible_total += (oos_end - oos_start)
        if curve:
            sx = pd.Series({p["time"]: p["equity"] for p in curve})
            sx.index = pd.to_datetime(sx.index, utc=True)
            series.append(sx.resample("1D").last().ffill())
    if series:
        agg = pd.concat(series, axis=1).ffill().fillna(INIT_EQ).sum(axis=1)
        curve = [{"time": t, "equity": float(v)} for t, v in agg.items()]
    else:
        curve = []
    m = metrics.compute(all_trades, curve, INIT_EQ * len(SY))
    return m, all_trades, n_eligible_total


def random_oos(n_target_per_sym: float):
    """Symmetric random baseline: SAME settings (SL/TP/trail), SAME stress costs,
    SAME OOS slice. Only entry timing random. Pooled exp/trade distribution."""
    exp_dist = []
    for s in SY:
        d = engine.prepare(data_loader.load(s), SETTINGS)
        arr = engine.to_arrays(d)
        bounds = splits.train_oos_bounds(d)
        oos_start, oos_end = bounds["OOS"]
        oos_start = max(oos_start, engine.WARMUP)
        r = baselines.random_montecarlo(
            arr, s, SETTINGS, COSTS, INIT_EQ, TRADE_QTY,
            oos_start, oos_end, n_target=int(n_target_per_sym), runs=300, seed=42)
        if len(r["_exp_dist"]):
            exp_dist.append(r["_exp_dist"])
    # pool: stack per-symbol run means weighted equally -> overall random exp/trade dist
    if not exp_dist:
        return np.array([0.0])
    minlen = min(len(x) for x in exp_dist)
    stacked = np.vstack([x[:minlen] for x in exp_dist])  # (n_sym, runs)
    return stacked.mean(axis=0)  # avg exp/trade across symbols per run


def main():
    print("=" * 110)
    print("ABLATION — OOS (2025-09-23 -> end), STRESS slippage (4/10 bps), pooled 8 symbols")
    print(f"Held constant: SL={SETTINGS['stop_loss_pct']} TP={SETTINGS['take_profit_pct']} "
          f"trail={SETTINGS['rsi_trailing_pct']} cooldown={SETTINGS['cooldown_minutes']}m qty={TRADE_QTY}")
    print(f"Symbols: {SY}")
    print("=" * 110)

    configs = [
        ("1) RSI-only      (rsi<=42)",        "rsi"),
        ("2) RSI+MACD      (+ hist>0)",       "rsi_macd"),
        ("3) RSI+MACD+ADX  (+ adx>=20)",      "rsi_macd_adx"),
        ("4) FULL actual   (score>=52)",      "full"),
    ]

    rows = []
    for label, kind in configs:
        m, trades, n_elig = pooled_oos(kind)
        rows.append((label, kind, m, len(trades)))
        print(f"\n{label}")
        print(f"   {m.row()}")

    print("\n" + "=" * 110)
    print("vs SYMMETRIC RANDOM (same SL/TP/trail/stress-costs, random entry timing):")
    print("=" * 110)
    for label, kind, m, n in rows:
        if n == 0:
            print(f"{label:32s}  N=0  -> no trades, skip random")
            continue
        avg_n_per_sym = max(1.0, n / len(SY))
        rdist = random_oos(avg_n_per_sym)
        pct = baselines.percentile_of(m.expectancy_usdt, rdist)
        rmean = float(rdist.mean())
        rp95 = float(np.percentile(rdist, 95))
        beats_p95 = m.expectancy_usdt > rp95
        rand_positive = rmean > 0
        print(f"{label:32s}  strat E/trade={m.expectancy_usdt:+7.4f}  "
              f"random mean={rmean:+7.4f} p95={rp95:+7.4f}  "
              f"pct={pct:5.1f}%  beats_p95={beats_p95}  rand_positive={rand_positive}")

    print("\n" + "=" * 110)
    print("VERDICT: any config with expectancy_usdt NET > 0 in OOS+stress?")
    print("=" * 110)
    any_green = False
    for label, kind, m, n in rows:
        green = m.expectancy_usdt > 0 and n > 0
        any_green = any_green or green
        tag = "VERDE" if green else "rojo "
        print(f"   [{tag}] {label:32s}  E/trade={m.expectancy_usdt:+7.4f} USDT  N={n}")
    print()
    if any_green:
        print(">> At least one config crosses. Sensor-calibration hypothesis NOT dead — check vs random.")
    else:
        print(">> NONE crosses E/trade>0. Hypothesis 'too many sensors' is DEAD.")
        print(">> Cause is STRUCTURAL: the raw RSI-dip signal has no gross edge; costs bury it.")


if __name__ == "__main__":
    main()
