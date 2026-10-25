"""
Kronos Foundation Model Adapter (`shiyu-coder/Kronos` / `NeoQuasar/Kronos-*`).

Provides probabilistic multi-step K-line (OHLCV + Amount) forecasting and
cross-sectional RankIC scoring for Spot and USDⓈ-M Futures.

Supported Hugging Face checkpoints:
  - NeoQuasar/Kronos-mini  (4.1M params,  tokenizer: NeoQuasar/Kronos-Tokenizer-2k,   max_context=2048)
  - NeoQuasar/Kronos-small (24.7M params, tokenizer: NeoQuasar/Kronos-Tokenizer-base, max_context=512) [DEFAULT]
  - NeoQuasar/Kronos-base  (102.3M params, tokenizer: NeoQuasar/Kronos-Tokenizer-base, max_context=512)

Execution contract:
  1. Only runs on CLOSED candles; caches forecasts keyed by (symbol, timeframe, last_open_time, model_id).
  2. Generates N Monte Carlo trajectories over horizon H bars to estimate:
     - Expected & median return (%)
     - First-passage probability of hitting Take Profit before Stop Loss for LONG (`prob_up_net`)
       and SHORT (`prob_down_net`)
     - Predicted volatility amplification (`volatility_amp = predicted_atr / realized_atr`)
     - Cross-sectional `rank_score` (0..100) for autonomous scanner asset selection.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import logging
import threading
from typing import Any, Callable

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


KRONOS_MODEL_REGISTRY: dict[str, dict[str, Any]] = {
    "NeoQuasar/Kronos-mini": {
        "tokenizer": "NeoQuasar/Kronos-Tokenizer-2k",
        "max_context": 2048,
        "params_m": 4.1,
    },
    "NeoQuasar/Kronos-small": {
        "tokenizer": "NeoQuasar/Kronos-Tokenizer-base",
        "max_context": 512,
        "params_m": 24.7,
    },
    "NeoQuasar/Kronos-base": {
        "tokenizer": "NeoQuasar/Kronos-Tokenizer-base",
        "max_context": 512,
        "params_m": 102.3,
    },
}

DEFAULT_KRONOS_MODEL = "NeoQuasar/Kronos-small"


@dataclass(frozen=True)
class KronosForecast:
    symbol: str
    timeframe: str
    model_id: str
    backend_mode: str  # "kronos_hf" | "monte_carlo_kline"
    last_candle_ts: int
    horizon_bars: int
    sample_count: int
    current_price: float
    expected_return_pct: float
    median_return_pct: float
    upside_p90_pct: float
    downside_p10_pct: float
    prob_up_net: float
    prob_down_net: float
    volatility_amp: float
    predicted_atr_pct: float
    rank_score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def prepare_kronos_dataframe(df: pd.DataFrame, max_lookback: int = 400) -> pd.DataFrame:
    """
    Normalizes a klines DataFrame into the exact schema required by Kronos:
    columns: ['open', 'high', 'low', 'close', 'volume', 'amount', 'timestamps']
    """
    if df is None or df.empty:
        raise ValueError("klines dataframe is empty")

    required = {"open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"klines dataframe missing required columns: {sorted(missing)}")

    work = df.tail(max(int(max_lookback), 30)).copy().reset_index(drop=True)
    for col in ("open", "high", "low", "close", "volume"):
        work[col] = pd.to_numeric(work[col], errors="coerce").astype(float)

    if "amount" in work.columns:
        work["amount"] = pd.to_numeric(work["amount"], errors="coerce").astype(float)
    elif "quote_asset_volume" in work.columns:
        work["amount"] = pd.to_numeric(work["quote_asset_volume"], errors="coerce").astype(float)
    else:
        typical_price = (work["open"] + work["high"] + work["low"] + work["close"]) / 4.0
        work["amount"] = typical_price * work["volume"]

    if "timestamps" in work.columns:
        ts = pd.to_datetime(work["timestamps"], utc=True)
    elif "open_time" in work.columns:
        ts = pd.to_datetime(work["open_time"], utc=True)
    elif "timestamp" in work.columns:
        ts = pd.to_datetime(work["timestamp"], utc=True)
    else:
        ts = pd.date_range(end=pd.Timestamp.now(tz="UTC"), periods=len(work), freq="15min")

    work["timestamps"] = ts
    work = work.dropna(subset=["open", "high", "low", "close", "volume"]).reset_index(drop=True)
    if len(work) < 30:
        raise ValueError(f"insufficient valid candles for Kronos ({len(work)} < 30)")
    return work[["open", "high", "low", "close", "volume", "amount", "timestamps"]]


def compute_first_passage_probabilities(
    high_paths: np.ndarray,
    low_paths: np.ndarray,
    close_paths: np.ndarray,
    entry_price: float,
    tp_pct: float,
    sl_pct: float,
) -> tuple[float, float]:
    """
    Computes empirical first-passage probabilities across N simulated K-line paths
    of shape (N, H):
      - prob_up_net:   P(LONG hits +tp_pct before -sl_pct)
      - prob_down_net: P(SHORT hits -tp_pct before +sl_pct)
    If neither barrier is touched within H bars, terminal close sign weighted by
    fraction of target reached is used as a soft credit in [0, 1].
    """
    if entry_price <= 0:
        raise ValueError("entry_price must be positive")
    n_paths, horizon = close_paths.shape
    if n_paths == 0 or horizon == 0:
        return 0.5, 0.5

    tp_frac = max(float(tp_pct), 0.1) / 100.0
    sl_frac = max(float(sl_pct), 0.1) / 100.0

    long_tp = entry_price * (1.0 + tp_frac)
    long_sl = entry_price * (1.0 - sl_frac)
    short_tp = entry_price * (1.0 - tp_frac)
    short_sl = entry_price * (1.0 + sl_frac)

    long_scores = np.zeros(n_paths, dtype=float)
    short_scores = np.zeros(n_paths, dtype=float)

    for p in range(n_paths):
        # LONG evaluation (worst-case intrabar ordering: SL checked first)
        long_resolved = False
        for t in range(horizon):
            if low_paths[p, t] <= long_sl:
                long_scores[p] = 0.0
                long_resolved = True
                break
            if high_paths[p, t] >= long_tp:
                long_scores[p] = 1.0
                long_resolved = True
                break
        if not long_resolved:
            ret = (close_paths[p, -1] - entry_price) / entry_price
            long_scores[p] = float(np.clip(0.5 + 0.5 * (ret / tp_frac), 0.0, 1.0))

        # SHORT evaluation (worst-case intrabar ordering: SL checked first)
        short_resolved = False
        for t in range(horizon):
            if high_paths[p, t] >= short_sl:
                short_scores[p] = 0.0
                short_resolved = True
                break
            if low_paths[p, t] <= short_tp:
                short_scores[p] = 1.0
                short_resolved = True
                break
        if not short_resolved:
            ret = (entry_price - close_paths[p, -1]) / entry_price
            short_scores[p] = float(np.clip(0.5 + 0.5 * (ret / tp_frac), 0.0, 1.0))

    return float(np.mean(long_scores)), float(np.mean(short_scores))


def _simulate_kline_monte_carlo_paths(
    work: pd.DataFrame,
    horizon_bars: int,
    sample_count: int,
    temperature: float,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Calibrated K-line path generator (OHLC structure + volume-weighted drift +
    EWMA volatility clustering) used when Kronos neural weights are not loaded
    or during fast deterministic backtesting.
    Returns (high_paths, low_paths, close_paths) of shape (sample_count, horizon_bars).
    """
    closes = work["close"].to_numpy(dtype=float)
    highs = work["high"].to_numpy(dtype=float)
    lows = work["low"].to_numpy(dtype=float)
    vols = work["volume"].to_numpy(dtype=float)

    log_rets = np.diff(np.log(np.maximum(closes, 1e-12)))
    if len(log_rets) < 10:
        log_rets = np.zeros(10, dtype=float)

    # EWMA volatility & volume-weighted momentum + mean-reversion blend
    recent_rets = log_rets[-min(len(log_rets), 48):]
    sigma = float(np.std(recent_rets)) if len(recent_rets) > 1 else 0.003
    sigma = max(sigma, 0.0005) * max(float(temperature), 0.25)

    # Short-term vs medium-term drift with volume confirmation
    short_window = min(len(log_rets), 12)
    med_window = min(len(log_rets), 48)
    vol_weights = vols[-short_window:] / max(float(np.mean(vols[-med_window:])), 1e-12)
    vol_weights = np.clip(vol_weights, 0.25, 3.0)
    weighted_short_drift = float(np.average(log_rets[-short_window:], weights=vol_weights))
    med_drift = float(np.mean(log_rets[-med_window:]))

    # Intrabar range ratios (high-to-body and low-to-body)
    tr_pct = np.maximum((highs - lows) / np.maximum(closes, 1e-12), 0.0005)
    median_wick_pct = float(np.median(tr_pct[-min(len(tr_pct), 30):])) * 0.45

    # Z-score of close vs 48-bar mean to damp over-extended drift
    ma_ref = float(np.mean(closes[-med_window:]))
    std_ref = max(float(np.std(closes[-med_window:])), closes[-1] * 0.002)
    z_ext = (closes[-1] - ma_ref) / std_ref
    mean_rev_pull = -0.12 * sigma * float(np.clip(z_ext, -3.0, 3.0))

    step_drift = 0.55 * weighted_short_drift + 0.25 * med_drift + mean_rev_pull
    step_drift = float(np.clip(step_drift, -2.5 * sigma, 2.5 * sigma))

    rng = np.random.default_rng(seed)
    # Use Student-t (df=5) innovations scaled to unit variance to capture crypto fat tails
    raw_shocks = rng.standard_t(df=5, size=(sample_count, horizon_bars)) / np.sqrt(5.0 / 3.0)
    wick_up_noise = np.abs(rng.normal(loc=median_wick_pct, scale=median_wick_pct * 0.5, size=(sample_count, horizon_bars)))
    wick_dn_noise = np.abs(rng.normal(loc=median_wick_pct, scale=median_wick_pct * 0.5, size=(sample_count, horizon_bars)))

    high_paths = np.zeros((sample_count, horizon_bars), dtype=float)
    low_paths = np.zeros((sample_count, horizon_bars), dtype=float)
    close_paths = np.zeros((sample_count, horizon_bars), dtype=float)

    last_close = float(closes[-1])
    for p in range(sample_count):
        prev_c = last_close
        local_sigma = sigma
        for t in range(horizon_bars):
            # Mild drift decay over horizon
            decay = np.exp(-0.08 * t)
            shock = raw_shocks[p, t] * local_sigma
            r_t = step_drift * decay + shock
            next_c = prev_c * float(np.exp(r_t))
            bar_max = max(prev_c, next_c) * (1.0 + wick_up_noise[p, t])
            bar_min = min(prev_c, next_c) * max(0.01, 1.0 - wick_dn_noise[p, t])
            close_paths[p, t] = next_c
            high_paths[p, t] = bar_max
            low_paths[p, t] = bar_min
            # GARCH-like volatility update
            local_sigma = float(np.sqrt(0.85 * (local_sigma ** 2) + 0.15 * (shock ** 2)))
            prev_c = next_c

    return high_paths, low_paths, close_paths


