import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from harness.gate import assess_backtest
from harness.metrics import Metrics


def _metrics(n, expectancy, factor, drawdown):
    return Metrics(n, 50.0, factor, expectancy, 0.1, n * expectancy, 1.0,
                   drawdown, 0.0, False)


def test_gate_rejects_small_sample_even_with_positive_pnl():
    result = assess_backtest(_metrics(22, 0.001, 1.01, 3.42), random_p95=0.0)
    assert result.passed is False
    assert "menos de 30 operaciones" in result.reasons


def test_gate_requires_random_baseline():
    result = assess_backtest(_metrics(50, 0.01, 1.2, 4.0), random_p95=None)
    assert result.passed is False


def test_gate_accepts_all_conditions():
    assert assess_backtest(_metrics(50, 0.01, 1.2, 4.0), random_p95=0.005).passed


if __name__ == "__main__":
    test_gate_rejects_small_sample_even_with_positive_pnl()
    test_gate_requires_random_baseline()
    test_gate_accepts_all_conditions()
    print("gate tests ok")
