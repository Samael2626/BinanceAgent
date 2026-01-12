from typing import Dict, Any
import pandas as pd
import pandas_ta as ta


def calculate_indicators(df: pd.DataFrame, settings: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculates technical indicators for the trading bot.

    Args:
        df: DataFrame with OHLCV data.
        settings: Dictionary containing indicator parameters (ema_length, macd_fast, etc.)

    Returns:
        Dict: A dictionary containing calculated indicators (rsi, macd, ema_200, etc.)
    """
    results = {}

    if df.empty:
        return results

    # RSI Calculation
    if len(df) > 14:
        try:
            rsi = df.ta.rsi(length=14)
            if rsi is not None and not rsi.empty:
                results['rsi'] = float(rsi.iloc[-1])
        except Exception:
            pass

    # MACD Calculation
    macd_fast = int(settings.get('macd_fast', 12))
    macd_slow = int(settings.get('macd_slow', 26))
    macd_signal = int(settings.get('macd_signal', 9))

    if len(df) > max(macd_fast, macd_slow, macd_signal):
        try:
            macd = df.ta.macd(fast=macd_fast, slow=macd_slow,
                              signal=macd_signal)
            if macd is not None and not macd.empty:
                # pandas_ta returns columns like MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
                macd_col = next(
                    (c for c in macd.columns if c.startswith('MACD_')), None)
                hist_col = next(
                    (c for c in macd.columns if c.startswith('MACDh_')), None)
                sig_col = next(
                    (c for c in macd.columns if c.startswith('MACDs_')), None)

                if macd_col and hist_col and sig_col:
                    results['macd'] = float(
                        macd[macd_col].iloc[-1]) if pd.notna(macd[macd_col].iloc[-1]) else 0.0
                    results['macd_hist'] = float(
                        macd[hist_col].iloc[-1]) if pd.notna(macd[hist_col].iloc[-1]) else 0.0
                    results['macd_signal'] = float(
                        macd[sig_col].iloc[-1]) if pd.notna(macd[sig_col].iloc[-1]) else 0.0
        except Exception:
            pass

    # EMA Calculation
    ema_length = int(settings.get('ema_length', 200))
    if len(df) > ema_length:
        try:
            ema = df.ta.ema(length=ema_length)
            if ema is not None and not ema.empty:
                results['trend_ema'] = float(ema.iloc[-1])
        except Exception:
            pass

    # Standard EMAs (Fast)
    if len(df) > 7:
        try:
            results['ema_2'] = float(df.ta.ema(length=2).iloc[-1])
            results['ema_7'] = float(df.ta.ema(length=7).iloc[-1])
        except Exception:
            pass

    # Bollinger Bands
    if len(df) > 20:
        try:
            bbands = df.ta.bbands(length=20, std=2)
            if bbands is not None and not bbands.empty:
                results['bb_lower'] = float(bbands.iloc[-1, 0])
                results['bb_middle'] = float(bbands.iloc[-1, 1])
                results['bb_upper'] = float(bbands.iloc[-1, 2])
        except Exception:
            pass

    # Volume Confirmation
    if len(df) > 20:
        try:
            results['vol_sma'] = float(
                df['volume'].rolling(window=20).mean().iloc[-1])
            results['current_vol'] = float(df['volume'].iloc[-1])
            results['vol_prev'] = float(df['volume'].iloc[-2])
        except Exception:
            pass

    # Trend Strength (ADX)
    if len(df) > 14:
        try:
            adx = df.ta.adx(length=14)
            if adx is not None and not adx.empty:
                results['adx'] = float(adx['ADX_14'].iloc[-1])
        except Exception:
            pass

    # ATR (Volatility)
    if len(df) > 14:
        try:
            atr = df.ta.atr(length=14)
            if atr is not None and not atr.empty:
                results['atr'] = float(atr.iloc[-1])
        except Exception:
            pass

    # Fluctuation Factor (Volatility proxy)
    if len(df) > 20:
        try:
            recent = df.tail(20)
            avg_size = (recent['high'] - recent['low']).mean()
            current_price = float(df['close'].iloc[-1])
            results['fluctuation_factor'] = avg_size / \
                (current_price * 0.0002) if current_price > 0 else 1.0

            # Lateral detection (if avg size is too small relative to price)
            results['is_lateral'] = results['fluctuation_factor'] < 0.5 or (
                results.get('adx', 25) < 20)
        except Exception:
            results['fluctuation_factor'] = 1.0
            results['is_lateral'] = False

    return results
