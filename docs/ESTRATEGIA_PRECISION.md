# 🎯 Estrategia Multi-Indicador (Alta Precisión)

Esta estrategia ha sido diseñada para minimizar las "falsas alarmas" del mercado y operar con una mayor probabilidad de éxito, combinando confirmación de tendencia, impulso y niveles de sobreventa.

## 🛠️ Los 3 Pilares de la Estrategia

Para que el bot ejecute una operación, deben alinearse tres indicadores técnicos distintos:

### 1. Media Móvil Exponencial (EMA 200) - "El Filtro de Tendencia"
- **Función**: Identifica la tendencia de largo plazo.
- **Regla**: Solo compramos si el precio actual está **por encima** de la EMA 200. 
- **Por qué?**: Esto asegura que solo estamos operando a favor de la tendencia alcista principal, evitando entrar cuando el mercado está en caída libre.

### 2. Relative Strength Index (RSI) - "El Timing de Entrada"
- **Función**: Mide la velocidad y el cambio de los movimientos de precios para identificar condiciones de sobrecompra o sobreventa.
- **Regla**: Buscamos niveles de sobreventa (ej. RSI < 30).
- **Por qué?**: Nos indica que el precio ha bajado "demasiado" y es probable un rebote técnico.

### 3. MACD Histogram - "La Confirmación de Fuerza"
- **Función**: Confirma si el cambio de tendencia tiene fuerza real.
- **Regla**: Solo entramos si el histograma del MACD es **positivo (> 0)**.
- **Por qué?**: El RSI puede estar bajo durante mucho tiempo mientras el precio sigue cayendo. El MACD nos confirma que el impulso está empezando a girar a favor de los compradores.

---

## 📈 Lógica de Operación

### ✅ Condiciones para COMPRAR
1. **Precio > EMA 200** (Tendencia Alcista ✅)
2. **RSI < 30** (Precio en Descuento ✅)
3. **MACD Histograma > 0** (Confirmación de Rebote ✅)

> [!IMPORTANT]
> Deben cumplirse las **3 condiciones simultáneamente**. Si falta una, el bot esperará pacientemente.

### ❌ Condiciones para VENDER
El bot cerrará la operación si ocurre **cualquiera** de estas condiciones:
1. **RSI > 70**: El activo está sobrecomprado y es momento de tomar ganancias.
2. **MACD Histograma < 0**: El impulso alcista se ha agotado y el precio podría empezar a caer.
3. **Stop Loss**: Si el precio cae un % determinado (configurado en el panel) desde el precio de entrada.

---

## ⚙️ Configuración Técnica
- **Ventana de Datos**: El bot descarga las últimas **300 velas** de 1 minuto para asegurar que la EMA 200 sea extremadamente precisa.
- **Símbolo**: BTC/USDT (configurable).
- **Entorno**: Funciona tanto en Testnet como en Mainnet de Binance.

---

## 🚀 Cómo Activarla
1. Ve al panel de **Configuración de Trading**.
2. En el menú desplegable de **Estrategia Activa**, selecciona:  
   `Multi-Indicador (RSI + MACD + EMA - Precisión)`.
3. Haz clic en **Start Trading**.

![Dashboard](file:///C:/Users/HOME/.gemini/antigravity/brain/6a29c939-d60e-465a-aeda-3a70d0ebced4/binance_bot_multi_strategy_verified_1767541312508.png)
