# BinanceAgent — Bot trading spot Binance

## Stack
- Python 3.12 / FastAPI / python-binance / SQLite
- React 19 + Vite 7 + Three.js + lightweight-charts
- PostgreSQL (migrando)
- pytest + harness de backtest

## Estructura
Monorepo con `backend/` (FastAPI) y `frontend/` (React/Vite).
Scanner -> estrategia -> risk engine -> binance_wrapper -> orden MARKET.
Una posicion a la vez. Multi-usuario.

## Skills
- binanceagent-dev: desarrollo general backend/frontend
- binanceagent-auditor: auditoria read-only bugs + integridad harness
- binanceagent-ops: operacion del bot en vivo
- binanceagent-quant: backtest harness + validacion estrategia

## Reglas
- Nada a REAL sin: harness verde (expectancy positiva OOS + stress slippage) + OK auditor
- Una posicion a la vez. Single instancia backend.
- .env UTF-8 sin BOM (python-dotenv crashea con BOM)
- PYTHONIOENCODING=utf-8 obligatorio en Windows
- No loguear API keys ni secrets
- Cache con pickle, no parquet (pyarrow no disponible)
- Cambios de logica trading -> validar con binanceagent-quant
- Capital > frecuencia > ego

## Produccion
- Bot corriendo en localhost:8000
- Usuario activo: samael (~47 USDT)
- Frontend en localhost:3001, Vite dev en 3002
- DB: backend/bot_data.db (SQLite)

## Flujo
1. Leer codigo real antes de tocar. No asumir de memoria.
2. Elegir skill segun sintoma.
3. Hacer cambio minimo.
4. Correr compileall backend + tests tras tocar.
5. Reportar cambio, prueba y riesgo restante.
6. Si afecta trading -> harness + auditor antes de deploy.
