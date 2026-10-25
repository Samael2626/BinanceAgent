"""
Download and Activation Script for Kronos-small Neural Weights on NVIDIA GPU (or CPU fallback).

Usage:
    python scripts/download_kronos_weights.py [options]

Options:
    --model-id       Hugging Face repository ID for Kronos model (default: NeoQuasar/Kronos-small)
    --tokenizer-id   Hugging Face repository ID for tokenizer (default: NeoQuasar/Kronos-Tokenizer-base)
    --cache-dir      Base directory for weights storage (default: D:/models/huggingface)
    --dest-dir       Target directory for explicit model snapshot (default: D:/models/kronos_small)
    --device         Device for smoke test: auto | cuda:0 | cpu (default: auto)
    --skip-test      Skip smoke-test inference run
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

# Ensure repo root and backend are on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("kronos_downloader")


def configure_d_drive_environment(custom_cache_dir: str | None = None) -> Path:
    """Configures HF_HOME and temp variables on drive D to avoid C: exhaustion."""
    d_cache = Path(custom_cache_dir or "D:/models/huggingface")
    d_cache.mkdir(parents=True, exist_ok=True)
    d_temp = Path("D:/temp")
    d_temp.mkdir(parents=True, exist_ok=True)

    os.environ["HF_HOME"] = str(d_cache)
    os.environ["HUGGINGFACE_HUB_CACHE"] = str(d_cache / "hub")
    if "TMP" not in os.environ or os.environ["TMP"].upper().startswith("C:"):
        os.environ["TMP"] = str(d_temp)
    if "TEMP" not in os.environ or os.environ["TEMP"].upper().startswith("C:"):
        os.environ["TEMP"] = str(d_temp)

    logger.info("Configured storage paths: HF_HOME=%s, TEMP=%s", os.environ["HF_HOME"], os.environ["TEMP"])
    return d_cache


def download_checkpoints(
    model_id: str,
    tokenizer_id: str,
    dest_dir: Path | None = None,
) -> tuple[str, str]:
    """Downloads model and tokenizer from Hugging Face hub, verifying essential artifacts."""
    from huggingface_hub import snapshot_download

    logger.info("Downloading tokenizer: %s", tokenizer_id)
    tok_dir = snapshot_download(
        repo_id=tokenizer_id,
        local_dir=str(dest_dir.parent / "kronos_tokenizer_base") if dest_dir else None,
        local_dir_use_symlinks=False,
        resume_download=True,
    )
    logger.info("Tokenizer ready at: %s", tok_dir)

    logger.info("Downloading model checkpoint: %s", model_id)
    mdl_dir = snapshot_download(
        repo_id=model_id,
        local_dir=str(dest_dir) if dest_dir else None,
        local_dir_use_symlinks=False,
        resume_download=True,
    )
    logger.info("Model weights ready at: %s", mdl_dir)

    # Verify key artifacts
    mdl_path = Path(mdl_dir)
    safetensors = list(mdl_path.glob("*.safetensors")) + list(mdl_path.glob("*.bin"))
    if not safetensors:
        raise FileNotFoundError(f"No model weights (.safetensors / .bin) found in {mdl_dir}")

    config_file = mdl_path / "config.json"
    if not config_file.exists():
        raise FileNotFoundError(f"Missing config.json in {mdl_dir}")

    weight_size_mb = sum(f.stat().st_size for f in safetensors) / (1024 * 1024)
    logger.info("Verified %d weight files (total %.2f MB)", len(safetensors), weight_size_mb)
    return mdl_dir, tok_dir


def smoke_test_activation(model_dir: str, tokenizer_dir: str, target_device: str = "auto") -> bool:
    """Loads Kronos model onto GPU/CPU and tests 12-bar multi-step prediction on synthetic candles."""
    import numpy as np
    import pandas as pd
    import torch
    from model import Kronos, KronosTokenizer, KronosPredictor

    # Device resolution
    if target_device == "auto":
        dev = "cuda:0" if torch.cuda.is_available() else "cpu"
    else:
        dev = target_device

    logger.info("Evaluating device: %s (torch %s, cuda available=%s)", dev, torch.__version__, torch.cuda.is_available())
    if dev.startswith("cuda"):
        gpu_name = torch.cuda.get_device_name(0)
        vram_total_mb = torch.cuda.get_device_properties(0).total_memory / (1024 * 1024)
        logger.info("Active GPU: %s (Total VRAM: %.1f MB)", gpu_name, vram_total_mb)

    t0 = time.perf_counter()
    logger.info("Loading tokenizer from %s...", tokenizer_dir)
    tokenizer = KronosTokenizer.from_pretrained(tokenizer_dir)

    logger.info("Loading Kronos model from %s...", model_dir)
    model = Kronos.from_pretrained(model_dir)

    use_fp16 = dev.startswith("cuda")
    if use_fp16:
        model = model.half()
        logger.info("Converted model weights to FP16 for NVIDIA GPU execution")

    load_time_s = time.perf_counter() - t0
    param_count = sum(p.numel() for p in model.parameters())
    logger.info("Model loaded in %.2f s (Parameters: %d = %.2f M)", load_time_s, param_count, param_count / 1e6)

    # Initialize predictor
    predictor = KronosPredictor(model, tokenizer, device=dev, max_context=512)

    if dev.startswith("cuda"):
        vram_allocated_mb = torch.cuda.memory_allocated(0) / (1024 * 1024)
        vram_reserved_mb = torch.cuda.memory_reserved(0) / (1024 * 1024)
        logger.info("VRAM after load: allocated=%.1f MB, reserved=%.1f MB", vram_allocated_mb, vram_reserved_mb)

    # Build realistic 60-candle input series
    n_candles = 60
    base_price = 100.0
    rng = np.random.default_rng(42)
    dt_index = pd.date_range(end=pd.Timestamp.now(tz="UTC"), periods=n_candles, freq="15min")
    price_series = base_price * np.exp(np.cumsum(rng.normal(0, 0.003, n_candles)))
    highs = price_series * (1.0 + np.abs(rng.normal(0, 0.002, n_candles)))
    lows = price_series * (1.0 - np.abs(rng.normal(0, 0.002, n_candles)))
    closes = price_series
    opens = np.roll(closes, 1)
    opens[0] = base_price
    volumes = np.abs(rng.normal(1500, 300, n_candles))
    amounts = closes * volumes

    x_df = pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
        "amount": amounts,
    })
    x_timestamp = pd.Series(dt_index)
    bar_delta = pd.Timedelta(minutes=15)
    horizon = 12
    y_timestamp = pd.Series([dt_index[-1] + bar_delta * (i + 1) for i in range(horizon)])

    logger.info("Running smoke-test prediction (horizon=%d bars)...", horizon)
    inf_t0 = time.perf_counter()
    pred_df = predictor.predict(
        df=x_df,
        x_timestamp=x_timestamp,
        y_timestamp=y_timestamp,
        pred_len=horizon,
        T=0.8,
        top_p=0.9,
        sample_count=1,
        verbose=False,
    )
    inf_lat_ms = (time.perf_counter() - inf_t0) * 1000.0

    logger.info("Smoke test forecast generated in %.1f ms", inf_lat_ms)
    logger.info("Output forecast shape: %s, columns: %s", pred_df.shape, list(pred_df.columns))
    logger.info(
        "Forecast sample: start close=%.4f -> end close=%.4f (return: %+.2f%%)",
        float(pred_df["close"].iloc[0]),
        float(pred_df["close"].iloc[-1]),
        ((float(pred_df["close"].iloc[-1]) - closes[-1]) / closes[-1]) * 100.0,
    )

    if dev.startswith("cuda"):
        vram_peak_mb = torch.cuda.max_memory_allocated(0) / (1024 * 1024)
        logger.info("Peak VRAM during inference: %.1f MB", vram_peak_mb)

    assert len(pred_df) == horizon, f"Expected {horizon} bars, got {len(pred_df)}"
    assert all(c in pred_df.columns for c in ["open", "high", "low", "close"]), "Missing required OHLC columns"
    logger.info("SUCCESS: Kronos-small neural pipeline verified and ready for production inference!")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Download and activate Kronos neural weights on D:")
    parser.add_argument("--model-id", default="NeoQuasar/Kronos-small", help="HuggingFace model ID")
    parser.add_argument("--tokenizer-id", default="NeoQuasar/Kronos-Tokenizer-base", help="HuggingFace tokenizer ID")
    parser.add_argument("--cache-dir", default="D:/models/huggingface", help="HF_HOME cache on D:")
    parser.add_argument("--dest-dir", default="D:/models/kronos_small", help="Explicit target dir on D:")
    parser.add_argument("--device", default="auto", help="auto | cuda:0 | cpu")
    parser.add_argument("--skip-test", action="store_true", help="Skip smoke test")
    args = parser.parse_args()

    try:
        configure_d_drive_environment(args.cache_dir)
        dest_path = Path(args.dest_dir) if args.dest_dir else None
        model_dir, tokenizer_dir = download_checkpoints(args.model_id, args.tokenizer_id, dest_path)

        if not args.skip_test:
            smoke_test_activation(model_dir, tokenizer_dir, target_device=args.device)

        return 0
    except Exception as exc:
        logger.error("Failed downloading/activating Kronos weights: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
