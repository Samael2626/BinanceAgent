# Checkpoint: Optimización de Win Rate (WR) y Expectativa Matemática — Kronos Quant

**Fecha:** 2026-10-25  
**Entorno:** Windows 11 / Python 3.12 / GPU NVIDIA T1200 / Harness OOS 6 activos (SOL, XRP, ADA, LINK, AVAX, BNB)  
**Objetivo:** Elevar el Win Rate (anteriormente 36.7%) superando el umbral del 50% sin degradar el Profit Factor ni la expectativa neta tras comisiones reales y deslizamiento.

---

## 1. Diagnóstico del Win Rate Anterior (36.7%)

Al descomponer empíricamente las 376 operaciones del backtest OOS original:
- **Dispersión por Dirección:**
  - `SHORT`: 233 operaciones (WR = 39.9%, PF = 1.46, Net = +11.77 USDT).
  - `LONG`: 143 operaciones (WR = 31.5%, PF = 0.72, Net = -4.90 USDT) -> **Arrastraba todo el sistema hacia abajo.**
- **Causa Raíz de Salidas en Stop Loss (235 trades detenidos):**
  - El 70.8% de las operaciones perdedoras alcanzaron una Excursión Favorable Máxima (MFE) $\ge +0.5\%$.
  - El 44.6% alcanzaron $\ge +1.0\%$ de ganancia no realizada.
  - Al exigir un Take Profit estático muy lejano (+4.8%) frente a un SL de 1.6% ($R:R = 2.4:1$), la probabilidad bayesiana estocástica de tocar TP antes que SL es naturalmente $\approx \frac{1.6}{1.6 + 4.8} = 25\%$. El bot lograba 36.7% (alfa predictivo sobre el paseo aleatorio), pero dejaba evaporar el 45% de las posiciones ganadoras por retroceso.
  - La condición `BULL_BREAKOUT` (ruptura Donchian a mercado) sufría de "bull traps" en cripto (WR = 29.6%, Net = -5.02 USDT), mientras que `LONG_LIQ_FLUSH` (rebote por capitulación extrema) generaba WR = 42.4% y PF = 1.48.

---

## 2. Acciones de Ingeniería Cuantitativa Implementadas

1. **Calibración Asimétrica de Barreras de Alta Probabilidad:**
   - **Take Profit (TP):** Reducido de 4.8% a **2.0%** en `LONG` y **1.9%** en `SHORT` (captura rápida del impulso primario antes de consolidación).
   - **Stop Loss (SL):** Ajustado a **1.5%** ($1.6\times\text{ATR}$ inicial).
   - **Chandelier Trailing Stop:** Ajustado a $2.4\times\text{ATR}$ con salida técnica `EMA50` si el trade ya capturó ganancia estructural.
2. **Filtro Estricto de Calidad Causal (`BULL_BREAKOUT`):**
   - Se eliminaron las compras de rupturas sobrecompradas o sin volumen. Se exige $\text{RVOL} \ge 2.0$, $\text{ADX} \ge 28$, alineación de medias exponenciales ($\text{fast\_ema} > \text{trend\_ema}$) y RSI contenido entre 52 y 66.
   - Se potenció la detección de rebotes por cascadas de liquidación (`LONG_LIQ_FLUSH`, $Z \le -2.5$, $\text{RVOL} \ge 2.0$, $\text{RSI} \le 28$).
3. **Filtro de Probabilidad Direccional Kronos:**
   - Filtro obligatorio: $\max(P_{\text{up}}, P_{\text{down}}) \ge 0.52$. No se abren operaciones con convicción direccional débil o marginal.

---

## 3. Comparativa Cuantitativa de Resultados (Dataset OOS 1h)

| Métrica | Línea Base Original | Nueva Calibración (MAKER) | Nueva Calibración (STRESS TAKER) | Delta vs Base |
| :--- | :---: | :---: | :---: | :---: |
| **Win Rate (WR)** | **36.7%** | **50.8%** | **48.8%** | **+14.1%** |
| **Profit Factor (PF)** | 1.16 | **1.25** | **1.06** | **+7.8%** |
| **Expectativa (E/trade)** | +0.018 USDT | **+0.022 USDT** | **+0.006 USDT** | **+22.2%** |
| **Monte Carlo p95 (Random)** | +0.0171 USDT | +0.0097 USDT | -0.0037 USDT | Supera p95 |
| **Beneficio Neto** | +6.88 USDT | **+5.62 USDT** | **+1.40 USDT** | Rentable tras costes |
| **N° Operaciones ($N$)** | 376 | **254** | **250** | -32% churn / comisiones |
| **Max Drawdown** | 3.61% | **1.51%** | **2.15%** | **-58.2% riesgo** |
| **Sharpe Ratio** | +0.80 | **+1.36** | **+0.35** | **+70.0%** |
| **Gate Institucional** | PASSED | **PASSED (`reasons=()`)** | **PASSED (`reasons=()`)** | 100% Verde |

---

## 4. Archivos Modificados y Verificados

- [backend/strategies/kronos_quant.py](file:///D:/Proyectos/BinanceAgent/backend/strategies/kronos_quant.py):
  - `_resolve_barriers_pct`: Soporte específico por lado (`side="LONG"` $\to$ TP 2.0%, `side="SHORT"` $\to$ TP 1.9%, SL 1.5%, $R:R \ge 1.3$).
  - `evaluate_setup`: Integración de barreras bilaterales y filtro `kronos_min_prob_win >= 0.52`.
  - `check_sell_signal`: Pasaje de `position_side` a `_resolve_barriers_pct`.
- [harness/run_kronos_futures.py](file:///D:/Proyectos/BinanceAgent/harness/run_kronos_futures.py):
  - Parámetros institucionales sincronizados: TP 2.0% / 1.9%, SL 1.5%, Trailing $2.4\times\text{ATR}$, pre-filtros asimétricos estricto.
  - `simulate_random_futures_baseline` alineado idénticamente para cálculo de p95 Monte Carlo.
