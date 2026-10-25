"""
Targeted Verification for Kronos-small Neural Forecasting on NVIDIA T1200 GPU.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend.services.kronos_adapter import KronosAdapter, KronosForecast


def generate_synthetic_candles(n: int = 60, seed: int = 123) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dt_index = pd.date_range(end=pd.Timestamp.now(tz="UTC"), periods=n, freq="15min")
    price = 150.0 * np.exp(np.cumsum(rng.normal(0, 0.002, n)))
    high = price * (1.0 + np.abs(rng.normal(0, 0.0015, n)))
    low = price * (1.0 - np.abs(rng.normal(0, 0.0015, n)))
    close = price
    open_ = np.roll(close, 1)
    open_[0] = 150.0
    vol = np.abs(rng.normal(5000, 1000, n))
    amt = close * vol

    return pd.DataFrame({
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": vol,
        "amount": amt,
        "timestamps": dt_index,
    })


def test_kronos_gpu_neural_inference():
    import torch
    assert torch.cuda.is_available(), "CUDA should be available with NVIDIA T1200"
    device_name = torch.cuda.get_device_name(0)
    print(f"\n[GPU] Active Device: {device_name}")

    df = generate_synthetic_candles(n=60, seed=777)

    # 1. Test neural inference on GPU
    adapter_gpu = KronosAdapter(
        model_id="NeoQuasar/Kronos-small",
        device="cuda:0",
        use_fp16=True,
        prefer_neural=True,
    )

    pred_gpu: KronosForecast = adapter_gpu.forecast(
        df,
        symbol="SOLUSDT",
        timeframe="15m",
        horizon_bars=12,
        sample_count=1,
        temperature=0.8,
        tp_pct=2.0,
        sl_pct=1.0,
    )

    print(f"[Neural Inference] Backend Mode: {pred_gpu.backend_mode}")
    print(f"[Neural Inference] Exp Return: {pred_gpu.expected_return_pct:+.2f}%, P_up: {pred_gpu.prob_up_net:.3f}, P_dn: {pred_gpu.prob_down_net:.3f}")
    print(f"[Neural Inference] Volatility Amp: {pred_gpu.volatility_amp:.2f}, Rank Score: {pred_gpu.rank_score:.1f}")

    assert pred_gpu.backend_mode == "kronos_hf", "Expected neural execution with Kronos model"
    assert 0.0 <= pred_gpu.prob_up_net <= 1.0
    assert 0.0 <= pred_gpu.prob_down_net <= 1.0
    assert 0.0 <= pred_gpu.rank_score <= 100.0

    # 2. Test statistical Monte Carlo fallback toggle
    adapter_mc = KronosAdapter(
        model_id="NeoQuasar/Kronos-small",
        prefer_neural=False,
    )

    pred_mc: KronosForecast = adapter_mc.forecast(
        df,
        symbol="SOLUSDT",
        timeframe="15m",
        horizon_bars=12,
        sample_count=20,
    )

    print(f"[Fallback Inference] Backend Mode: {pred_mc.backend_mode}")
    assert pred_mc.backend_mode == "monte_carlo_kline", "Expected statistical Monte Carlo fallback"
    assert 0.0 <= pred_mc.rank_score <= 100.0

    print("Kronos GPU neural + Monte Carlo fallback verification passed successfully!")


if __name__ == "__main__":
    test_kronos_gpu_neural_inference()
