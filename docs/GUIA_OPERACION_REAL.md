# Guia de operacion real - BinanceAgent

Esta guia explica como arrancar el bot, por que puede no comprar aunque el panel marque zona de compra, y que parametros tocar para operar de forma conservadora o mas agresiva.

> Importante: esto no garantiza ganancias. En cuenta real el capital esta en riesgo. Empieza con montos pequenos y cambia un parametro a la vez.

## 1. Estado minimo para operar

Antes de activar compras reales, confirma:

- Backend activo: `http://127.0.0.1:8000/health`
- Frontend activo: `http://127.0.0.1:5173`
- Login hecho con usuario real.
- `Execution` debe mostrar `REAL` si estas usando cuenta real.
- `BUYING: ON`.
- `SELLING: ON`.
- La API key debe tener permisos de lectura y spot trading.
- No actives retiros en la API key.
- Debe haber saldo USDT suficiente para superar el minimo de Binance.

Con el saldo actual cercano a `47 USDT`, usa operaciones pequenas. No uses todo el balance en una sola orden.

## 2. Por que no compra aunque diga BUY ZONE

El panel `RSI Monitor` es informativo. Marca zonas de RSI por moneda, pero no es la decision final de compra.

La compra automatica depende de la estrategia activa. En el default `RSI Rebound`, el bot compra solo si pasan varias condiciones:

- `RSI < buy_rsi`.
- Precio por encima de la EMA rapida si `enable_fast_ema` esta activo.
- Precio por encima de EMA 200 si `enable_trend_filter` esta activo.
- Volumen actual mayor al promedio si `enable_vol_filter` esta activo.
- Mercado no lateral.
- `market_score >= min_market_score_to_buy`.
- No hay cooldown.
- No se activo el kill-switch.
- La orden cumple filtros de Binance.

Ejemplo real de la pantalla:

- BTC RSI: `36.3`.
- Default del bot: `buy_rsi = 21`.

Resultado: no compra porque `36.3` no es menor que `21`. El panel puede decir `BUY ZONE`, pero la estrategia todavia no tiene senal automatica confirmada.

## 3. Configuracion recomendada para empezar

Perfil prudente para cuenta real pequena:

```text
Timeframe: 15m
Active strategy: rsi_rebound
BUY RSI: 28
SELL RSI: 70-75
Sizing automatico: ON
Risk per trade: 0.5% - 1.0%
Max daily loss: 3% - 5%
Max consecutive losses: 2 - 3
Kill switch global: ON
Portfolio max drawdown: 8% - 12%
Trailing adaptativo: ON
ATR trail mult: 1.25
Trail min: 0.35%
Trail max: 1.8%
```

Conservador significa menos compras, pero menos entradas malas.

## 4. Configuracion mas activa

Usa esto solo si entiendes que aumenta entradas falsas:

```text
Timeframe: 5m o 15m
Active strategy: smart_scalping
BUY RSI: 35
SELL RSI: 70
Min market score to buy: 40 - 45
Risk per trade: 1%
Max daily loss: 5%
Auto asset rotation: ON
Rotation interval: 10 - 15 min
Min rotation score: 55 - 60
```

Si quieres que compre mas seguido con `RSI Rebound`, sube `BUY RSI` de `21` a `30-35`. No recomiendo pasar de `38` al inicio.

## 4.1 Perfil aplicado ahora

Esta es la calibracion aplicada al usuario actual `samael`:

```text
Active strategy: smart_scalping
Timeframe: 15m
BUY RSI: 38
SELL RSI: 70
Volume filter: OFF
Trend filter: ON
Fast EMA filter: ON
Auto position sizing: ON
Risk per trade: 0.75%
Max daily loss: 4%
Max consecutive losses: 2
Stop loss: 2.5%
Take profit: 1.2%
Min market score to buy: 40
Cooldown: 8 min
Auto asset rotation: ON
Rotation interval: 10 min
Min rotation score: 52
Portfolio kill-switch: ON
Portfolio max drawdown: 8%
```

