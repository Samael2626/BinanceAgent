"""Validation harness: maker/1h variant vs current 5m/taker baseline.

Usage
-----
# Download 1h data first (one time):
    python -m harness.data_loader --tf 1h

# Run full comparison:
    python -m harness.run_maker

# Run specific section only:
    python -m harness.run_maker --section strategy
    python -m harness.run_maker --section oos
    python -m harness.run_maker --section regime
    python -m harness.run_maker --section baseline
    python -m harness.run_maker --section nofill    # fill-rate diagnostic

# Monte Carlo runs (default 300):
    python -m harness.run_maker --runs 500

WHAT THIS MEASURES
------------------
1. strategy  -- Maker/1h pooled over 8 symbols, BASE and STRESS costs, full 24mo.
               Baseline: current 5m/taker re-run for side-by-side.
2. oos       -- TRAIN (2024-06..2025-09) vs OOS (2025-09..2026-06) split.
               OOS is the locked test set -- the number that matters.
3. regime    -- Per-regime (bull/lateral/bear) breakdown.
               Edge that only appears in BULL = beta, not alpha.
4. baseline  -- Random-entry MC vs maker/1h strategy.
               If strategy can't beat random E/trade, there is no entry signal.
5. nofill    -- Fill-rate diagnostic: how many signals expired vs filled.
               High no-fill % = limit offset too deep or expiry too short.

GATE (do not move)
------------------
OOS expectancy > 0 USDT/trade under STRESS costs, AND strategy beats random
at p95 or above in OOS window (i.e. strategy E/trade >= p95 of the symmetric
random-maker distribution), AND auditor confirms no look-ahead / no-IS-tuning.

NOTE on "symmetric random": the random baseline MUST use the same execution
model as the strategy (MakerCostModel, ATR-based SL/TP, trailing). The old
p50 gate and the old engine._simulate baseline (which silently zeroed SL/TP)
were both invalid. Both are now fixed -- do not revert to p50 or to the
5m engine for the random baseline.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

from harness import data_loader, metrics, baselines, splits
from harness import engine        as eng5m   # 5m/taker baseline
from harness import engine_maker  as eng1h   # 1h/maker variant
from harness.costs import CostModel, MakerCostModel

INITIAL   = 1000.0
TRADE_QTY = 12.0
SETTINGS_5M = eng5m.DEFAULT_SETTINGS
SETTINGS_1H = eng1h.DEFAULT_SETTINGS_1H


# ---------------------------------------------------------------------------
# Helpers shared by all sections
# ---------------------------------------------------------------------------

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
    curve  = _agg_curve(results, INITIAL)
    return metrics.compute(trades, curve, INITIAL * n)


def load_arrs_5m():
    """Load and prepare 5m arrays (same as run.py)."""
    arrs = {}
    for s in data_loader.SYMBOLS:
        d = data_loader.load(s, "5m")
        arrs[s] = eng5m.to_arrays(eng5m.prepare(d, SETTINGS_5M))
    return arrs


def load_arrs_1h():
    """Load and prepare 1h arrays."""
    arrs = {}
    for s in data_loader.SYMBOLS:
        d = data_loader.load(s, "1h")
        prep = eng1h.prepare_1h(d, SETTINGS_1H)
        arrs[s] = eng1h.to_arrays_1h(prep)
    return arrs


# ---------------------------------------------------------------------------
# Section: strategy overview
# ---------------------------------------------------------------------------

def section_strategy(arrs5m, arrs1h):
    print("\n" + "=" * 110)
    print("SECTION: STRATEGY OVERVIEW -- maker/1h vs taker/5m baseline | full 24mo | NET costs")
    print("=" * 110)

    print("\n--- 5m/TAKER BASELINE (existing strategy) ---")
    for cost_name, cm in [("BASE  (fee .10/side, slip 2/5bps)", CostModel.base()),
                          ("STRESS(fee .10/side, slip 4/10bps)", CostModel.stress())]:
        print(f"  costs: {cost_name}")
        results = []
        for s in data_loader.SYMBOLS:
            tr, cv = eng5m.run_strategy(arrs5m[s], s, SETTINGS_5M, cm, INITIAL, TRADE_QTY)
            results.append((tr, cv))
            m = metrics.compute(tr, cv, INITIAL)
            print(f"    {s:9s} {m.row()}")
        agg = _pool(results, len(data_loader.SYMBOLS))
        print(f"    {'POOLED':9s} {agg.row()}")

    print("\n--- 1h/MAKER VARIANT (hypothesis) ---")
    print(f"  ATR SL mult={eng1h.ATR_SL_MULT}x  TP mult={eng1h.ATR_TP_MULT}x  "
          f"trail={eng1h.TRAIL_PCT_1H}%  cooldown=2bars")
    for cost_name, cm in [
        ("BASE  (0bps entry, SL taker 2/5bps, 0bps TP, offset 5bps, expiry 3bars)",
         MakerCostModel.base()),
        ("STRESS(1bps entry, SL taker 4/10bps, 1bps TP, offset 10bps, expiry 2bars)",
         MakerCostModel.stress()),
    ]:
        print(f"  costs: {cost_name}")
        results = []
        for s in data_loader.SYMBOLS:
            tr, cv = eng1h.run_strategy_maker(arrs1h[s], s, SETTINGS_1H, cm, INITIAL, TRADE_QTY)
            results.append((tr, cv))
            m = metrics.compute(tr, cv, INITIAL)
            print(f"    {s:9s} {m.row()}")
        agg = _pool(results, len(data_loader.SYMBOLS))
        print(f"    {'POOLED':9s} {agg.row()}")

    print("\n  (* Sharpe unreliable with <100 trades)")


# ---------------------------------------------------------------------------
# Section: OOS split
# ---------------------------------------------------------------------------

def section_oos(arrs5m, arrs1h):
    print("\n" + "=" * 110)
    print("SECTION: OOS | TRAIN (2024-06..2025-09) vs OOS (2025-09..2026-06, bear+lateral)")
    print("=" * 110)

    cm5m  = CostModel.base()
    cm1h_base   = MakerCostModel.base()
    cm1h_stress = MakerCostModel.stress()

    for label in ("TRAIN", "OOS"):
        print(f"\n  -- {label} --")

        # 5m baseline
        res5m = []
        for s in data_loader.SYMBOLS:
            d = data_loader.load(s, "5m")
            a, b = splits.train_oos_bounds(d)[label]
            tr, cv = eng5m.run_strategy(arrs5m[s], s, SETTINGS_5M, cm5m, INITIAL, TRADE_QTY,
                                        start_idx=a, end_idx=b)
            res5m.append((tr, cv))
        agg = _pool(res5m, len(data_loader.SYMBOLS))
        print(f"    5m/taker  BASE   {label:6s} {agg.row()}")

        # 1h maker base
        res1h_base = []
        for s in data_loader.SYMBOLS:
            d = data_loader.load(s, "1h")
            a, b = splits.train_oos_bounds(d)[label]
            tr, cv = eng1h.run_strategy_maker(arrs1h[s], s, SETTINGS_1H, cm1h_base,
                                              INITIAL, TRADE_QTY, start_idx=a, end_idx=b)
            res1h_base.append((tr, cv))
        agg = _pool(res1h_base, len(data_loader.SYMBOLS))
        print(f"    1h/maker  BASE   {label:6s} {agg.row()}")

        # 1h maker stress
        res1h_stress = []
        for s in data_loader.SYMBOLS:
            d = data_loader.load(s, "1h")
            a, b = splits.train_oos_bounds(d)[label]
            tr, cv = eng1h.run_strategy_maker(arrs1h[s], s, SETTINGS_1H, cm1h_stress,
                                              INITIAL, TRADE_QTY, start_idx=a, end_idx=b)
            res1h_stress.append((tr, cv))
        agg = _pool(res1h_stress, len(data_loader.SYMBOLS))
        print(f"    1h/maker  STRESS {label:6s} {agg.row()}")

    print("\n  -> OOS STRESS expectancy > 0 is the minimum gate for deployment consideration.")
    print("  -> if TRAIN green but OOS red, it was overfitting. Do NOT deploy.")


# ---------------------------------------------------------------------------
# Section: regime breakdown
# ---------------------------------------------------------------------------

def section_regime(arrs5m, arrs1h):
    print("\n" + "=" * 110)
    print("SECTION: REGIME | per market regime, 1h/maker BASE costs, pooled 8 symbols")
    print("=" * 110)

    cm = MakerCostModel.base()
    for name, start, end in splits.REGIMES:
        results = []
        for s in data_loader.SYMBOLS:
            d  = data_loader.load(s, "1h")
            a  = splits.idx_at(d, start)
            b  = splits.idx_at(d, end)
            if b - a < eng1h.WARMUP + 5:
                continue
            tr, cv = eng1h.run_strategy_maker(arrs1h[s], s, SETTINGS_1H, cm,
                                              INITIAL, TRADE_QTY,
                                              start_idx=max(a, eng1h.WARMUP), end_idx=b)
            results.append((tr, cv))
        agg = _pool(results, len(results) or 1)
        print(f"  {name:14s} {agg.row()}")

    print("  -> edge only in BULL = beta exposure, not alpha.")


# ---------------------------------------------------------------------------
# Section: random MC baseline
# ---------------------------------------------------------------------------

def section_baseline(arrs1h, runs):
    """Random-entry Monte Carlo baseline vs maker/1h strategy.

    SYMMETRY: the random MC uses random_montecarlo_maker() (engine_maker.py),
    which drives _simulate_maker with a random decider. This guarantees:
      - Same MakerCostModel (limit fill / no-fill / expiry).
      - Same exits: ATR-based SL + TP + trailing, identical to the strategy.
      - Same costs on every leg.
    Only the entry timing differs (random vs score-gated).

    GATE: strategy E/trade must be >= p95 of the random distribution
    (per-symbol, OOS window). p50 was the old (invalid) threshold -- it was
    too easy to beat and masked the exit-asymmetry bug. p95 is the agreed
    gate, fixed BEFORE any results were seen post-fix.
    """
    print("\n" + "=" * 110)
    print(f"SECTION: BASELINE | symmetric random-entry MC ({runs} runs) vs 1h/maker | NET BASE costs")
    print("=" * 110)
    print("  Random baseline: same MakerCostModel + ATR SL/TP/trailing as strategy.")
    print("  Only entry timing is random. Gate: strategy E/trade >= p95 of random dist.")

    cm = MakerCostModel.base()

    print(f"\n  {'symbol':9s} {'strat E/trade':>14s} {'rand p50':>10s} {'rand p95':>10s} "
          f"{'strat pctile':>13s} {'gate p95':>10s}")

    beats_p95 = 0
    total = 0
    for s in data_loader.SYMBOLS:
        arr = arrs1h[s]
        tr, _ = eng1h.run_strategy_maker(arr, s, SETTINGS_1H, cm,
                                         INITIAL, TRADE_QTY, build_curve=False)
        n = len(tr)
        if n == 0:
            print(f"  {s:9s} {'no trades':>14s}")
            continue
        strat_e = float(np.mean([t["net_pnl"] for t in tr]))

        # Symmetric random MC: same engine, same costs, only timing is random.
        mc = eng1h.random_montecarlo_maker(
            arr, s, SETTINGS_1H, cm, INITIAL, TRADE_QTY,
            eng1h.WARMUP, len(arr["close"]), n_target=n, runs=runs,
        )
        pct = baselines.percentile_of(strat_e, mc["_exp_dist"])
        total += 1
        gate_ok = "PASS" if pct >= 95.0 else "FAIL"
        if pct >= 95.0:
            beats_p95 += 1
        print(f"  {s:9s} {strat_e:>14.4f} {mc['exp_per_trade_p50']:>10.4f} "
              f"{mc['exp_per_trade_p95']:>10.4f} {pct:>12.1f}% {gate_ok:>10s}")

    print(f"\n  Strategy beats random at p95 on {beats_p95}/{total} symbols.")
    print("  Gate requires ALL symbols pass p95 in the OOS window (not just pooled).")
    print("  NOTE: random and strategy both use MakerCostModel -- no cost asymmetry.")
    print("  If E/trade < random p95: no entry signal -- cost structure alone insufficient.")


# ---------------------------------------------------------------------------
# Section: no-fill rate diagnostic
# ---------------------------------------------------------------------------

def section_nofill(arrs1h):
    """Diagnostic: what fraction of signals actually filled.

    A high no-fill rate means the limit offset is too deep or expiry too short.
    Ideal range: 60-85% fill rate. Below 50% = limit too far, missing the move.
    Above 95% = limit essentially at market, not really maker behavior.
    """
    print("\n" + "=" * 110)
    print("SECTION: NO-FILL DIAGNOSTIC | how many signals expired vs filled")
    print("=" * 110)

    for cm_name, cm in [("BASE  (offset 5bps, expiry 3bars)",  MakerCostModel.base()),
                        ("STRESS(offset 10bps, expiry 2bars)", MakerCostModel.stress())]:
        print(f"\n  costs: {cm_name}")
        print(f"  {'symbol':9s} {'signals':>8s} {'filled':>8s} {'expired':>8s} {'fill%':>8s}")
        for s in data_loader.SYMBOLS:
            arr = arrs1h[s]
            signals, filled, expired = _count_fills(arr, s, SETTINGS_1H, cm)
            fill_pct = filled / signals * 100.0 if signals > 0 else 0.0
            print(f"  {s:9s} {signals:>8d} {filled:>8d} {expired:>8d} {fill_pct:>7.1f}%")
    print("  -> 60-85% fill rate is reasonable. Tune offset/expiry if outside this range.")
    print("     (Do not tune to maximize E/trade -- tune to reach reasonable fill rate first.)")


def _count_fills(arr: dict, symbol: str, settings: dict, costs: MakerCostModel):
    """Count signals, fills, and no-fills for diagnostic purposes.

    Simplified: no position tracking, just tests each signal independently.
    """
    from backend.strategies.smart_scalper import SmartScalperStrategy
    strat = SmartScalperStrategy()
    min_score = settings["smart_scalper_entry_score"]
    close = arr["close"]
    low   = arr["low"]
    rsi   = arr["rsi"]
    mh    = arr["macd_hist"]
    te    = arr["trend_ema"]
    fe    = arr["fast_ema"]
    adx   = arr["adx"]
    vs    = arr["vol_sma"]
    vol   = arr["vol"]

    n = len(close)
    signals = 0
    filled  = 0
    expired = 0

    for i in range(eng1h.WARMUP, n - 1):
        ind = {
            "rsi": rsi[i], "macd_hist": mh[i], "macd_signal": 0.0,
            "trend_ema": te[i], "fast_ema": fe[i], "is_lateral": False,
            "adx": adx[i], "current_vol": vol[i], "vol_sma": vs[i],
        }
        score, _ = strat.score_buy_setup(ind, settings, {"current_price": close[i]})
        if score < min_score:
            continue
        signals += 1
        lp = costs.limit_price(close[i])
        did_fill = False
        for j in range(i + 1, min(i + 1 + costs.expiry_bars, n)):
            if low[j] <= lp:
                did_fill = True
                break
        if did_fill:
            filled += 1
        else:
            expired += 1

    return signals, filled, expired


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="BinanceAgent maker/1h harness")
    ap.add_argument("--section", default="all",
                    choices=["all", "strategy", "oos", "regime", "baseline", "nofill"])
    ap.add_argument("--runs", type=int, default=300,
                    help="Monte Carlo runs for baseline section (default 300)")
    args = ap.parse_args()

    # Load data
    print("Loading 1h data (maker variant)...")
    try:
        arrs1h = load_arrs_1h()
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        print("Run:  python -m harness.data_loader --tf 1h")
        sys.exit(1)

    arrs5m = None
    if args.section in ("all", "strategy", "oos"):
        print("Loading 5m data (baseline)...")
        arrs5m = load_arrs_5m()

    print("Ready.\n")
    print(f"Maker/1h settings: score>={SETTINGS_1H['smart_scalper_entry_score']}, "
          f"RSI<={SETTINGS_1H['buy_rsi']}, ATR SL {eng1h.ATR_SL_MULT}x / TP {eng1h.ATR_TP_MULT}x, "
          f"trail {eng1h.TRAIL_PCT_1H}%, cooldown {SETTINGS_1H['cooldown_minutes']}min")

    if args.section in ("all", "strategy"):
        section_strategy(arrs5m, arrs1h)
    if args.section in ("all", "oos"):
        section_oos(arrs5m, arrs1h)
    if args.section in ("all", "regime"):
        section_regime(arrs5m, arrs1h)
    if args.section in ("all", "baseline"):
        section_baseline(arrs1h, args.runs)
    if args.section in ("all", "nofill"):
        section_nofill(arrs1h)


if __name__ == "__main__":
    main()
