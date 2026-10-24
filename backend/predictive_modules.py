import pandas as pd
import numpy as np
from datetime import datetime, time as dtime
import pytz


class PredictiveEngine:
    """
    Motor Predictivo Avanzado para el Bot de Trading.

    Este módulo analiza el mercado buscando patrones específicos:
    - Divergencias de RSI (Señales tempranas de reversión).
    - RVOL (Volumen Relativo): Detecta actividad inusual.
    - Zonas de Liquidez: Dónde están los precios clave (soportes/resistencias).
    - Estado del Mercado: Puntuación general de salud (0-100).
    - Sesión de Mercado: Qué mercado global está activo (Asia, Londres, NY).
    """

    # --- CONSTANTES DE CONFIGURACIÓN ---
    RSI_PERIOD = 14
    RSI_OVERBOUGHT = 70
    RSI_OVERSOLD = 30
    VOL_WINDOW = 20  # Ventana para calcular promedio de volumen
    RVOL_THRESHOLD = 1.2  # Volumen 20% superior al promedio se considera alto
    COMPRESSION_THRESHOLD = 1.5  # Umbral para detectar compresión de bandas
    PROJECTION_CANDLES = 5  # Cuántas velas proyectar a futuro

    def __init__(self):
        self.last_price_update = datetime.now()
        self.last_price = 0.0
        # Almacena tuplas (timestamp, precio) para calcular velocidad
        self.speed_buffer = []

    def analyze(self, df: pd.DataFrame, current_price: float) -> dict:
        """
        Punto de entrada principal del análisis.
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
            "speed": self._calculate_speed(current_price),
            "volatility": self._calculate_volatility_atr(df),
            "trend_strength": self._calculate_trend_strength_adx(df),
            "fear_greed": self._calculate_fear_greed(df),
            "smart_money": self._calculate_smart_money_flow(df)
        }

        # Proyección, Trampas y Resumen
        results['projection'] = self._calculate_simple_projection(df)
        results['traps'] = self._detect_traps(df)
        results['summary'] = self.get_readable_summary(results)

        return results

    def _calculate_volatility_atr(self, df: pd.DataFrame) -> dict:
        """Calcula ATR (Average True Range) para medir volatilidad real."""
        if len(df) < 15:
            return {"value": 0, "status": "Baja"}

        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()

        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]

        # Determinar si la volatilidad está subiendo
        avg_atr = tr.rolling(50).mean().iloc[-1]
        status = "Alta 📉" if atr > avg_atr * \
            1.2 else ("Baja 💤" if atr < avg_atr * 0.8 else "Normal")

        return {"value": float(atr), "status": status}

    def _calculate_trend_strength_adx(self, df: pd.DataFrame) -> dict:
        """Estima la fuerza de la tendencia (estilo ADX)."""
        # Simplificamos: Relación entre distancia de EMA y precio
        if 'EMA_200' not in df.columns:
            return {"score": 50, "label": "Neutral"}

        close = df['close'].iloc[-1]
        ema = df['EMA_200'].iloc[-1]
        if pd.isna(ema) or ema <= 0:
            return {"score": 50, "label": "Neutral"}
        dist = abs(close - ema) / ema * 100

        score = min(100, dist * 10)  # 10% de distancia = 100 score
        label = "Fuerte" if score > 70 else (
            "Débil" if score < 30 else "Media")

        return {"score": int(score), "label": label}

    def _calculate_fear_greed(self, df: pd.DataFrame) -> dict:
        """Estima sentimiento de Miedo vs Codicia basado en RSI y Volatilidad."""
        rsi = df[f'RSI_{self.RSI_PERIOD}'].iloc[-1] if f'RSI_{self.RSI_PERIOD}' in df.columns else 50
        if pd.isna(rsi):
            rsi = 50

        score = rsi  # Base
        if rsi > 75:
            label = "Extrema Codicia 🤑"
        elif rsi > 60:
            label = "Codicia"
        elif rsi < 25:
            label = "Extremo Miedo 😨"
        elif rsi < 40:
            label = "Miedo"
        else:
            label = "Neutral"

        return {"score": int(score), "label": label}

    def _calculate_smart_money_flow(self, df: pd.DataFrame) -> str:
        """Detecta flujo de dinero (Smart Money) usando OBV (On Balance Volume)."""
        if 'volume' not in df.columns:
            return "Neutral"

        obv = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
        obv_ema = obv.rolling(20).mean()

        curr_obv = obv.iloc[-1]
        curr_ema = obv_ema.iloc[-1]

        if curr_obv > curr_ema * 1.05:
            return "Acumulación (Compra ✅)"
        if curr_obv < curr_ema * 0.95:
            return "Distribución (Venta ❌)"
        return "Neutral"

    def get_readable_summary(self, results: dict) -> str:
        """
        Genera un resumen en texto plano (Español) de las predicciones.
        Ideal para mostrar en logs o enviar por Telegram.
        """
        summ = []

        # 1. Score de Mercado
        score = results.get('market_score', 50)
        sentiment = "Neutral"
        if score > 65:
            sentiment = "Alcista Fuerte 🚀"
        elif score > 55:
            sentiment = "Alcista Moderado 📈"
        elif score < 35:
            sentiment = "Bajista Fuerte 🩸"
        elif score < 45:
            sentiment = "Bajista Moderado 📉"
        summ.append(f"• Estado: {sentiment} (Score: {score}/100)")

        # 2. Sentimiento y Dinero Inteligente
        fg = results.get('fear_greed', {})
        sm = results.get('smart_money', 'Neutral')
        summ.append(
            f"• Sentimiento: {fg.get('label', 'Neutral')} (Score: {fg.get('score', 50)})")
        summ.append(f"• Flujo Institucional: {sm}")

        # 3. Fuerza de Tendencia y Volatilidad
        trend = results.get('trend_strength', {})
        vol = results.get('volatility', {})
        summ.append(
            f"• Tendencia: {trend.get('label', 'Media')} (Fuerza: {trend.get('score', 0)}%)")
        summ.append(f"• Volatilidad: {vol.get('status', 'Normal')}")

        # 4. Volumen Relativo
        rvol = results.get('rvol', 0)
        if rvol > self.RVOL_THRESHOLD:
            summ.append(f"• Actividad: Inusual ({rvol}x promedio).")

        # 5. Divergencias y Ruptura
        divs = results.get('divergences', [])
        if divs:
            summ.append(
                f"• Divergencias: ⚠️ {', '.join([d['label'] for d in divs])}")

        prob = results.get('breakout_prob', 0)
        if prob > 60:
            summ.append(
                f"• Prob. Ruptura: Alta ({prob}%) - Compresión detectada.")

        # 6. Rangos Clave
        zones = results.get('liquidity_zones', {})
        if zones:
            summ.append(
                f"• Rango Operativo: ${zones.get('support', 0):,.2f} - ${zones.get('target', 0):,.2f}")

        if not summ:
            return "Sin señales predictivas claras."

        return "\n".join(summ)

    def _detect_divergences(self, df: pd.DataFrame) -> list:
        """
        Detecta Divergencias de RSI en las últimas 20 velas.

        Una divergencia ocurre cuando el precio y el RSI van en direcciones opuestas.
        - Alcista: Precio hace bajos más bajos, pero RSI hace bajos más altos (Fuerza subyacente).
        - Bajista: Precio hace altos más altos, pero RSI hace altos más bajos (Debilidad subyacente).
        """
        column_rsi = f'RSI_{self.RSI_PERIOD}'
        if column_rsi not in df.columns:
            return []

        divergences = []
        window = 20
        subset = df.iloc[-window:].copy().reset_index(drop=True)

        if len(subset) < window:
            return []

        prices = subset['close'].values
        rsis = subset[column_rsi].values

        # Buscamos PIVOTS (puntos de giro local)
        # Low Pivot: Una vela con velas más altas a izquierda y derecha.
        # High Pivot: Una vela con velas más bajas a izquierda y derecha.
        lows = []
        highs = []

        for i in range(2, len(subset) - 2):
            # Encontrar Bajos (Lows)
            if prices[i] < prices[i-1] and prices[i] < prices[i+1]:
                lows.append((i, prices[i], rsis[i]))

            # Encontrar Altos (Highs)
            if prices[i] > prices[i-1] and prices[i] > prices[i+1]:
                highs.append((i, prices[i], rsis[i]))

        # Verificar Divergencia Alcista (Bullish)
        # Condición: Precio más bajo que el anterior bajo, PERO RSI más alto que el anterior RSI.
        if len(lows) >= 2:
            last_l = lows[-1]  # Último bajo
            prev_l = lows[-2]  # Penúltimo bajo

            if last_l[1] < prev_l[1] and last_l[2] > prev_l[2]:
                divergences.append({
                    "type": "bullish",
                    "label": "Div Alcista (Bull)",
                    "index": int(last_l[0])
                })

        # Verificar Divergencia Bajista (Bearish)
        # Condición: Precio más alto que el anterior alto, PERO RSI más bajo que el anterior RSI.
        if len(highs) >= 2:
            last_h = highs[-1]
            prev_h = highs[-2]

            if last_h[1] > prev_h[1] and last_h[2] < prev_h[2]:
                divergences.append({
                    "type": "bearish",
                    "label": "Div Bajista (Bear)",
                    "index": int(last_h[0])
                })

        return divergences

    def _calculate_rvol(self, df: pd.DataFrame) -> float:
        """
        Calcula Volumen Relativo (RVOL).

        RFormula: Volumen Actual / Promedio de Volumen de las últimas 20 velas.
        """
        if 'volume' not in df.columns:
            return 0.0

        avg_vol = df['volume'].rolling(window=self.VOL_WINDOW).mean().iloc[-1]
        current_vol = df['volume'].iloc[-1]

        if avg_vol == 0:
            return 0.0

        return round(current_vol / avg_vol, 2)

    def _calculate_breakout_prob(self, df: pd.DataFrame) -> float:
        """
        Calcula la probabilidad de una ruptura (explosión de precio) (0-100%).

        Basado en:
        1. Volumen creciente (Interés).
        2. Baja Volatilidad (Compresión de Bandas de Bollinger).
        3. RSI no sobreextendido (Espacio para correr).
        """
        rvol = self._calculate_rvol(df)

        # Compresión de Volatilidad (Ancho de Bandas de Bollinger / Promedio)
        if 'BBU_20_2.0' in df.columns and 'BBL_20_2.0' in df.columns:
            bb_width = (df['BBU_20_2.0'].iloc[-1] - df['BBL_20_2.0'].iloc[-1])
            avg_width = (df['BBU_20_2.0'] - df['BBL_20_2.0']
                         ).rolling(20).mean().iloc[-1]
            # Si el ancho actual es mucho menor al promedio, hay compresión.
            compression = avg_width / bb_width if bb_width > 0 else 1.0
        else:
            compression = 1.0

        score = 0
        if rvol > self.RVOL_THRESHOLD:
            score += 40  # Buen volumen = combustible
        if compression > self.COMPRESSION_THRESHOLD:
            score += 40  # Alta compresión = muelle cargado

        column_rsi = f'RSI_{self.RSI_PERIOD}'
        rsi = df[column_rsi].iloc[-1] if column_rsi in df.columns else 50
        if pd.isna(rsi):
            rsi = 50

        # Si el RSI está en zona neutral (40-60), hay espacio para moverse.
        if 40 <= rsi <= 60:
            score += 20

        return min(score, 100)

    def _find_liquidity_zones(self, df: pd.DataFrame) -> dict:
        """
        Identifica zonas de liquidez (Soportes y Resistencias recientes).

        Utiliza los máximos y mínimos de las últimas 50 velas para determinar
        dónde el precio ha rebotado.
        """
        recent = df.iloc[-50:]

        # Soporte: El nivel más bajo reciente (donde entraron compradores)
        support = recent['low'].min()

        # Resistencia: El nivel más alto reciente (donde entraron vendedores)
        target = recent['high'].max()

        return {
            "support": float(support),
            "target": float(target)
        }

    def _calculate_market_score(self, df: pd.DataFrame) -> int:
        """
        Puntuación compuesta de salud del mercado (0-100).
        > 50: Tendencia Positiva.
        < 50: Tendencia Negativa.
        """
        score = 50
        column_rsi = f'RSI_{self.RSI_PERIOD}'

        # Componente RSI
        rsi = df[column_rsi].iloc[-1] if column_rsi in df.columns else 50
        if pd.isna(rsi):
            rsi = 50
        if rsi > 50:
            score += 10
        if rsi > self.RSI_OVERBOUGHT:
            score -= 20  # Sobrecompra (Riesgo de caída)
        if rsi < self.RSI_OVERSOLD:
            score += 20  # Sobreventa (Potencial rebote)

        # Componente de Tendencia (EMA)
        close = df['close'].iloc[-1]
        ema = df['EMA_200'].iloc[-1] if 'EMA_200' in df.columns else close
        if pd.isna(ema):
            ema = close
        if close > ema:
            score += 20  # Precio sobre la media de 200 = Tendencia Alcista sana
        else:
            score -= 20  # Precio bajo la media de 200 = Tendencia Bajista

        return max(0, min(100, score))

    def _get_market_session(self) -> str:
        """Determina qué sesión de mercado principal está activa (Asia, Londres, NY)."""
        now = datetime.now(pytz.utc)
        hour = now.hour

        # Mapeo aproximado de sesiones (UTC)
        # Asia: 00:00 - 09:00
        # Londres: 07:00 - 16:00
        # NY: 13:00 - 22:00

        sessions = []
        if 0 <= hour < 9:
            sessions.append("ASIA")
        if 7 <= hour < 16:
            sessions.append("LONDRES")
        if 13 <= hour < 22:
            sessions.append("NY")

        if not sessions:
            return "GLOBAL (Cierre)"

        return " & ".join(sessions)

    def _calculate_speed(self, current_price: float) -> str:
        """
        Calcula la velocidad del precio (% de cambio en los últimos 10 segundos).
        Útil para detectar 'pump' o 'dumps' repentinos.
        """
        now = datetime.now()

        # Limpiar buffer (eliminar datos con antigüedad > 10s)
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
        """
        Proyecta el precio a futuro (5 velas) basado en la inercia actual (regresión lineal).
        Nota: Esto es una estimación matemática simple, no una profecía.
        """
        try:
            recent = df['close'].iloc[-self.PROJECTION_CANDLES:].values
            if len(recent) < self.PROJECTION_CANDLES:
                return []

            # Calcular pendiente (Slope)
            x = np.arange(self.PROJECTION_CANDLES)
            y = recent
            slope, intercept = np.polyfit(x, y, 1)

            last_time = int(
                df.iloc[-1]['time']) if 'time' in df.columns else int(df.index[-1].timestamp())
            start_price = recent[-1]

            projection = []

            # Proyectar
            for i in range(1, self.PROJECTION_CANDLES + 1):
                next_price = start_price + (slope * i)
                # Asumimos intervalo de 1 minuto (60s) para la visualización
                next_time = last_time + (i * 60)
                projection.append({"time": next_time, "value": next_price})

            return projection
        except Exception:
            return []

    def _detect_traps(self, df: pd.DataFrame) -> list:
        """
        Detecta Trampas de Toro (Bull Trap) o de Oso (Bear Trap) en la última vela.

        - Bull Trap: El precio rompe un máximo previo pero cierra por debajo (rechazo).
        - Bear Trap: El precio rompe un mínimo previo pero cierra por encima (recuperación).
        """
        traps = []
        if len(df) < 3:
            return traps

        curr = df.iloc[-1]
        prev = df.iloc[-2]

        # Bull Trap (Trampa Alcista)
        # El precio superó el alto anterior intradía, pero cerró peor que el cierre anterior.
        if curr['high'] > prev['high'] and curr['close'] < prev['close']:
            traps.append("BULL_TRAP")

        # Bear Trap (Trampa Bajista)
        # El precio cayó bajo el mínimo anterior intradía, pero cerró mejor que el cierre anterior.
        if curr['low'] < prev['low'] and curr['close'] > prev['close']:
            traps.append("BEAR_TRAP")

        return traps
