
import pandas_ta as ta
import mplfinance as mpf
import io
import pandas as pd
import matplotlib
import sys
import os

# Add current dir to path
sys.path.append(os.getcwd())

matplotlib.use('Agg')

# Mock klines (12 columns)
mock_klines = []
for i in range(100):
    t = 1704067200000 + (i * 900000)
    p = 42000.0 + (i * 5)
    mock_klines.append([t, str(p), str(p+100), str(p-50), str(p+20),
                       "100.0", t+900000, "4200000.0", 500, "50.0", "2100000.0", "0"])

df = pd.DataFrame(mock_klines).iloc[:, :6]
df.columns = ['time', 'open', 'high', 'low', 'close', 'volume']
df['time'] = pd.to_datetime(df['time'], unit='ms')
for col in ['open', 'high', 'low', 'close', 'volume']:
    df[col] = pd.to_numeric(df[col], errors='coerce')
df.set_index('time', inplace=True)
df['RSI'] = ta.rsi(df['close'], length=14)

apds = [mpf.make_addplot(df['RSI'], panel=1, color='#2962ff',
                         width=1.5, secondary_y=False, ylim=(0, 100))]
fig, axes = mpf.plot(df, type='candle', volume=False,
                     addplot=apds, returnfig=True)
print(f"Number of axes: {len(axes)}")
for i, ax in enumerate(axes):
    print(f"Axis {i}: {ax}")
