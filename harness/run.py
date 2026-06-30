"""Validation harness orchestrator.

Sections:
  strategy  -> current strategy, full 24mo, per-symbol + aggregate (base + stress costs)
  oos       -> TRAIN vs OUT-OF-SAMPLE side by side
  regime    -> per market regime (bull/lateral/bear)
  baseline  -> buy&hold + random Monte Carlo (is there signal vs random?)

Usage: python -m harness.run [--section all|strategy|oos|regime|baseline] [--runs 300]
All metrics are NET of fees (0.10%/side) + slippage. Honest by construction.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

from harness import data_loader, engine, metrics, baselines, splits
from harness.costs import CostModel

INITIAL = 1000.0
TRADE_QTY = 12.0
SETTINGS = engine.DEFAULT_SETTINGS


def _agg_curve(results, initial_per):
    series = []
    for _, curve in results:
        if not curve:
            continue
        s = pd.Series({pt["time"]: pt["equity"] for pt in curve})
        s.index = pd.to_datetime(s.index, utc=True)
        series.append(s.resample("1D").last().ffill())
    if not series:
        return []
    agg = pd.concat(series, axis=1).ffill().fillna(initial_per).sum(axis=1)
    return [{"time": t, "equity": float(v)} for t, v in agg.items()]


def _pool(results, n):
    trades = [t for tr, _ in results for t in tr]
    curve = _agg_curve(results, INITIAL)
    return metrics.compute(trades, curve, INITIAL * n)


def load_arrays():
    arrs = {}
    for s in data_loader.SYMBOLS:
        d = engine.prepare(data_loader.load(s), SETTINGS)
        arrs[s] = engine.to_arrays(d)
    return arrs


def section_strategy(arrs):
    print("\n" + "=" * 100)
    print("STRATEGY (current smart_scalper, 52/28, filters off) | full 24mo | NET of fees+slippage")
    print("=" * 100)
    for cost_name, cm in [("BASE  (fee .10/side, slip 2/5bps)", CostModel.base()),
                          ("STRESS(fee .10/side, slip 4/10bps)", CostModel.stress())]:
        print(f"\n--- costs: {cost_name} ---")
        results = []
        for s in data_loader.SYMBOLS:
            tr, cv = engine.run_strategy(arrs[s], s, SETTINGS, cm, INITIAL, TRADE_QTY)
            results.append((tr, cv))
            m = metrics.compute(tr, cv, INITIAL)
            print(f"  {s:9s} {m.row()}")
        agg = _pool(results, len(data_loader.SYMBOLS))
        print(f"  {'POOLED':9s} {agg.row()}")
    print("\n  (* Sharpe unreliable with <100 trades)")


def section_oos(arrs):
    print("\n" + "=" * 100)
    print("OUT-OF-SAMPLE | TRAIN (2024-06..2025-09, bull+lateral) vs OOS (2025-09..2026-06, bear+lateral)")
    print("=" * 100)
    cm = CostModel.base()
    for label in ("TRAIN", "OOS"):
        results = []
        for s in data_loader.SYMBOLS:
            d = data_loader.load(s)
            a, b = splits.train_oos_bounds(d)[label]
            tr, cv = engine.run_strategy(arrs[s], s, SETTINGS, cm, INITIAL, TRADE_QTY,
                                         start_idx=a, end_idx=b)
            results.append((tr, cv))
        agg = _pool(results, len(data_loader.SYMBOLS))
        print(f"  {label:6s} {agg.row()}")
    print("  -> if edge is positive in TRAIN but dies in OOS, it was overfitting.")


def section_regime(arrs):
    print("\n" + "=" * 100)
    print("WALK-FORWARD BY REGIME | pooled across 8 symbols | NET base costs")
    print("=" * 100)
    cm = CostModel.base()
    for name, start, end in splits.REGIMES:
        results = []
        for s in data_loader.SYMBOLS:
            d = data_loader.load(s)
            a, b = splits.idx_at(d, start), splits.idx_at(d, end)
            if b - a < engine.WARMUP + 10:
                continue
            tr, cv = engine.run_strategy(arrs[s], s, SETTINGS, cm, INITIAL, TRADE_QTY,
                                         start_idx=max(a, engine.WARMUP), end_idx=b)
            results.append((tr, cv))
        agg = _pool(results, len(results) or 1)
        print(f"  {name:14s} {agg.row()}")
    print("  -> a strategy that only wins in BULL has beta, not edge.")


def section_baseline(arrs, runs):
    print("\n" + "=" * 100)
    print(f"BASELINES | buy&hold vs random-entry Monte Carlo ({runs} runs) | NET base costs")
    print("=" * 100)
    cm = CostModel.base()
    print(f"\n  {'symbol':9s} {'strat E/trade':>14s} {'rand E/trade p50':>17s} {'rand p95':>10s} "
          f"{'strat pctile':>13s} {'buy&hold ret%':>14s}")
    beats = 0
    total = 0
    for s in data_loader.SYMBOLS:
        d = data_loader.load(s)
        tr, _ = engine.run_strategy(arrs[s], s, SETTINGS, cm, INITIAL, TRADE_QTY, build_curve=False)
        n = len(tr)
        if n == 0:
            print(f"  {s:9s} {'no trades':>14s}")
            continue
        strat_e = float(np.mean([t["net_pnl"] for t in tr]))
        bh = baselines.buy_and_hold(arrs[s], s, cm, INITIAL, engine.WARMUP, len(d))
        mc = baselines.random_montecarlo(arrs[s], s, SETTINGS, cm, INITIAL, TRADE_QTY,
                                         engine.WARMUP, len(d), n_target=n, runs=runs)
        pct = baselines.percentile_of(strat_e, mc["_exp_dist"])
        total += 1
        if pct >= 50:
            beats += 1
        print(f"  {s:9s} {strat_e:>14.4f} {mc['exp_per_trade_p50']:>17.4f} "
              f"{mc['exp_per_trade_p95']:>10.4f} {pct:>12.1f}% {bh['return_pct']:>13.2f}%")
    print(f"\n  Strategy beats random-median on {beats}/{total} symbols.")
    print("  -> if it can't beat random with the same risk, there is no entry signal.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--section", default="all",
                    choices=["all", "strategy", "oos", "regime", "baseline"])
    ap.add_argument("--runs", type=int, default=300)
    args = ap.parse_args()

    print("Loading + preparing indicators for 8 symbols (24mo 5m)...")
    arrs = load_arrays()
    print("Ready.")

    if args.section in ("all", "strategy"):
        section_strategy(arrs)
    if args.section in ("all", "oos"):
        section_oos(arrs)
    if args.section in ("all", "regime"):
        section_regime(arrs)
    if args.section in ("all", "baseline"):
        section_baseline(arrs, args.runs)


if __name__ == "__main__":
    main()
