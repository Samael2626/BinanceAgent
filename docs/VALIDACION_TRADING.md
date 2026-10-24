# Validacion de trading (2026-10-24)

## Estado

**Gate REAL: ROJO.** No iniciar compras automaticas ni subir esta rama a produccion. La consulta de solo lectura a Binance Spot del 2026-10-24 mostro un saldo inferior al minimo habitual de orden. Los 47 USDT de documentos antiguos son un capital hipotetico para las simulaciones; no son el saldo actual. Esta consulta no cubre Funding ni Earn.

## Datos y costes

- Fuente: archivos mensuales oficiales de Binance Spot. `harness.spot_data` verifica el SHA256 publicado junto a cada ZIP y acepta marcas de tiempo en milisegundos o microsegundos.
- Descarga usada: velas 4h de BTC, ETH, SOL y BNB desde junio de 2024 hasta septiembre de 2026; velas 1m de los ocho simbolos de la lista guardada durante septiembre de 2026.
- Tarifa verificada por API de la cuenta en BTCUSDT, ETHUSDT, SOLUSDT y BNBUSDT: maker y taker 0.1% por lado. Los escenarios de estres suman deslizamiento; son supuestos, no ejecuciones reales.
- Los ZIP, las claves y la instantanea local de configuracion estan excluidos de Git.

## Resultados medidos

La estrategia candidata 4h usa ruptura del maximo de 20 velas sobre EMA200, orden en la apertura siguiente, stop ATR y una sola posicion. Capital simulado: 47 USDT.

| Periodo | Operaciones | PF | Resultado neto | Caida maxima |
| --- | ---: | ---: | ---: | ---: |
| Entrenamiento (junio 2024 a junio 2026) | 49 | 0.49 | -3.21 USDT | 8.12% |
| Reservado (julio a septiembre 2026) | 22 | 1.01 | +0.03 USDT | 3.42% |

El periodo reservado no cumple las 30 operaciones minimas ni la comparacion con el percentil 95 de estrategias aleatorias. El resultado positivo de 0.03 USDT es demasiado pequeno para justificar capital real. No ajustar parametros usando ese periodo.

El replay de la configuracion guardada (`smart_scalping`, 1m, rotacion de ocho activos) utiliza las funciones de indicadores, estrategia, scanner y riesgo del backend. Usa velas cerradas, una cartera, entrada en la apertura siguiente y costes de estres. Es una aproximacion: OHLCV no revela el orden de los ticks dentro de la vela ni reproduce latencia y libro de ordenes. Falta comparar su registro de decisiones con PAPER en tiempo real.

Muestra exploratoria del 2 de septiembre de 2026: 13 operaciones, PF 0.18, neto -0.38 USDT y caida maxima 0.97%. Un dia no sirve para estimar rentabilidad; confirma que la configuracion guardada tampoco merece activarse ahora.

## Barreras implementadas

- El calculo de tamano devuelve cero si el minimo de Binance excede el limite de riesgo; el bot no infla automaticamente la orden.
- Las senales usan velas cerradas.
- Cada orden lleva un `newClientOrderId` unico. Si falla la respuesta, el bot consulta ese identificador. Si el estado sigue incierto, guarda la orden pendiente, se detiene y bloquea nuevos envios. Una orden con ejecucion parcial requiere revision antes de reanudar.

## Reproduccion

Desde la raiz del repositorio, con las dependencias instaladas:

```powershell
python -m harness.spot_data --symbols BTCUSDT ETHUSDT SOLUSDT BNBUSDT --interval 4h --start 2024-06 --end 2026-09 --data-dir harness/data
python -m harness.trend_breakout --data-dir harness/data
python -m harness.config_snapshot --db RUTA_A_LA_BASE_DE_DATOS --output harness/data/config-local.json
python -m harness.spot_data --symbols BTCUSDT ETHUSDT SOLUSDT BNBUSDT XRPUSDT ADAUSDT AVAXUSDT LINKUSDT --interval 1m --start 2026-09 --end 2026-09 --data-dir harness/data
python -m harness.replay_spot --data-dir harness/data --config harness/data/config-local.json --start-month 2026-09 --end-month 2026-09 --start 2026-09-02 --end 2026-09-03
```

Antes de considerar REAL: replay completo de periodos no usados para ajustar, costes y fallos de red bajo estres, comparacion aleatoria predefinida, al menos 30 dias de PAPER con decisiones y ejecuciones cotejadas, pruebas verdes y aprobacion del auditor. Consultar balance Spot justo antes de cualquier decision; la instantanea de julio es obsoleta.