Intencion del perfil:

- Comprar mas seguido que el default `RSI Rebound`.
- Mantener entradas con algo de momentum por MACD y EMA rapida.
- No exigir volumen perfecto, porque en mercado lento bloqueaba casi todo.
- Mantener riesgo bajo por operacion para una cuenta pequena.

## 5. Scanner autonomo de activos

El scanner no compra por si solo. Primero elige el mejor simbolo de la watchlist. Luego la estrategia decide si compra.

Configuracion sugerida:

```text
Auto asset rotation: ON
Rotation interval: 15
Min rotation score: 58
Watchlist: BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT,ADAUSDT,AVAXUSDT,LINKUSDT
```

Reglas del scanner:

- Solo rota si no hay posicion abierta.
- No vende una posicion para saltar a otro activo.
- Exige que el nuevo activo supere el score minimo.
- Exige ventaja contra el activo actual.

## 6. Orden recomendado para operar

1. Inicia backend y frontend.
2. Entra con tu usuario.
3. Verifica `REAL`.
4. Pulsa `Clear PnL` si quieres reiniciar la linea base del dia.
5. Activa `BUYING: ON` y `SELLING: ON`.
6. Usa `Risk per trade` en `0.5%` o `1%`.
7. Configura `BUY RSI`.
8. Deja correr al menos una vela completa del timeframe.
9. Revisa logs si no compra.
10. No fuerces compras manuales si no entiendes la razon de entrada.

## 7. Como interpretar que no compra

Si no compra, revisa en este orden:

1. `RSI` esta por debajo de `BUY RSI`.
2. `Market Score` supera `Score Minimo Compra`.
3. Precio esta por encima de `Fast EMA`.
4. Precio esta por encima de `EMA 200`.
5. Volumen actual supera promedio.
6. No esta en cooldown.
7. Kill-switch no esta activo.
8. Balance USDT supera el minimo de orden.
9. No hay posicion bloqueando mutual exclusion.

## 8. Ajustes rapidos segun comportamiento

Si no compra nunca:

```text
BUY RSI: subir a 30-35
Min market score: bajar a 40-45
Trend filter: mantener ON al inicio
Vol filter: puedes apagarlo si el mercado esta lento
Strategy: probar smart_scalping
```

Si compra demasiado:

```text
BUY RSI: bajar a 25-28
Min market score: subir a 55-60
Rotation score: subir a 62+
Risk per trade: bajar a 0.5%
```

Si entra y sale muy rapido:

```text
Trail min: subir a 0.5%
Trail max: subir a 2.0%
Take profit: subir levemente
Timeframe: usar 15m en vez de 5m
```

Si aguanta perdidas demasiado:

```text
Stop loss: bajar a 2.0% - 2.5%
Max consecutive losses: 2
Max daily loss: 3%
Portfolio max drawdown: 8%
```

## 9. Botones importantes

`HALT SYSTEM`

Detiene ejecucion automatica. Usalo si ves comportamiento raro.

`BUYING: ON/OFF`

Permite o bloquea compras. Puede estar en ON y aun asi no comprar si no hay senal.

`SELLING: ON/OFF`

Permite o bloquea ventas automaticas. En real, normalmente debe estar ON.

`Reset Pos`

Resetea estado interno de posicion. No vende por si mismo. Usalo solo si el bot quedo desincronizado con Binance.

`Clear PnL`

Reinicia linea base de PnL y tambien limpia el estado del kill-switch.

## 10. Regla operativa

No interpretes `BUY ZONE` como orden de compra. Interpretalo como "esta moneda merece atencion". La compra real ocurre cuando la estrategia confirma RSI, tendencia, momentum, volumen, score y riesgo.

Para el estado actual de la captura, el motivo principal de no compra es:

```text
BTC RSI = 36.3
BUY RSI default = 21
36.3 no cumple RSI < 21
```

Si quieres que el bot sea mas activo, cambia `BUY RSI` a `30-35` o usa `smart_scalping`, pero manten `Risk per trade` bajo.
