# Hybrid Changeset

## 2026-06-28 — 5m migration
- Timeframe: `15m` → `5m`
- `stop_loss_pct`: `2.5` → `1.5`
- `take_profit_pct`: `1.2` → `1.5`
- `cooldown_minutes`: `8` → `3`
- Sensitivity tuning preserved: `smart_scalper_entry_score=58`, `min_market_score_to_buy=32`

## 2026-06-27 — defaults + backtest
- `trade_qty` default aligned to `12`
- `risk_per_trade_pct` aligned to `0.75`
- Backtest exposes `win_rate`, `profit_factor`, `max_drawdown_pct`
