# Agentes especializados de BinanceAgent

Estos agentes son skills personales instaladas en:

`C:\Users\USUARIO\.agents\skills`

Sirven para que Codex active especialistas segun el tipo de trabajo del bot.

## Agentes creados

### `binanceagent-risk-manager`

Para riesgo real: drawdown, kill-switch, stop loss, take profit, position sizing, perdida diaria y limites de cuenta.

Usalo cuando digas cosas como:

- "calibra el riesgo"
- "sube o baja el tamano de posicion"
- "revisa el kill-switch"
- "quiero operar real pero protegido"

### `binanceagent-signal-strategist`

Para senales: RSI, EMA, MACD, volumen, score de mercado, estrategias y frecuencia de compras/ventas.

Usalo cuando digas:

- "por que no compra"
- "hazlo mas constante"
- "calibra las entradas"
- "mejora smart_scalping"

### `binanceagent-execution-guardian`

Para ejecucion real con Binance API: permisos, ordenes, filtros de simbolo, min notional, balances y errores de API.

Usalo cuando digas:

- "fallo una orden"
- "revisa Binance API"
- "no ejecuta compras reales"
- "valida permisos y filtros"

### `binanceagent-autonomy-scanner`

Para autonomia: scanner, rotacion automatica de activos, watchlist, ranking de monedas y seleccion de oportunidades.

Usalo cuando digas:

- "que opere solo"
- "elige la mejor moneda"
- "mejora la rotacion"
- "revisa el scanner"

### `binanceagent-ops-runbook`

Para operacion diaria: arrancar, detener, login, logs, health, status, troubleshooting y documentacion.

Usalo cuando digas:

- "como lo acciono"
- "arranca el bot"
- "mira los logs"
- "documenta en vault"

### `binanceagent-ui-controls`

Para interfaz: dashboard, controles, settings, botones, estados visibles y experiencia de operacion real.

Usalo cuando digas:

- "mejora la interfaz"
- "agrega controles"
- "muestra por que no compra"
- "haz mas claro el modo real"

## Regla de seguridad

Ningun agente debe prometer ganancias ni desactivar protecciones criticas por defecto. En cuenta real, el orden correcto es:

1. Proteger capital.
2. Explicar por que compra o no compra.
3. Aumentar frecuencia de operaciones gradualmente.
4. Verificar con logs, status y pruebas.

## Estado actual recomendado

El bot ya tiene modo REAL configurado, scanner, risk engine, kill-switch y guia operativa. Para cambios futuros, conviene llamar al agente por dominio:

- Senales: `binanceagent-signal-strategist`
- Riesgo: `binanceagent-risk-manager`
- Ejecucion Binance: `binanceagent-execution-guardian`
- Autonomia: `binanceagent-autonomy-scanner`
- Operacion/docs: `binanceagent-ops-runbook`
- UI: `binanceagent-ui-controls`
