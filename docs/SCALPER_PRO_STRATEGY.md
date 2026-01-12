# 🚀 Estrategia: Scalper-PRO (Basada en RSI + MACD)

Esta estrategia está diseñada para capturar reversiones de momentum de alta frecuencia. Utiliza una combinación de **RSI** para identificar condiciones de sobreventa y el **Histograma de MACD** para confirmar la recuperación del precio antes de entrar.

## 🧠 Lógica de Operación

La estrategia prioriza la precisión de la entrada sobre la frecuencia pura, esperando a que el momentum bajista se agote.

### 🟢 Gatillo de Compra (BUY)
El bot ejecutará una compra cuando se cumplan **todas** estas condiciones simultáneamente:
1.  **RSI Bajo**: El RSI actual debe ser menor al valor configurado (Ej: `< 30`).
2.  **Confirmación de Momentum (MACD)**: El histograma de MACD debe ser mayor a 0 (`macd_hist > 0`).
    *   *Nota*: Esto asegura que no estamos comprando mientras el precio sigue cayendo libremente; esperamos a que la presión de venta disminuya.
3.  **Filtro Lateral (Global)**: La estrategia está sujeta al filtro de mercado lateral del bot. No comprará si el **ADX < 20** o si la volatilidad es extremadamente baja.

### 🔴 Gatillo de Venta (SELL)
El bot venderá la posición cuando se cumpla **cualquiera** de estas condiciones:
1.  **Trailing Stop (Prioritario)**: Si está activado, el bot seguirá el precio al alza y cerrará la posición si retrocede el porcentaje configurado. Esta es la salida principal recomendada para Scalper-PRO.
2.  **RSI Alto**: El RSI cruza por encima del límite de venta configurado (Ej: `> 60`).
3.  **Take Profit Fijo**: Si se alcanza el objetivo de ganancia porcentual configurado.

## 🛠️ Parámetros Recomendados

| Parámetro | Valor Sugerido | Razón |
| :--- | :--- | :--- |
| **Intervalo** | `1m` | Necesario para detectar cambios rápidos de momentum. |
| **Compra RSI** | `35 - 40` | Dado que el MACD ya filtra la caída, podemos ser un poco más laxos con el RSI. |
| **Venta RSI** | `60 - 65` | Salidas rápidas para mantener el ciclo de trading activo. |
| **Trailing Stop %**| `0.5% - 1.0%` | Permite capturar rachas alcistas extendidas tras el rebote. |
| **DCA Distancia %**| `1.0% - 1.5%` | Protege contra la continuación de la tendencia bajista. |

## ⚠️ Advertencia de Riesgo
Al ser una estrategia que busca rebotes:
-   **Confirmación MACD**: En caídas muy lentas o mercados muy laterales, el MACD puede tardar en dar señal.
-   **DCA Esencial**: Se recomienda tener activado el **DCA** para manejar retrocesos si el primer rebote falla.

---
*Fuente de Verdad: `backend/strategies/smart_scalper.py`*
*Documentación actualizada automáticamente para reflejar la implementación real.*
