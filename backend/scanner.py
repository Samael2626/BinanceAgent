from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


DEFAULT_ROTATION_SYMBOLS = (
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "BNBUSDT",
    "ADAUSDT",
    "XRPUSDT",
    "DOGEUSDT",
    "MATICUSDT",
    "AVAXUSDT",
    "LINKUSDT",
)


@dataclass(frozen=True)
class RotationCandidate:
    symbol: str
    score: float
    market_score: float
    breakout_prob: float
    trend_strength: float
    rsi: float
    is_lateral: bool


def build_scanner_decision(
    symbol: str,
    *,
    candidate_score: float | None,
    min_candidate_score: float,
    prediction: dict | None = None,
    indicators: dict | None = None,
    candle_count: int | None = None,
    min_candles: int = 50,
    min_market_score: float = 28.0,
    spread_bps: float | None = None,
    max_spread_bps: float | None = None,
) -> dict:
    """Build a diagnostic record without changing scanner selection rules."""
    prediction = prediction or {}
    indicators = indicators or {}
    reasons: list[str] = []

    if candle_count is None:
        reasons.append("no_candles")
    elif candle_count <= 0:
        reasons.append("no_candles")
    elif candle_count < min_candles:
        reasons.append("insufficient_candles")

    market_score = float(prediction.get("market_score", 50) or 50)
    trend_strength = float(
        (prediction.get("trend_strength") or {}).get("score", 50) or 50
    )
    rvol = float(prediction.get("rvol", 1.0) or 1.0)

    if rvol < 0.5:
        reasons.append("low_volume")
    if max_spread_bps is not None and spread_bps is not None and spread_bps > max_spread_bps:
        reasons.append("spread_too_wide")
    if market_score < min_market_score:
        reasons.append("low_market_score")
    if trend_strength < 35:
        reasons.append("weak_trend")
    if bool(indicators.get("is_lateral", False)):
        reasons.append("lateral_market")

    allowed = candidate_score is not None and candidate_score >= min_candidate_score
    reason = "candidate_ok" if allowed else "below_rotation_score"
    if candidate_score is None:
        reason = reasons[0] if reasons else "not_scored"

    return {
        "symbol": symbol,
        "allowed": allowed,
        "reason": reason,
        "reasons": reasons,
        "score": candidate_score,
        "threshold": min_candidate_score,
        "market_score": market_score,
        "min_market_score": min_market_score,
        "trend_strength": trend_strength,
        "rvol": rvol,
        "candles": candle_count,
        "spread_bps": spread_bps,
    }


def parse_rotation_watchlist(raw: str | Iterable[str] | None) -> list[str]:
    if raw is None:
        return list(DEFAULT_ROTATION_SYMBOLS)

    if isinstance(raw, str):
        parts = raw.replace("\n", ",").split(",")
    else:
        parts = list(raw)

    symbols: list[str] = []
    seen: set[str] = set()

    for part in parts:
        symbol = str(part or "").strip().upper()
        if not symbol:
            continue
        if not symbol.endswith("USDT"):
            symbol = f"{symbol}USDT"
        if not symbol.replace("USDT", "").isalnum():
            continue
        if symbol not in seen:
            seen.add(symbol)
            symbols.append(symbol)

    return symbols or list(DEFAULT_ROTATION_SYMBOLS)


def score_rotation_candidate(prediction: dict, indicators: dict) -> float:
    market_score = float(prediction.get("market_score", 50) or 50)
    breakout_prob = float(prediction.get("breakout_prob", 0) or 0)
    trend_strength = float(
        (prediction.get("trend_strength") or {}).get("score", 50) or 50
    )
    rvol = float(prediction.get("rvol", 1.0) or 1.0)
    rsi = float(indicators.get("rsi", 50) or 50)
    macd_hist = float(indicators.get("macd_hist", 0) or 0)
    is_lateral = bool(indicators.get("is_lateral", False))

    score = (market_score * 0.45) + (breakout_prob * 0.2) + (trend_strength * 0.2)
    score += min(max((rvol - 1.0) * 12.0, 0.0), 10.0)

    if macd_hist > 0:
        score += 4.0
    if is_lateral:
        score -= 10.0
    if rsi >= 72:
        score -= 8.0
    elif rsi <= 28:
        score += 3.0

    return round(max(0.0, min(100.0, score)), 2)


def should_switch_rotation_candidate(
    current_symbol: str,
    current_score: float,
    best_candidate: RotationCandidate | None,
    min_candidate_score: float,
    min_score_edge: float = 4.0,
) -> bool:
    if best_candidate is None:
        return False
    if best_candidate.score < min_candidate_score:
        return False
    if best_candidate.symbol == current_symbol:
        return False
    return best_candidate.score >= (current_score + min_score_edge)
