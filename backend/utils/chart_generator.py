import pandas_ta as ta
import pandas as pd
import io
import mplfinance as mpf
import matplotlib
matplotlib.use('Agg')


def generate_chart(symbol, klines):
    """
    Genera una imagen de gráfico profesional (velas + RSI) usando mplfinance.

    Args:
        symbol: Símbolo del par (ej: 'BTCUSDT')
        klines: Datos históricos de Binance
    """
    try:
        # Convertir klines a DataFrame
        # Convertir klines a DataFrame (Manejo robusto de columnas)
        # Binance devuelve típicamente 12 columnas, pero a veces menos en historiales internos.
        # Solo necesitamos las primeras 6: Time, Open, High, Low, Close, Volume
        df = pd.DataFrame(klines)

        # Seleccionamos solo las primeras 6 columnas y las renombramos
        df = df.iloc[:, :6]
        df.columns = ['time', 'open', 'high', 'low', 'close', 'volume']

        # Tipado y limpieza estricta
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df = df.dropna()  # Eliminar filas corruptas o incompletas

        df.set_index('time', inplace=True)

        # Calcular RSI para el panel inferior usando pandas_ta
        df['RSI'] = ta.rsi(df['close'], length=14)

        # Configuración de estilo premium (Dark Mode)
        mc = mpf.make_marketcolors(
            up='#26a69a', down='#ef5350',
            edge='inherit',
            wick='inherit',
            volume='in',
            ohlc='inherit'
        )

        s = mpf.make_mpf_style(
            base_mpf_style='charles',
            marketcolors=mc,
            gridstyle='dotted',
            y_on_right=True,
            facecolor='#131722',  # Color de fondo similar a TradingView
            edgecolor='#434651',
            figcolor='#131722'
        )

        # Agregar indicadores (RSI en panel separado) con líneas de referencia 70/30
        apds = [
            mpf.make_addplot(df['RSI'], panel=1, color='#2962ff', width=1.5,
                             secondary_y=False, ylim=(0, 100)),
        ]

        # Obtener los últimos valores para mostrarlos en el gráfico
        last_price = df['close'].iloc[-1]
        last_rsi = df['RSI'].iloc[-1]

        # Crear buffer para la imagen
        buf = io.BytesIO()

        # Generar el gráfico minimalista y obtener los ejes para anotar
        fig, axes = mpf.plot(
            df,
            type='candle',
            style=s,
            ylabel='Price',
            volume=False,
            addplot=apds,
            panel_ratios=(2, 0.7),
            figsize=(12, 8),
            hlines=dict(hlines=[30.0, 70.0], colors=[
                        '#434651'], linestyle='dashed', linewidths=1),
            tight_layout=True,
            xrotation=0,
            returnfig=True  # IMPORTANTE: Retornar fig para anotar
        )

        # Anotar el precio actual en el panel principal (axes[0])
        axes[0].text(0.02, 0.95, f'PRICE: {last_price:,.2f}', transform=axes[0].transAxes,
                     fontsize=20, fontweight='bold', color='#ffffff',
                     bbox=dict(facecolor='#131722', alpha=0.8, edgecolor='#26a69a'))

        # Anotar el RSI actual en el panel del RSI (axes[2] o axes[1] dependiendo de mpf)
        # Normalmente axes[0] es el main, [1] es volume (si existe), [2] es el primer addplot
        # Como volume=False, axes[2] debería ser nuestro RSI
        rsi_axis = axes[2]
        rsi_color = '#ef5350' if last_rsi > 70 else (
            '#26a69a' if last_rsi < 30 else '#2962ff')
        rsi_axis.text(0.02, 0.85, f'RSI: {last_rsi:.1f}', transform=rsi_axis.transAxes,
                      fontsize=16, fontweight='bold', color='#ffffff',
                      bbox=dict(facecolor='#131722', alpha=0.8, edgecolor=rsi_color))

        # Guardar la figura final
        fig.savefig(buf, format='png', bbox_inches='tight', dpi=120)
        matplotlib.pyplot.close(fig)  # Limpiar memoria

        buf.seek(0)
        return buf

    except Exception as e:
        print(f"Error generando gráfico: {e}")
        return None
