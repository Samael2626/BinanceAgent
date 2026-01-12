
import io
import pandas as pd
import matplotlib
import sys
import os

# Add current dir to path
sys.path.append(os.getcwd())

matplotlib.use('Agg')

try:
    from backend.utils.chart_generator import generate_chart
    print("generate_chart imported successfully")
except Exception as e:
    print(f"Error importing generate_chart: {e}")
    sys.exit(1)

# Mock klines (12 columns)
mock_klines = []
for i in range(100):
    t = 1704067200000 + (i * 900000)
    p = 42000.0 + (i * 5)
    mock_klines.append([t, str(p), str(p+100), str(p-50), str(p+20),
                       "100.0", t+900000, "4200000.0", 500, "50.0", "2100000.0", "0"])

print("Testing generate_chart with annotations...")
try:
    buf = generate_chart("BTCUSDT", mock_klines)
    if buf:
        print("Chart generated successfully!")
        with open("annotated_chart.png", "wb") as f:
            f.write(buf.getbuffer())
        print("Saved to annotated_chart.png")
    else:
        print("Failed to generate chart.")
except Exception as e:
    print(f"Exception during generate_chart: {e}")
    import traceback
    traceback.print_exc()
