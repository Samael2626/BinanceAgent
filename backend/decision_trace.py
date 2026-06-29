def _trace_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    if isinstance(value, int):
        return str(value)
    text = str(value).replace('"', "'")
    if not text or any(ch.isspace() for ch in text) or "=" in text:
        return f'"{text}"'
    return text


def format_decision_trace(event: str, **fields) -> str:
    parts = [event]
    for key, value in fields.items():
        if value is None:
            continue
        parts.append(f"{key}={_trace_value(value)}")
    return " ".join(parts)


def decision_reason_code(reason: str) -> str:
    text = str(reason or "").lower()
    if "cooldown" in text:
        return "cooldown_active"
    if "perdida diaria" in text:
        return "daily_loss_guard_active"
    if "racha" in text:
        return "max_consecutive_losses_active"
    if "market score" in text:
        return "market_score_low"
    if "kill switch" in text:
        return "kill_switch_active"
    if "lateral" in text:
        return "lateral_market"
    if "mutual exclusion" in text:
        return "mutual_exclusion_active"
    if "strategy threshold" in text:
        return "strategy_score_below_threshold"
    if "buying" in text and "false" in text:
        return "buying_disabled"
    if "balance" in text or "saldo" in text:
        return "balance_insufficient"
    return text.replace(" ", "_") or "unknown"


def order_reason_code(reason: str) -> str:
    text = str(reason or "").lower()
    if "notional" in text or "minimo permitido" in text or "mÃ­nimo permitido" in text:
        return "min_notional_failed"
    if "lot_size" in text or "market_lot_size" in text:
        return "lot_size_failed"
    if "stepsize" in text:
        return "step_size_failed"
    if "balance" in text or "saldo" in text:
        return "balance_insufficient"
    if "apierror" in text or "api error" in text:
        return "binance_api_error"
    if "http" in text or "418" in text or "429" in text:
        return "binance_http_error"
    if "quantity" in text:
        return "quantity_validation_failed"
    return "internal_validation_failed"
