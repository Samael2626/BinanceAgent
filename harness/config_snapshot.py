"""Captura reproducible de ajustes de trading sin credenciales."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


SETTING_KEYS = frozenset({
    "active_strategy", "timeframe", "symbol", "rotation_watchlist",
    "auto_asset_rotation", "rotation_interval_minutes", "min_rotation_score",
    "buy_rsi", "sell_rsi", "smart_scalper_entry_score", "enable_trend_filter",
    "enable_fast_ema", "enable_vol_filter", "ema_length", "fast_ema_len",
    "macd_fast", "macd_slow", "macd_signal", "stop_loss_pct", "take_profit_pct",
    "rsi_trailing_pct", "adaptive_trailing_enabled", "adaptive_trailing_atr_mult",
    "adaptive_trailing_min_pct", "adaptive_trailing_max_pct", "trade_qty",
    "trade_qty_type", "auto_position_sizing", "risk_per_trade_pct",
    "max_daily_loss_pct", "max_consecutive_losses", "atr_stop_mult",
    "min_market_score_to_buy", "cooldown_minutes", "portfolio_max_drawdown_pct",
    "portfolio_kill_switch_enabled", "dca_step_pct", "max_dca_orders",
})
STATE_KEYS = frozenset({"dca_enabled", "enable_buying", "enable_selling"})


def snapshot(db_path: Path, user_id: int) -> dict:
    source = db_path.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    connection = sqlite3.connect(f"{source.as_uri()}?mode=ro&immutable=1", uri=True)
    try:
        settings = {key: value for key, value in connection.execute(
            "SELECT key,value FROM settings WHERE user_id=?", (user_id,))
            if key in SETTING_KEYS}
        state = {key: value for key, value in connection.execute(
            "SELECT key,value FROM state WHERE user_id=?", (user_id,))
            if key in STATE_KEYS}
    finally:
        connection.close()
    if not settings:
        raise ValueError(f"sin configuracion de trading para usuario {user_id}")
    captured = {
        "user_id": user_id,
        "source_modified_utc": datetime.fromtimestamp(source.stat().st_mtime, timezone.utc).isoformat(),
        "settings": settings,
        "state": state,
    }
    payload = json.dumps(captured, sort_keys=True, separators=(",", ":")).encode()
    captured["sha256"] = hashlib.sha256(payload).hexdigest()
    return captured


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--user-id", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = snapshot(args.db, args.user_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{args.output}: {result['sha256']}")


if __name__ == "__main__":
    main()
