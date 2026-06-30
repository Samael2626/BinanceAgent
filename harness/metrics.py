"""Performance metrics. All computed on NET pnl (after fees + slippage).

Definitions / math:
  expectancy_usdt   = mean(net_pnl per trade)                       # the target
  expectancy_pct    = mean(net_return_pct per trade)
  profit_factor     = sum(wins) / |sum(losses)|                     # >1 = edge
  win_rate          = #wins / #trades                               # secondary
  max_drawdown_pct  = max peak-to-trough of mark-to-market equity
  sharpe            = mean(daily_ret) / std(daily_ret) * sqrt(365)  # crypto = 365d
                      (reliable only with a meaningful sample; flagged < 100 trades)
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import pandas as pd


@dataclass
class Metrics:
    n_trades: int
    win_rate: float
    profit_factor: float
    expectancy_usdt: float
    expectancy_pct: float
    net_pnl: float
    return_pct: float
    max_drawdown_pct: float
    sharpe: float
    sharpe_reliable: bool

    def row(self) -> str:
        flag = "" if self.sharpe_reliable else "*"
        return (f"N={self.n_trades:<5d} WR={self.win_rate:5.1f}%  PF={self.profit_factor:5.2f}  "
                f"E/trade={self.expectancy_usdt:+7.3f}USDT ({self.expectancy_pct:+5.2f}%)  "
                f"net={self.net_pnl:+9.2f}  ret={self.return_pct:+7.2f}%  "
                f"maxDD={self.max_drawdown_pct:5.2f}%  Sharpe={self.sharpe:+5.2f}{flag}")


def compute(trades: list[dict], equity_curve: list[dict], initial_equity: float) -> Metrics:
    n = len(trades)
    if n == 0:
        return Metrics(0, 0, 0, 0, 0, 0, 0, 0, 0.0, False)

    pnls = [t["net_pnl"] for t in trades]
    rets = [t["net_return_pct"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    pf = (gross_win / gross_loss) if gross_loss > 0 else float("inf")

    net_pnl = sum(pnls)
    ret_pct = (net_pnl / initial_equity * 100.0) if initial_equity > 0 else 0.0

    # max drawdown on mark-to-market equity curve
    peak = initial_equity
    max_dd = 0.0
    for pt in equity_curve:
        eq = pt["equity"]
        peak = max(peak, eq)
        dd = (peak - eq) / peak * 100.0 if peak > 0 else 0.0
        max_dd = max(max_dd, dd)

    # Sharpe from daily-resampled equity returns
    sharpe = 0.0
    if equity_curve:
        s = pd.Series({pt["time"]: pt["equity"] for pt in equity_curve})
        s.index = pd.to_datetime(s.index, utc=True)
        daily = s.resample("1D").last().ffill()
        dret = daily.pct_change().dropna()
        if len(dret) > 2 and dret.std() > 0:
            sharpe = float(dret.mean() / dret.std() * math.sqrt(365))

    return Metrics(
        n_trades=n,
        win_rate=len(wins) / n * 100.0,
        profit_factor=round(pf, 3) if pf != float("inf") else float("inf"),
        expectancy_usdt=sum(pnls) / n,
        expectancy_pct=sum(rets) / n,
        net_pnl=net_pnl,
        return_pct=ret_pct,
        max_drawdown_pct=max_dd,
        sharpe=sharpe,
        sharpe_reliable=(n >= 100),
    )
