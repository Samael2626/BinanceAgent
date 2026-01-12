# Guía Profesional de Estrategias de Trading

Esta documentación detalla las estrategias implementadas en el bot, sus indicadores, lógica de entrada/salida y gestión de riesgos.

---

## 1. RSI Rebound (Rebote RSI)

Estrategia diseñada para capturar reversiones en niveles extremos de sobreventa o sobrecompra.

### Lógica de Entrada
- **Condición Principal**: RSI < `buy_rsi` (por defecto 30).
- **Confirmación**: Cruce alcista de medias rápidas (`ema_2` > `ema_7`). Refleja el inicio del rebote.
- **Filtro Lateral**: Se ignora si el mercado está en lateralidad (ADX < 20).

### Lógica de Salida
- **Salida por RSI**: RSI > `sell_rsi` (por defecto 70).
- **Stop Loss**: Porcentaje fijo definido en ajustes.
- **Take Profit**: Porcentaje fijo definido en ajustes.

### Riesgos y Limitaciones
- **Falsos Rebotes**: En tendencias bajistas fuertes, el RSI puede permanecer en sobreventa mientras el precio sigue cayendo.
- **Mercado Tendencial**: Sufre en tendencias fuertes sin retrocesos.

---

## 2. Breakout Volume (Ruptura por Volumen)

Estrategia de seguimiento de tendencia que busca rupturas de rango confirmadas por un aumento significativo en la actividad.

### Lógica de Entrada
- **Condición Principal**: El precio de cierre cruza por encima de la Banda de Bollinger Superior (`bb_upper`).
- **Confirmación**: El volumen actual es al menos 1.5 veces mayor al promedio de las últimas 20 velas (`vol_sma`).
- **Filtro Lateral**: Solo opera si hay volatilidad suficiente.

### Lógica de Salida
- **Stop Dinámico**: Venta inmediata si el precio cae por debajo de la Media de Bollinger (`bb_middle`).
- **Take Profit**: Generalmente busca movimientos rápidos de ruptura.

### Riesgos y Limitaciones
- **Fakeouts**: Rupturas falsas que regresan rápidamente al rango.
- **Slippage**: El alto volumen puede venir acompañado de mayor spread.

---

## 3. Smart Scalper (Scalping Inteligente)

Estrategia de alta frecuencia que combina momentum y micro-tendencias.

### Lógica de Entrada
- **Condición Principal**: RSI en zona neutral-baja (< 40).
- **Confirmación**: Histograma del MACD positivo (impulso alcista).
- **Filtro**: Alta liquidez preferida.

### Lógica de Salida
- **Trailing Stop**: Obligatorio. Protege las ganancias mientras el precio sube.
- **RSI High**: Salida rápida si el RSI sube sobre 60.

### Riesgos y Limitaciones
- **Comisiones**: Al ser de alta frecuencia, las comisiones de Binance pueden erosionar la ganancia neta si no se calibran bien los objetivos.
- **Ruido de Mercado**: Muy sensible a micro-fluctuaciones.

---

## Principios de Gestión de Riesgo (Core)

1. **Ganancia Neta Positiva**: El bot valida que el beneficio cubra las comisiones de entrada (0.1%) y salida (0.1%) antes de vender por estrategia (excepto en Stop Loss).
2. **Reset Total**: Tras cada venta exitosa o Stop Loss, se limpian todos los residuos de estado para evitar arrastrar errores a la siguiente operación.
3. **Filtro Anti-Lateralidad**: El indicador ADX actúa como guardián universal para evitar "comprar el suelo" en mercados muertos.
