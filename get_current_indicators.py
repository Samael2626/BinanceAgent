import sys
import os
import pandas as pd
from backend.binance_wrapper import BinanceWrapper
from backend.indicators import calculate_indicators


def get_recommendation():
    # Public market data is sufficient for indicators
    client = BinanceWrapper()
    symbols = ["BNBUSDT", "BTCUSDT"]
    timeframe = "1m"  # Default bot timeframe

    settings = {
        'buy_rsi': 21,
        'sell_rsi': 75,
        'ema_length': 200,
        'enable_trend_filter': True,
        'enable_vol_filter': True
    }

    print(f"{'Symbol':<10} | {'Price':<10} | {'RSI':<6} | {'EMA200':<10} | {'Trend':<8}")
    print("-" * 55)

    for symbol in symbols:
        df = client.get_historical_klines(symbol, timeframe, limit=200)
        if df.empty:
            print(f"No data for {symbol}")
            continue

        indicators = calculate_indicators(df, settings)
        price = df['close'].iloc[-1]
        rsi = indicators.get('rsi', 0)
        ema = indicators.get('trend_ema', 0)
        trend = "UP" if price > ema else "DOWN"

        print(
            f"{symbol:<10} | {price:<10.2f} | {rsi:<6.1f} | {ema:<10.2f} | {trend:<8}")

        # Simple recommendation logic based on RSIReboundStrategy
        if rsi < settings['buy_rsi'] and price > ema:
            print(f"  >>> SUGERENCIA: COMPRA (RSI bajo y tendencia alcista)")
        elif rsi < settings['buy_rsi']:
            print(
                f"  >>> INFO: RSI bajo pero precio debajo de EMA (Filtro de tendencia bloquea)")
        else:
            print(
                f"  >>> SUGERENCIA: ESPERAR (Buscando RSI < {settings['buy_rsi']})")
        print()


if __name__ == "__main__":
    get_recommendation()
