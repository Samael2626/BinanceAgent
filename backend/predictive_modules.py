import pandas as pd
import numpy as np
from datetime import datetime, time as dtime
import pytz


class PredictiveEngine:
    """
    Advanced Predictive Module for Trading Bot.
    Handles RSI Divergences, RVOL, Liquidity Zones, and Market Sessions.
    """

    def __init__(self):
        self.last_price_update = datetime.now()
        self.last_price = 0.0
        self.speed_buffer = []  # Stores (timestamp, price) tuples

    def analyze(self, df: pd.DataFrame, current_price: float) -> dict:
        """
        Main analysis entry point. Returns a dictionary of predictive metrics.
        """
        if df.empty or len(df) < 50:
            return {}

        results = {
            "divergences": self._detect_divergences(df),
            "rvol": self._calculate_rvol(df),
            "breakout_prob": self._calculate_breakout_prob(df),
            "liquidity_zones": self._find_liquidity_zones(df),
            "market_score": self._calculate_market_score(df),
            "session": self._get_market_session(),
            "speed": self._calculate_speed(current_price)
        }

        # Projection (Simple linear regression of last 5 candles)
        results['projection'] = self._calculate_simple_projection(df)

        # Traps (Bull/Bear)
        results['traps'] = self._detect_traps(df)

        return results

    def _detect_divergences(self, df: pd.DataFrame) -> list:
        """
        Detects RSI Divergences in the last 20 candles.
        Returns list of dicts: {"type": "bullish/bearish", "start_idx": int, "end_idx": int}
        """
        if 'RSI_14' not in df.columns:
            return []

        divergences = []
        window = 20
        subset = df.iloc[-window:].copy().reset_index(drop=True)

        if len(subset) < window:
            return []

        # Find Local Minima/Maxima logic (Simplified)
        # We look for a pivot: Left > Pivot < Right (Low) or Left < Pivot > Right (High)
        # This is computationally expensive to do perfectly on every tick, so we use a vectorized approach or simplified pivot loop.

        prices = subset['close'].values
        rsis = subset['RSI_14'].values

        # Simple loop to find pivots in the subset
        # 1 = Bullish, -1 = Bearish

        # We need at least two pivots to compare
        lows = []
        highs = []

        for i in range(2, len(subset) - 2):
            # Find Lows
            if prices[i] < prices[i-1] and prices[i] < prices[i+1]:
                lows.append((i, prices[i], rsis[i]))

            # Find Highs
            if prices[i] > prices[i-1] and prices[i] > prices[i+1]:
                highs.append((i, prices[i], rsis[i]))

        # Check Bullish Divergence (Price Lower Low, RSI Higher Low)
        if len(lows) >= 2:
            last_l = lows[-1]
            prev_l = lows[-2]

            # Check price drop and RSI rise
            if last_l[1] < prev_l[1] and last_l[2] > prev_l[2]:
                divergences.append({
                    "type": "bullish",
                    "label": "Bull Div",
                    "index": int(last_l[0])  # Relative index in window
                })

        # Check Bearish Divergence (Price Higher High, RSI Lower High)
        if len(highs) >= 2:
            last_h = highs[-1]
            prev_h = highs[-2]

            if last_h[1] > prev_h[1] and last_h[2] < prev_h[2]:
                divergences.append({
                    "type": "bearish",
                    "label": "Bear Div",
                    "index": int(last_h[0])
                })

        return divergences

    def _calculate_rvol(self, df: pd.DataFrame) -> float:
        """Relative Volume: Current Volume / 20-period Average Volume"""
        if 'volume' not in df.columns:
            return 0.0

        avg_vol = df['volume'].rolling(window=20).mean().iloc[-1]
        current_vol = df['volume'].iloc[-1]

        if avg_vol == 0:
            return 0.0

        return round(current_vol / avg_vol, 2)

    def _calculate_breakout_prob(self, df: pd.DataFrame) -> float:
        """
        Calculates probability of a breakout (0-100%).
        Based on: Volume rising, Low Volatility (Compression), RSI not overextended.
        """
        rvol = self._calculate_rvol(df)

        # Volatility Compression (BB Width)
        if 'BBU_20_2.0' in df.columns and 'BBL_20_2.0' in df.columns:
            bb_width = (df['BBU_20_2.0'].iloc[-1] - df['BBL_20_2.0'].iloc[-1])
            avg_width = (df['BBU_20_2.0'] - df['BBL_20_2.0']
                         ).rolling(20).mean().iloc[-1]
            compression = avg_width / bb_width if bb_width > 0 else 1.0
        else:
            compression = 1.0

        score = 0
        if rvol > 1.2:
            score += 40
        if compression > 1.5:
            score += 40  # High compression

        rsi = df['RSI_14'].iloc[-1] if 'RSI_14' in df.columns else 50
        if 40 <= rsi <= 60:
            score += 20  # Room to move

        return min(score, 100)

    def _find_liquidity_zones(self, df: pd.DataFrame) -> dict:
        """
        Identifies liquidity zones based on wicks.
        Returns: {"support": float, "resistance": float}
        """
        # Simplistic approach: Find clusters of Highs/Lows
        # A more advanced approach would use KDE or clustering, but for 2s incrementality we keep it simple.

        recent = df.iloc[-50:]

        # Support: Average behavior of lower wicks
        # Zone is around the lowest points that have been tested multiple times
        # For simplicity in this iteration: Lowest low of last 50
        support = recent['low'].min()

        # Target/Resistance: Highest high
        target = recent['high'].max()

        return {
            "support": float(support),
            "target": float(target)
        }

    def _calculate_market_score(self, df: pd.DataFrame) -> int:
        """
        Composite 0-100 score of market health.
        """
        score = 50

        # RSI Component
        rsi = df['RSI_14'].iloc[-1] if 'RSI_14' in df.columns else 50
        if rsi > 50:
            score += 10
        if rsi > 70:
            score -= 20  # (Overbought)
        if rsi < 30:
            score += 20  # (Oversold bounce potential)

        # Trend Component (EMA)
        close = df['close'].iloc[-1]
        ema = df['EMA_200'].iloc[-1] if 'EMA_200' in df.columns else close
        if close > ema:
            score += 20
        else:
            score -= 20

        return max(0, min(100, score))

    def _get_market_session(self) -> str:
        """Returns current active major session (Asia, London, NY)."""
        now = datetime.now(pytz.utc)
        hour = now.hour

        # Very rough session map (UTC)
        # Asia: 00:00 - 09:00
        # London: 07:00 - 16:00
        # NY: 13:00 - 22:00

        sessions = []
        if 0 <= hour < 9:
            sessions.append("ASIA")
        if 7 <= hour < 16:
            sessions.append("LONDON")
        if 13 <= hour < 22:
            sessions.append("NY")

        if not sessions:
            return "GLOBAL OVR"

        return " & ".join(sessions)

    def _calculate_speed(self, current_price: float) -> str:
        """Calculates price speed (% change per second approx)."""
        now = datetime.now()

        # Cleanup buffer (> 10s old)
        self.speed_buffer = [x for x in self.speed_buffer if (
            now - x[0]).total_seconds() < 10]
        self.speed_buffer.append((now, current_price))

        if len(self.speed_buffer) < 2:
            return "+0.00 %"

        oldest_price = self.speed_buffer[0][1]
        change = ((current_price - oldest_price) / oldest_price) * 100

        sign = "+" if change >= 0 else ""
        return f"{sign}{change:.2f} %"

    def _calculate_simple_projection(self, df: pd.DataFrame) -> list:
        """Returns a list of dicts for a 5-candle forward projection based on recent slope."""
        try:
            recent = df['close'].iloc[-5:].values
            if len(recent) < 5:
                return []

            # Linear regression slope
            x = np.arange(5)
            y = recent
            slope, intercept = np.polyfit(x, y, 1)

            last_time = int(
                df.iloc[-1]['time']) if 'time' in df.columns else int(df.index[-1].timestamp())
            start_price = recent[-1]

            projection = []

            # Predict next 5 candles
            for i in range(1, 6):
                next_price = start_price + (slope * i)
                # Ensure we have a valid timestamp (add 60s for 1m candles)
                # Assuming 1m interval for now
                next_time = last_time + (i * 60)
                projection.append({"time": next_time, "value": next_price})

            return projection
        except Exception:
            return []

    def _detect_traps(self, df: pd.DataFrame) -> list:
        """Detects Bull/Bear Traps in the last candle."""
        traps = []
        if len(df) < 3:
            return traps

        curr = df.iloc[-1]
        prev = df.iloc[-2]

        # Bull Trap: Price breaks resistance (high of prev) but closes lower
        if curr['high'] > prev['high'] and curr['close'] < prev['close']:
            # Extra filter: Volume was high on the break?
            traps.append("BULL_TRAP")

        # Bear Trap: Price breaks support (low of prev) but closes higher
        if curr['low'] < prev['low'] and curr['close'] > prev['close']:
            traps.append("BEAR_TRAP")

        return traps
