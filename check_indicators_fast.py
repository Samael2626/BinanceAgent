import requests
import pandas as pd
import pandas_ta as ta


def check_now():
    symbols = ["BNBUSDT", "BTCUSDT"]
    print(f"{'Symbol':<10} | {'Price':<10} | {'RSI':<6} | {'EMA200':<10} | {'Trend':<8}")
    print("-" * 55)

    for symbol in symbols:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=200"
        try:
            r = requests.get(url, timeout=10)
            data = r.json()
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            df['close'] = pd.to_numeric(df['close'])

            rsi = df.ta.rsi(length=14).iloc[-1]
            ema = df.ta.ema(length=200)
            ema_val = ema.iloc[-1] if ema is not None and not ema.empty else 0
            price = df['close'].iloc[-1]
            trend = "UP" if price > ema_val else "DOWN"

            print(
                f"{symbol:<10} | {price:<10.2f} | {rsi:<6.1f} | {ema_val:<10.2f} | {trend:<8}")
        except Exception as e:
            print(f"Error {symbol}: {e}")


if __name__ == "__main__":
    check_now()
