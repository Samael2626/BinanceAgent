
from predictive_modules import PredictiveEngine
import sys
import os
import pandas as pd
import numpy as np

# Add backend to path to import modules
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'backend')))


def create_dummy_data():
    """Crea un DataFrame de prueba con datos que deberían disparar señales."""
    dates = pd.date_range("2024-01-01", periods=100, freq="1min")
    df = pd.DataFrame({
        "time": dates,
        "open": 100.0,
        "high": 105.0,
        "low": 95.0,
        "close": 100.0,
        "volume": 1000.0
    })

    # 1. Simular Divergencia Alcista: Precio baja, RSI sube
    prices = np.linspace(100, 90, 20)
    rsis = np.linspace(30, 40, 20)

    # Simular Volumen Alto
    volumes = np.linspace(1000, 1000, 20)
    volumes[-1] = 5000  # 5x promedio

    df.iloc[-20:, df.columns.get_loc('close')] = prices
    df.iloc[-20:, df.columns.get_loc('volume')] = volumes

    for i in range(-20, 0):
        curr_price = df.iloc[i]['close']
        if i % 2 == 0:
            df.iloc[i, df.columns.get_loc('low')] = curr_price - 1
        else:
            df.iloc[i, df.columns.get_loc('high')] = curr_price + 1

    df['RSI_14'] = 50.0
    df.iloc[-20:, df.columns.get_loc('RSI_14')] = rsis

    df['EMA_200'] = 95.0
    df['BBU_20_2.0'] = 110.0
    df['BBL_20_2.0'] = 90.0

    return df


def test_readable_summary():
    try:
        engine = PredictiveEngine()
        df = create_dummy_data()

        print("--- Ejecutando Análisis de Prueba ---")
        current_price = df['close'].iloc[-1]

        results = engine.analyze(df, current_price)

        print("\n[RESULTADOS CRUDOS]")
        print(list(results.keys()))

        print("\n[RESUMEN LEGIBLE GENERADO]")
        print("-" * 40)
        print(results.get('summary', 'No Summary Found'))
        print("-" * 40)
    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    test_readable_summary()
