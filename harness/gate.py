"""Criterios fijos antes de examinar el periodo reservado."""

from __future__ import annotations

from dataclasses import dataclass

from harness.metrics import Metrics


@dataclass(frozen=True)
class GateResult:
    passed: bool
    reasons: tuple[str, ...]


def assess_backtest(result: Metrics, random_p95: float | None,
                    max_drawdown_pct: float = 8.0) -> GateResult:
    reasons = []
    if result.n_trades < 30:
        reasons.append("menos de 30 operaciones")
    if result.expectancy_usdt <= 0:
        reasons.append("expectativa neta no positiva")
    if result.profit_factor <= 1:
        reasons.append("factor de beneficio no superior a 1")
    if result.max_drawdown_pct > max_drawdown_pct:
        reasons.append("caida maxima superior al limite")
    if random_p95 is None:
        reasons.append("comparacion aleatoria p95 pendiente")
    elif result.expectancy_usdt <= random_p95:
        reasons.append("no supera el percentil 95 aleatorio")
    return GateResult(not reasons, tuple(reasons))
