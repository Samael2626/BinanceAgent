# PAPER con precios ejecutables

PAPER es una cuenta virtual independiente de Binance Testnet y de la cuenta REAL. Se crea desde el registro sin claves API. Usa velas y libro de ordenes publicos de Binance Spot Mainnet; nunca llama a `create_order`. El capital inicial se elige al registrar la cuenta; el valor propuesto de **47 USDT virtuales** solo permite comparar con las simulaciones previas. El saldo virtual persiste al reiniciar y no refleja fondos de Binance.

## Ejecucion

- Compra MARKET al lado ask; venta MARKET al lado bid. Consume hasta 20 niveles del libro. Si falta profundidad, el simbolo no opera o los filtros de Binance no estan disponibles, rechaza la orden.
- Aplica 2 puntos basicos de movimiento adverso adicional por lado para modelar latencia. Rechaza un libro cuya consulta tarde mas de 2 segundos. El spread y la profundidad salen del libro observado, no de una vela media.
- Cobra 0.1% por lado por defecto, tarifa Spot verificada para la cuenta al preparar la investigacion. En compra descuenta la comision del activo recibido; en venta descuenta USDT del importe recibido. No presupone descuento por BNB. `paper_fee_pct` y `paper_latency_bps` son ajustes por usuario, limitados a 0-1% y 0-100 puntos basicos.
- Aplica filtros de simbolo `LOT_SIZE`, `MARKET_LOT_SIZE` y `NOTIONAL` mediante el validador del cliente. Rechaza saldo insuficiente. Una orden con el mismo `clientOrderId` devuelve el resultado ya guardado sin gastar dos veces.
- Registra precio de cada nivel consumido, mejor bid/ask, ID de actualizacion del libro, tiempo de consulta, comision, cantidad, coste y saldo. El endpoint autenticado `GET /api/paper/report` entrega la cartera virtual y todas las ordenes.
- El bot calcula el precio de entrada incluyendo la comision de compra y el PnL de venta neto de ambas comisiones.

## Alcance de la simulacion

Este modelo aproxima una orden MARKET pequena. El libro REST no incluye la hora exacta de cada nivel: el ID de actualizacion y la duracion de consulta quedan registrados, pero no permiten reconstruir la liquidez que habia en el instante de la senal. Los 2 puntos basicos adicionales son un supuesto; deslizamientos y fallos reales pueden ser mayores. No simula desconexiones del socket, rechazos inesperados del exchange, cortes de red entre envio y respuesta, ni cambios de tarifa o descuentos BNB. Comparar el registro PAPER con datos observados y ejecutar pruebas de estres antes de cualquier gate REAL.

## Verificacion y siguiente gate

`python tests/test_paper_broker.py` comprueba spread, comisiones, profundidad, filtros, persistencia, reintentos idempotentes y coincidencia entre PnL y saldo. `python tests/test_paper_registration.py` comprueba el registro sin claves y la validacion del capital. `npm run build` verifica la interfaz. Mantener PAPER al menos 30 dias, con las mismas reglas del bot, sin reajustar parametros al mirar resultados. Evaluar operaciones netas, factor de beneficio, caida maxima, errores de datos, rechazos y deslizamiento observado. El gate REAL permanece cerrado y las compras reales siguen bloqueadas en codigo.
