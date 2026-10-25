"""
Kronos Quant Strategy (`KronosQuantStrategy`).

Combines:
  1. Probabilistic K-line trajectories from `KronosAdapter` (`NeoQuasar/Kronos-*`)
  2. Real-time derivatives microstructure (`MicrostructureAnalyzer`: OBI, ΔOI regime, Funding rate)
  3. De Prado Meta-Labeling Expected Value Gate:
       EV_bps = P_win * TP_bps - P_loss * SL_bps - RoundTripCost_bps + MicroAdj_bps
     Only executes when EV_bps >= min_ev_bps AND reward-to-risk >= min_rr_ratio.
  4. Supports both Spot (LONG-only) and USDⓈ-M Futures (LONG and SHORT).
"""

from __future__ import annotations

from typing import Any, Dict

from .base_strategy import BaseStrategy


class KronosQuantStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("Kronos Quant")

    def get_required_indicators(self) -> list:
        return ["rsi", "macd_hist", "macd_signal", "trend_ema", "fast_ema", "atr", "adx"]

    @staticmethod
    def _resolve_barriers_pct(indicators: Dict[str, Any], settings: Dict[str, Any], current_price: float, side: str = "LONG") -> tuple[float, float]:
        """
        Computes volatility-adapted Stop Loss (%) and Take Profit (%) enforcing
        a calibrated reward-to-risk ratio (default >= 1.3x) tuned for high Win Rate.
        """
        default_tp = 1.9 if str(side).upper() == "SHORT" else 2.0
        base_sl = max(float(settings.get("stop_loss_pct", 1.5) or 1.5), 0.4)
        base_tp = max(float(settings.get("take_profit_pct", default_tp) or default_tp), 0.8)
        min_rr = max(float(settings.get("kronos_min_rr_ratio", 1.3) or 1.3), 1.0)

        atr = float(indicators.get("atr", 0.0) or 0.0)
        if atr > 0 and current_price > 0:
            atr_pct = (atr / current_price) * 100.0
            sl_mult = max(float(settings.get("atr_stop_mult", 1.6) or 1.6), 0.5)
            tp_mult = max(float(settings.get("atr_tp_multiplier", sl_mult * min_rr) or (sl_mult * min_rr)), sl_mult * min_rr)
            sl_pct = max(base_sl * 0.7, min(3.0, atr_pct * sl_mult))
            tp_pct = max(sl_pct * min_rr, min(5.0, atr_pct * tp_mult))
        else:
            sl_pct = base_sl
            tp_pct = max(base_tp, sl_pct * min_rr)

        return round(tp_pct, 4), round(sl_pct, 4)

    @staticmethod
    def _round_trip_cost_bps(settings: Dict[str, Any]) -> float:
        """
        Returns realistic round-trip execution cost in basis points (1% = 100 bps):
          - FUTURES Maker-First (`LIMIT_MAKER`): 2 * 2 bps fee + 1 bps slip = 5 bps
          - FUTURES Taker (`MARKET`):            2 * 5 bps fee + 4 bps slip = 14 bps
          - SPOT Taker (`MARKET`):               2 * 10 bps fee + 4 bps slip = 24 bps
        """
        market_type = str(settings.get("market_type", "SPOT") or "SPOT").upper()
        order_execution_style = str(settings.get("order_execution_style", "LIMIT_MAKER") or "LIMIT_MAKER").upper()
        latency_bps = float(settings.get("paper_latency_bps", 2.0) or 2.0)

        if market_type == "FUTURES":
            if order_execution_style == "LIMIT_MAKER":
                maker_fee_bps = float(settings.get("futures_maker_fee_pct", 0.02) or 0.02) * 100.0
                return 2.0 * maker_fee_bps + 1.0
            taker_fee_bps = float(settings.get("futures_taker_fee_pct", 0.05) or 0.05) * 100.0
            return 2.0 * taker_fee_bps + 2.0 * latency_bps

        spot_fee_bps = float(settings.get("paper_fee_pct", 0.10) or 0.10) * 100.0
        return 2.0 * spot_fee_bps + 2.0 * latency_bps

    def evaluate_setup(
        self,
        indicators: Dict[str, Any],
        settings: Dict[str, Any],
        state: Dict[str, Any],
    ) -> dict[str, Any]:
        """
        Evaluates both LONG and SHORT setups using Kronos + Microstructure + Meta-Labeling EV Gate.
        Returns a structured decision dict with:
          side ("LONG" | "SHORT" | "NONE"), score (0..100), ev_bps, tp_pct, sl_pct, reasons
        """
        current_price = float(state.get("current_price", 0.0) or 0.0)
        kronos = state.get("kronos_forecast") or indicators.get("kronos_forecast") or {}
        micro = state.get("microstructure") or indicators.get("microstructure") or {}

        tp_long_pct, sl_long_pct = self._resolve_barriers_pct(indicators, settings, current_price, "LONG")
        tp_short_pct, sl_short_pct = self._resolve_barriers_pct(indicators, settings, current_price, "SHORT")
        tp_long_bps = tp_long_pct * 100.0
        sl_long_bps = sl_long_pct * 100.0
        tp_short_bps = tp_short_pct * 100.0
        sl_short_bps = sl_short_pct * 100.0
        cost_bps = self._round_trip_cost_bps(settings)
        min_ev_bps = float(settings.get("kronos_min_ev_bps", 12.0) or 12.0)

        prob_up = float(kronos.get("prob_up_net", 0.5) or 0.5)
        prob_down = float(kronos.get("prob_down_net", 0.5) or 0.5)
        exp_ret_pct = float(kronos.get("expected_return_pct", 0.0) or 0.0)
        vol_amp = float(kronos.get("volatility_amp", 1.0) or 1.0)

        long_micro_adj = float(micro.get("long_edge_bps_adj", 0.0) or 0.0)
        short_micro_adj = float(micro.get("short_edge_bps_adj", 0.0) or 0.0)
        oi_regime = str(micro.get("oi_regime", "NEUTRAL") or "NEUTRAL")
        spread_bps = float(micro.get("spread_bps", 0.0) or 0.0)

        cross_venue = state.get("cross_venue_arb") or indicators.get("cross_venue_arb") or {}
        cv_bias_bps = float(cross_venue.get("directional_bias_bps", 0.0) or 0.0)
        long_micro_adj += cv_bias_bps
        short_micro_adj -= cv_bias_bps

        # Penalize if live order book spread is abnormally wide (> 8 bps)
        spread_penalty_bps = max(0.0, spread_bps - 3.0)

        rsi = float(indicators.get("rsi", 50.0) or 50.0)
        macd_hist = float(indicators.get("macd_hist", 0.0) or 0.0)
        trend_ema = float(indicators.get("trend_ema", 0.0) or 0.0)

        # Technical regime alignment bonus/penalty in bps
        tech_long_bps = 0.0
        tech_short_bps = 0.0
        if trend_ema > 0 and current_price > 0:
            if current_price >= trend_ema:
                tech_long_bps += 4.0
            else:
                tech_short_bps += 4.0
        if macd_hist > 0:
            tech_long_bps += 3.0
        elif macd_hist < 0:
            tech_short_bps += 3.0
        if rsi >= 74.0:
            tech_long_bps -= 12.0  # Do not chase extreme overbought on LONG
            tech_short_bps += 4.0
        elif rsi <= 26.0:
            tech_short_bps -= 12.0  # Do not chase extreme oversold on SHORT
            tech_long_bps += 4.0

        macro_lead = state.get("macro_lead") or indicators.get("macro_lead") or {}
        btc_trend = str(macro_lead.get("trend", "NEUTRAL") or "NEUTRAL").upper()
        btc_bias = float(macro_lead.get("bias_bps", 0.0) or 0.0)

        # Institutional Cross-Asset Lead-Lag Filter (BTC anchor alignment)
        if btc_trend == "BULLISH":
            tech_long_bps += btc_bias
            tech_short_bps -= 20.0
            # Anti-Blowoff filter: do not chase alt breakouts if BTC just expanded >= +1.40% in 1h
            btc_ret_1h = float(macro_lead.get("return_1h_pct", 0.0) or 0.0)
            if btc_ret_1h >= 1.40:
                tech_long_bps -= 30.0
        elif btc_trend == "BEARISH":
            tech_short_bps += abs(btc_bias)
            tech_long_bps -= 20.0

        # Expected Value (bps) net of round-trip costs
        ev_long_bps = (
            prob_up * tp_long_bps
            - (1.0 - prob_up) * sl_long_bps
            - cost_bps
            - spread_penalty_bps
            + long_micro_adj
            + tech_long_bps
        )
        ev_short_bps = (
            prob_down * tp_short_bps
            - (1.0 - prob_down) * sl_short_bps
            - cost_bps
            - spread_penalty_bps
            + short_micro_adj
            + tech_short_bps
        )

        # Require Kronos expected terminal return to agree with trade direction
        if exp_ret_pct < -0.05:
            ev_long_bps -= 15.0
        if exp_ret_pct > 0.05:
            ev_short_bps -= 15.0

        # Dead volatility filter: avoid entering when Kronos predicts volatility collapse
        if vol_amp < 0.45:
            ev_long_bps -= 10.0
            ev_short_bps -= 10.0

        market_type = str(settings.get("market_type", "SPOT") or "SPOT").upper()
        allow_short = market_type == "FUTURES" and bool(settings.get("futures_allow_short", True))

        chosen_side = "NONE"
        chosen_ev = ev_long_bps
        prob_win = prob_up
        tp_pct = tp_long_pct
        sl_pct = sl_long_pct

        if allow_short and ev_short_bps > ev_long_bps and ev_short_bps >= min_ev_bps:
            chosen_side = "SHORT"
            chosen_ev = ev_short_bps
            prob_win = prob_down
            tp_pct = tp_short_pct
            sl_pct = sl_short_pct
        elif ev_long_bps >= min_ev_bps:
            chosen_side = "LONG"
            chosen_ev = ev_long_bps
            prob_win = prob_up
            tp_pct = tp_long_pct
            sl_pct = sl_long_pct
        elif allow_short and ev_short_bps > ev_long_bps:
            chosen_ev = ev_short_bps
            prob_win = prob_down
            tp_pct = tp_short_pct
            sl_pct = sl_short_pct

        # High precision gate: require minimum directional probability (default >= 0.52)
        min_prob_win = float(settings.get("kronos_min_prob_win", 0.52) or 0.52)
        if chosen_side != "NONE" and prob_win < min_prob_win:
            chosen_side = "NONE"
            chosen_ev = min(chosen_ev, min_ev_bps - 1.0)

        # Anti-Wick quality filter: reject breakout candles with long opposing wicks (absorption)
        candle_close_pct = float(indicators.get("candle_close_pct", -1.0))
        if candle_close_pct >= 0.0 and chosen_side != "NONE":
            if chosen_side == "LONG" and candle_close_pct < 0.60:
                chosen_side = "NONE"
                chosen_ev = min(chosen_ev, min_ev_bps - 1.0)
            elif chosen_side == "SHORT" and candle_close_pct > 0.40:
                chosen_side = "NONE"
                chosen_ev = min(chosen_ev, min_ev_bps - 1.0)

        # Macro-Concurrencia Estricta con Bitcoin (Anti-Squeeze Shield)
        # Altcoins are severely squeezed if shorted while BTC is bullish
        if chosen_side == "SHORT" and btc_trend == "BULLISH":
            chosen_side = "NONE"
            chosen_ev = min(chosen_ev, min_ev_bps - 1.0)

        # RSI Exhaustion Floor: do not open SHORT if already deeply oversold (reversal zone)
        if chosen_side == "SHORT" and rsi < 33.0:
            chosen_side = "NONE"
            chosen_ev = min(chosen_ev, min_ev_bps - 1.0)

        # Map net EV (bps) into the 0..100 score scale used by BinanceBot & Scanner
        # At chosen_ev == min_ev_bps -> score = 65.0; +35 bps above threshold -> 100.0
        raw_score = 65.0 + (chosen_ev - min_ev_bps) * 1.0
        score = round(float(max(0.0, min(100.0, raw_score))), 2)

        reasons = [
            f"side={chosen_side}",
            f"EV={chosen_ev:+.1f}bps(min={min_ev_bps:.1f})",
            f"P_win={prob_win:.2f}",
            f"E[ret]={exp_ret_pct:+.2f}%",
            f"TP/SL={tp_pct:.2f}%/{sl_pct:.2f}%",
            f"cost={cost_bps:.1f}bps",
            f"OI={oi_regime}",
        ]
        if btc_trend != "NEUTRAL":
            reasons.append(f"Lead={btc_trend}({btc_bias:+.1f}bps)")
        if candle_close_pct >= 0.0:
            reasons.append(f"Wick={candle_close_pct:.2f}")
        return {
            "side": chosen_side,
            "score": score,
            "ev_bps": round(chosen_ev, 2),
            "ev_long_bps": round(ev_long_bps, 2),
            "ev_short_bps": round(ev_short_bps, 2),
            "tp_pct": tp_pct,
            "sl_pct": sl_pct,
            "cost_bps": round(cost_bps, 2),
            "prob_win": round(prob_win, 4),
            "reasons": reasons,
        }

    def score_buy_setup(
        self,
        indicators: Dict[str, Any],
        settings: Dict[str, Any],
        state: Dict[str, Any],
    ) -> tuple[float, list[str]]:
        eval_res = self.evaluate_setup(indicators, settings, state)
        return float(eval_res["score"]), list(eval_res["reasons"])

    def check_buy_signal(
        self,
        indicators: Dict[str, Any],
        settings: Dict[str, Any],
        state: Dict[str, Any],
    ) -> bool:
        eval_res = self.evaluate_setup(indicators, settings, state)
        min_score = float(settings.get("smart_scalper_entry_score", 65.0) or 65.0)
        if eval_res["side"] in {"LONG", "SHORT"} and eval_res["score"] >= min_score:
            self.log_decision(
                f"ENTRY {eval_res['side']} score {eval_res['score']:.1f}/{min_score:.1f}: {', '.join(eval_res['reasons'])}",
                print,
            )
            return True
        self.log_decision(
            f"ENTRY skipped: score {eval_res['score']:.1f}/{min_score:.1f}: {', '.join(eval_res['reasons'])}",
            print,
        )
        return False

    def check_sell_signal(
        self,
        indicators: Dict[str, Any],
        settings: Dict[str, Any],
        state: Dict[str, Any],
    ) -> bool:
        """
        Supports both LONG and SHORT position exits, plus Kronos regime-reversal exit.
        """
        position_side = str(state.get("position_side", "LONG") or "LONG").upper()
        current_price = float(state.get("current_price", 0.0) or 0.0)
        entry_price = float(state.get("entry_price", 0.0) or 0.0)
        lowest_price = float(state.get("lowest_price", 0.0) or 0.0)

        if entry_price <= 0 or current_price <= 0:
            return False

        tp_pct, sl_pct = self._resolve_barriers_pct(indicators, settings, entry_price, position_side)
        local_settings = {**settings, "stop_loss_pct": sl_pct, "take_profit_pct": tp_pct}

        highest_price = float(state.get("highest_price", 0.0) or 0.0)

        bars_held = int(state.get("bars_held", 0) or 0)

        # 1. 3-Bar Momentum Scratch: if trade is held >= 3 bars and floating in profit (>= +0.06%), lock it in
        if bars_held >= 3:
            if position_side == "SHORT" and current_price <= entry_price * 0.9994:
                self.log_decision(
                    f"EXIT SHORT: 3-Bar Momentum Scratch ({bars_held} bars) @ {current_price:.4f} <= {entry_price * 0.9994:.4f}",
                    print,
                )
                return True
            elif position_side == "LONG" and current_price >= entry_price * 1.0006:
                self.log_decision(
                    f"EXIT LONG: 3-Bar Momentum Scratch ({bars_held} bars) @ {current_price:.4f} >= {entry_price * 1.0006:.4f}",
                    print,
                )
                return True

        # 2. Vertical Time Barrier (8 bars momentum stall exit in profit >= +0.20%)
        if bars_held >= 8:
            if position_side == "SHORT" and current_price <= entry_price * 0.9980:
                self.log_decision(
                    f"EXIT SHORT: Vertical Time Barrier ({bars_held} bars) @ {current_price:.4f} <= {entry_price * 0.9980:.4f}",
                    print,
                )
                return True
            elif position_side == "LONG" and current_price >= entry_price * 1.0020:
                self.log_decision(
                    f"EXIT LONG: Vertical Time Barrier ({bars_held} bars) @ {current_price:.4f} >= {entry_price * 1.0020:.4f}",
                    print,
                )
                return True

        # 3. SHORT Position Exits (Profit Lock, Stop Loss, Trailing, TP)
        if position_side == "SHORT":
            # Tier-2 High Profit Lock: if reached +1.45% gain, lock +0.60%
            if lowest_price > 0 and lowest_price <= entry_price * 0.9855:
                lock_p = entry_price * 0.9940
                if current_price >= lock_p:
                    self.log_decision(f"EXIT SHORT: Profit Lock @ {current_price:.4f} >= {lock_p:.4f}", print)
                    return True
            # Tier-1 Breakeven Lock: if reached +1.00% gain, lock +0.25% (cover fees)
            elif lowest_price > 0 and lowest_price <= entry_price * 0.9900:
                lock_p = entry_price * 0.9975
                if current_price >= lock_p:
                    self.log_decision(f"EXIT SHORT: Tier-1 Breakeven Lock @ {current_price:.4f} >= {lock_p:.4f}", print)
                    return True

            sl_price = entry_price * (1.0 + sl_pct / 100.0)
            if current_price >= sl_price:
                self.log_decision(f"EXIT SHORT: Stop Loss @ {current_price:.4f} >= {sl_price:.4f}", print)
                return True

            trail_pct = float(settings.get("rsi_trailing_pct", 0.8) or 0.8)
            if lowest_price > 0 and lowest_price < entry_price:
                trail_price = lowest_price * (1.0 + trail_pct / 100.0)
                if current_price > trail_price:
                    self.log_decision(
                        f"EXIT SHORT: Profit Step Trail @ {current_price:.4f} (Low: {lowest_price:.4f})",
                        print,
                    )
                    return True

            tp_price = entry_price * (1.0 - tp_pct / 100.0)
            if current_price <= tp_price:
                self.log_decision(f"EXIT SHORT: Take Profit @ {current_price:.4f} <= {tp_price:.4f}", print)
                return True
            return False

        # 4. LONG Position Exits (Profit Lock, Standard Exits)
        if highest_price > 0:
            # Tier-2 High Profit Lock: if reached +1.45% gain, lock +0.60%
            if highest_price >= entry_price * 1.0145:
                lock_p = entry_price * 1.0060
                if current_price <= lock_p:
                    self.log_decision(f"EXIT LONG: Profit Lock @ {current_price:.4f} <= {lock_p:.4f}", print)
                    return True
            # Tier-1 Breakeven Lock: if reached +1.00% gain, lock +0.25% (cover fees)
            elif highest_price >= entry_price * 1.0100:
                lock_p = entry_price * 1.0025
                if current_price <= lock_p:
                    self.log_decision(f"EXIT LONG: Tier-1 Breakeven Lock @ {current_price:.4f} <= {lock_p:.4f}", print)
                    return True

        return self.check_standard_exits(indicators, local_settings, state)
