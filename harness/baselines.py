"""Baselines: buy & hold, and random-entry Monte Carlo.

The random baseline is the key 'is there signal?' test: same sizing, same
SL/TP exits, same costs -- only the ENTRY TIMING is random. If the strategy
can't beat random entry timing on expectancy-per-trade, there is no edge.
We compare expectancy/trade (robust to trade count) and report the
strategy's percentile within the random distribution.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from harness.costs import CostModel
from harness import engine, metrics


def buy_and_hold(arr: dict, symbol: str, costs: CostModel,
                 initial_equity: float, start_idx: int, end_idx: int) -> dict:
    """Full-capital buy at start close, sell at end close, one round-trip cost."""
    close = arr["close"]
    entry_mid = close[start_idx]
    exit_mid = close[end_idx - 1]
    buy_fill = costs.fill_price(symbol, entry_mid, "BUY", initial_equity)
    qty = (initial_equity - costs.fee(initial_equity)) / buy_fill
    sell_fill = costs.fill_price(symbol, exit_mid, "SELL", qty * exit_mid)
    gross = qty * sell_fill
    final = gross - costs.fee(gross)
    # max DD of the hold
    seg = close[start_idx:end_idx]
    peak = np.maximum.accumulate(seg)
    dd = float(((peak - seg) / peak * 100.0).max())
    return {
        "final_equity": final,
        "return_pct": (final - initial_equity) / initial_equity * 100.0,
        "max_drawdown_pct": dd,
    }


def random_montecarlo(arr: dict, symbol: str, settings: dict, costs: CostModel,
                      initial_equity: float, trade_qty: float,
                      start_idx: int, end_idx: int,
                      n_target: int, runs: int = 500, seed: int = 42) -> dict:
    eligible = end_idx - start_idx
    p = min(1.0, n_target / eligible) if eligible > 0 else 0.0
    rng = np.random.default_rng(seed)
    n_bars = len(arr["close"])

    exp_per_trade = []
    net_pnls = []
    n_trades = []
    for _ in range(runs):
        draws = rng.random(n_bars)

        def decide(i, _draws=draws):
            return (_draws[i] < p), 0.0

        trades, _ = engine._simulate(
            arr, symbol, settings, costs, decide, initial_equity,
            trade_qty, start_idx, end_idx, build_curve=False)
        if trades:
            pnls = [t["net_pnl"] for t in trades]
            exp_per_trade.append(np.mean(pnls))
            net_pnls.append(sum(pnls))
            n_trades.append(len(trades))

    exp_per_trade = np.array(exp_per_trade) if exp_per_trade else np.array([0.0])
    net_pnls = np.array(net_pnls) if net_pnls else np.array([0.0])
    return {
        "p": p,
        "runs_with_trades": len(exp_per_trade),
        "avg_n_trades": float(np.mean(n_trades)) if n_trades else 0.0,
        "exp_per_trade_mean": float(exp_per_trade.mean()),
        "exp_per_trade_p50": float(np.percentile(exp_per_trade, 50)),
        "exp_per_trade_p95": float(np.percentile(exp_per_trade, 95)),
        "net_pnl_mean": float(net_pnls.mean()),
        "net_pnl_p95": float(np.percentile(net_pnls, 95)),
        "_exp_dist": exp_per_trade,
        "_net_dist": net_pnls,
    }


def percentile_of(value: float, dist: np.ndarray) -> float:
    """What fraction of the random distribution the strategy beats (0-100)."""
    if len(dist) == 0:
        return 0.0
    return float((dist < value).mean() * 100.0)
