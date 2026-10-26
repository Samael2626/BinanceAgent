# Kronos Futures: validacion de REAL

Estado: **ROJO**. Holdout congelado: 2026-07-01 00:00 a 2026-10-25 00:00 UTC (fin exclusivo). No ajustar parametros con ese periodo.

La tabla local de `samael` tiene 0 operaciones. Su winrate REAL verificable es indefinido; no se verifico historial remoto del exchange. La configuracion local observada es `smart_scalping`, `1m`, rotacion cada 10 minutos. El perfil objetivo esta en `docs/kronos_futures_target.json` y no modifica la cuenta.

El antiguo `harness.run_kronos_futures` queda bloqueado: leia velas Spot, creaba una billetera por simbolo, suponia funding y agregaba resultados con una cartera proxy. No autoriza REAL. El replay nuevo implementa una billetera global, seleccion por EV, 1m, coste taker stress, stop prioritario y funding real. Su salida es descriptiva hasta verificar paridad completa.

Datos verificados el 2026-10-25: para cada uno de los siete simbolos, 3504 velas Futures 1h (desde junio), 167040 velas Futures 1m y 348 liquidaciones de funding dentro del holdout. Checksums y secuencia UTC exacta guardados en `harness/data/futures_um/holdout_manifest.json` (cache ignorada por Git). `python -m harness.prepare_futures_holdout --download` reproduce la descarga y validacion. Un hueco o checksum fallido detiene el proceso.

`python -m harness.run_futures_replay` devuelve `Gate REAL ROJO: faltan snapshots historicos ...; winrate OOS indefinido`. No se calcula metrica para una decision que no puede reconstruirse sin los estados historicos que produccion usa.

Pendiente para un gate valido: snapshots historicos de libro/OI/force orders que usa la decision de produccion; filtros del contrato vigentes durante el holdout; baseline aleatorio con la misma billetera, oportunidades y costes; paridad de salidas bot/replay; testnet; auditoria independiente. `assess_live_gate` rechaza cualquier faltante. La clave `BINANCE_DB_FERNET_KEY` no esta presente en el entorno de esta sesion; no reiniciar ni migrar credenciales hasta provisionarla fuera del repositorio y comprobar que desencripta la cuenta.

Regla estadistica fijada antes de examinar el holdout: minimo 30 cierres, expectativa neta positiva con taker stress, PF > 1, maxDD <= 8 %, superar p95 aleatorio y OK auditor. Winrate = cierres con PnL neto > 0 / todos los cierres. Si falla cualquier control, REAL sigue bloqueado. Ningun numero del harness historico Spot mide el bot Futures MARKET actual.
