"""Senales causales de Kronos Futures a partir de snapshots historicos completos."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

import pandas as pd

from backend.services.kronos_adapter import KronosAdapter
from backend.strategies.kronos_quant import (
    KRONOS_HORIZON_BARS, KRONOS_SAMPLE_COUNT, KronosQuantStrategy,
)
from harness.engine import DEFAULT_SETTINGS, prepare
from harness.futures_replay import Signal


PROFILE = json.loads((Path(__file__).resolve().parents[1] / "docs" / "kronos_futures_target.json").read_text(encoding="utf-8"))
if PROFILE["kronos_horizon_bars"] != KRONOS_HORIZON_BARS or PROFILE["kronos_sample_count"] != KRONOS_SAMPLE_COUNT:
    raise ValueError("perfil Kronos diverge del bot")

TARGET_SETTINGS = {
    **DEFAULT_SETTINGS,
    **{key: PROFILE[key] for key in (
        "market_type", "timeframe", "order_execution_style", "stop_loss_pct",
        "take_profit_pct", "atr_stop_mult", "atr_tp_multiplier",
        "kronos_min_ev_bps", "kronos_min_rr_ratio", "kronos_min_prob_win",
        "smart_scalper_entry_score", "max_consecutive_losses",
    )},
    "futures_allow_short": True,
    "futures_taker_fee_pct": 0.05, "paper_latency_bps": 4.0,
}


def build_signals(
    hourly_bars: Mapping[str, pd.DataFrame],
    snapshots: Mapping[tuple[pd.Timestamp, str], dict],
    adapter: KronosAdapter,
) -> dict[pd.Timestamp, list[Signal]]:
    """Cada pronostico ve solo velas cerradas; faltantes detienen el replay."""
    if not hourly_bars or not snapshots:
        raise ValueError("faltan velas o snapshots historicos de microestructura")
    strategy = KronosQuantStrategy()
    signals: dict[pd.Timestamp, list[Signal]] = {}
    for symbol in sorted(hourly_bars):
        frame = hourly_bars[symbol]
        prepared = prepare(frame, TARGET_SETTINGS)
        closes = prepared["close"].astype(float)
        returns = closes.pct_change().fillna(0.0)
        means = returns.rolling(24).mean()
        stds = returns.rolling(24).std().clip(lower=1e-6)
        ema50 = closes.ewm(span=50, adjust=False).mean()
        high36 = prepared["high"].shift(1).rolling(36).max()
        low36 = prepared["low"].shift(1).rolling(36).min()
        times = pd.to_datetime(prepared["open_time"], utc=True)
        for i in range(250, len(prepared)):
            close_time = times.iloc[i] + pd.Timedelta(hours=1)
            if close_time < pd.Timestamp("2026-07-01", tz="UTC") or close_time >= pd.Timestamp("2026-10-25", tz="UTC"):
                continue
            snapshot = snapshots.get((close_time, symbol))
            if not snapshot or "microstructure" not in snapshot or "macro_lead" not in snapshot:
                raise ValueError(f"snapshot historico incompleto: {symbol} {close_time}")
            row = prepared.iloc[i]
            price = float(row["close"])
            bar_range = float(row["high"] - row["low"])
            indicators = {
                "rsi": float(row["rsi"]), "macd_hist": float(row["macd_hist"]),
                "macd_signal": 0.0, "trend_ema": float(row["trend_ema"]),
                "fast_ema": float(row["fast_ema"]), "atr": float(row["atr"]),
                "adx": float(row["adx"]), "is_lateral": bool(row["is_lateral"]),
                "rvol": float(row["volume"] / max(row["vol_sma"], 1e-12)),
                "candle_close_pct": (price - float(row["low"])) / bar_range if bar_range > 0 else 0.5,
                "return_z_score": float((returns.iloc[i] - means.iloc[i]) / stds.iloc[i]),
                "donchian_high_36": float(high36.iloc[i]),
                "donchian_low_36": float(low36.iloc[i]), "ema_50": float(ema50.iloc[i]),
            }
            state = {
                "current_price": price, "microstructure": snapshot["microstructure"],
                "macro_lead": snapshot["macro_lead"],
            }
            if indicators["is_lateral"] or not any(strategy.classify_entry_prefilter(indicators, state).values()):
                continue
            window = frame.iloc[max(0, i - 399):i + 1].copy()
            window["timestamps"] = pd.to_datetime(window["open_time"], utc=True)
            forecast = adapter.forecast(
                window, symbol=symbol, timeframe="1h",
                horizon_bars=KRONOS_HORIZON_BARS, sample_count=KRONOS_SAMPLE_COUNT,
                tp_pct=TARGET_SETTINGS["take_profit_pct"], sl_pct=TARGET_SETTINGS["stop_loss_pct"],
            )
            if not strategy.neural_forecast_ready(
                forecast.to_dict(), symbol, "1h", int(close_time.timestamp()) - 1
            ):
                raise RuntimeError(f"Kronos neural ausente o desfasado: {symbol} {close_time}")
            state["kronos_forecast"] = forecast.to_dict()
            setup = strategy.evaluate_setup(indicators, TARGET_SETTINGS, state)
            if setup["side"] in {"LONG", "SHORT"} and setup["score"] >= TARGET_SETTINGS["smart_scalper_entry_score"]:
                signals.setdefault(close_time, []).append(Signal(
                    symbol, setup["side"], float(setup["ev_bps"]), float(row["atr"]),
                    float(setup["tp_pct"]), float(setup["sl_pct"]), indicators, TARGET_SETTINGS,
                ))
    return signals