class KronosAdapter:
    """
    Thread-safe adapter for `NeoQuasar/Kronos-*` with candle-close caching.
    """

    def __init__(
        self,
        model_id: str = DEFAULT_KRONOS_MODEL,
        device: str = "auto",
        use_fp16: bool = True,
        prefer_neural: bool = True,
        predictor_factory: Callable[[str, str, int], Any] | None = None,
    ):
        self.model_id = model_id if model_id in KRONOS_MODEL_REGISTRY else DEFAULT_KRONOS_MODEL
        self.device = device
        self.use_fp16 = use_fp16
        self.prefer_neural = prefer_neural
        self._predictor_factory = predictor_factory
        self._predictor: Any = None
        self._neural_attempted = False
        self._lock = threading.RLock()
        self._cache: dict[tuple[str, str, int, str, int, int], KronosForecast] = {}

    def _resolve_device(self) -> str:
        if self.device != "auto":
            return self.device
        try:
            import torch
            return "cuda:0" if torch.cuda.is_available() else "cpu"
        except Exception:
            return "cpu"

    def _get_or_load_neural_predictor(self) -> Any | None:
        if not self.prefer_neural:
            return None
        with self._lock:
            if self._predictor is not None:
                return self._predictor
            if self._neural_attempted and self._predictor_factory is None:
                return None
            self._neural_attempted = True

            spec = KRONOS_MODEL_REGISTRY[self.model_id]
            if self._predictor_factory is not None:
                try:
                    self._predictor = self._predictor_factory(
                        self.model_id, spec["tokenizer"], int(spec["max_context"])
                    )
                    return self._predictor
                except Exception as exc:
                    logger.warning("Custom Kronos predictor factory failed: %s", exc)
                    return None

            try:
                # Attempt loading official shiyu-coder/Kronos classes if installed in environment
                from model import Kronos, KronosTokenizer, KronosPredictor  # type: ignore
                import torch
                from pathlib import Path

                # Prioritize local checkpoint paths on D: drive if available
                local_model_dir = Path("D:/models/kronos_small")
                local_tok_dir = Path("D:/models/kronos_tokenizer_base")
                model_source = str(local_model_dir) if local_model_dir.exists() and (local_model_dir / "config.json").exists() else self.model_id
                tokenizer_source = str(local_tok_dir) if local_tok_dir.exists() and (local_tok_dir / "config.json").exists() else spec["tokenizer"]

                dev = self._resolve_device()
                tokenizer = KronosTokenizer.from_pretrained(tokenizer_source)
                model = Kronos.from_pretrained(model_source)
                if self.use_fp16 and dev.startswith("cuda"):
                    model = model.half()
                self._predictor = KronosPredictor(
                    model, tokenizer, device=dev, max_context=int(spec["max_context"])
                )
                logger.info("Loaded Kronos neural model=%s (source=%s) on device=%s", self.model_id, model_source, dev)
                return self._predictor
            except Exception as exc:
                logger.debug(
                    "Kronos neural weights not loaded in current process (%s); using calibrated K-line Monte Carlo engine",
                    exc,
                )
                return None

    def forecast(
        self,
        df: pd.DataFrame,
        *,
        symbol: str,
        timeframe: str = "15m",
        horizon_bars: int = 12,
        sample_count: int = 20,
        temperature: float = 0.8,
        top_p: float = 0.9,
        tp_pct: float = 1.8,
        sl_pct: float = 1.0,
    ) -> KronosForecast:
        spec = KRONOS_MODEL_REGISTRY.get(self.model_id, KRONOS_MODEL_REGISTRY[DEFAULT_KRONOS_MODEL])
        max_lookback = min(int(spec["max_context"]) - int(horizon_bars), 400)
        work = prepare_kronos_dataframe(df, max_lookback=max_lookback)

        last_ts = int(pd.Timestamp(work["timestamps"].iloc[-1]).value // 10**6)
        cache_key = (
            symbol.upper(),
            timeframe,
            last_ts,
            self.model_id,
            int(horizon_bars),
            int(sample_count),
        )
        with self._lock:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        current_price = float(work["close"].iloc[-1])
        high_low = (work["high"] - work["low"]).to_numpy(dtype=float)
        realized_atr = float(np.mean(high_low[-min(len(high_low), 14):]))
        realized_atr_pct = max((realized_atr / max(current_price, 1e-12)) * 100.0, 0.05)

        predictor = self._get_or_load_neural_predictor()
        backend_mode = "monte_carlo_kline"

        if predictor is not None:
            try:
                diffs = work["timestamps"].diff().dropna()
                bar_delta = diffs.median() if not diffs.empty else pd.Timedelta(minutes=15)
                last_time = work["timestamps"].iloc[-1]
                y_timestamp = pd.Series(
                    [last_time + bar_delta * (i + 1) for i in range(horizon_bars)]
                )
                x_df = work[["open", "high", "low", "close", "volume", "amount"]]
                x_timestamp = work["timestamps"]

                high_list, low_list, close_list = [], [], []
                runs = max(1, min(int(sample_count), 10))
                for _ in range(runs):
                    pred_df = predictor.predict(
                        df=x_df,
                        x_timestamp=x_timestamp,
                        y_timestamp=y_timestamp,
                        pred_len=int(horizon_bars),
                        T=float(temperature),
                        top_p=float(top_p),
                        sample_count=1,
                        verbose=False,
                    )
                    high_list.append(pred_df["high"].to_numpy(dtype=float))
                    low_list.append(pred_df["low"].to_numpy(dtype=float))
                    close_list.append(pred_df["close"].to_numpy(dtype=float))

                high_paths = np.vstack(high_list)
                low_paths = np.vstack(low_list)
                close_paths = np.vstack(close_list)
                backend_mode = "kronos_hf"
            except Exception as exc:
                logger.warning("Kronos neural predict fallback for %s: %s", symbol, exc)
                predictor = None

        if predictor is None:
            seed_bytes = f"{symbol}:{timeframe}:{last_ts}:{round(current_price, 6)}".encode("utf-8")
            seed = int.from_bytes(hashlib.sha256(seed_bytes).digest()[:8], "little")
            high_paths, low_paths, close_paths = _simulate_kline_monte_carlo_paths(
                work,
                horizon_bars=int(horizon_bars),
                sample_count=max(int(sample_count), 5),
                temperature=float(temperature),
                seed=seed,
            )

        terminal_closes = close_paths[:, -1]
        term_returns_pct = ((terminal_closes - current_price) / current_price) * 100.0
        expected_return_pct = float(np.mean(term_returns_pct))
        median_return_pct = float(np.median(term_returns_pct))
        upside_p90_pct = float(np.percentile(term_returns_pct, 90))
        downside_p10_pct = float(np.percentile(term_returns_pct, 10))

        prob_up_net, prob_down_net = compute_first_passage_probabilities(
            high_paths=high_paths,
            low_paths=low_paths,
            close_paths=close_paths,
            entry_price=current_price,
            tp_pct=tp_pct,
            sl_pct=sl_pct,
        )

        pred_ranges = np.maximum(high_paths - low_paths, 0.0)
        pred_atr = float(np.mean(pred_ranges))
        pred_atr_pct = (pred_atr / max(current_price, 1e-12)) * 100.0
        volatility_amp = float(np.clip(pred_atr_pct / realized_atr_pct, 0.2, 5.0))

        # Directional conviction + Sharpe-like signal-to-noise for cross-sectional RankIC
        ret_std = max(float(np.std(term_returns_pct)), 0.15)
        directional_ir = abs(expected_return_pct) / ret_std
        best_dir_prob = max(prob_up_net, prob_down_net)
        raw_rank = 50.0 + (best_dir_prob - 0.5) * 70.0 + min(directional_ir * 12.0, 20.0)
        rank_score = round(float(np.clip(raw_rank, 0.0, 100.0)), 2)

        result = KronosForecast(
            symbol=symbol.upper(),
            timeframe=timeframe,
            model_id=self.model_id,
            backend_mode=backend_mode,
            last_candle_ts=last_ts,
            horizon_bars=int(horizon_bars),
            sample_count=int(close_paths.shape[0]),
            current_price=round(current_price, 8),
            expected_return_pct=round(expected_return_pct, 4),
            median_return_pct=round(median_return_pct, 4),
            upside_p90_pct=round(upside_p90_pct, 4),
            downside_p10_pct=round(downside_p10_pct, 4),
            prob_up_net=round(prob_up_net, 4),
            prob_down_net=round(prob_down_net, 4),
            volatility_amp=round(volatility_amp, 4),
            predicted_atr_pct=round(pred_atr_pct, 4),
            rank_score=rank_score,
        )

        with self._lock:
            if len(self._cache) > 512:
                self._cache.clear()
            self._cache[cache_key] = result
        return result
