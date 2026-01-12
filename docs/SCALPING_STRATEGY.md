# 🦅 Estrategia: Scalping Controlado Automático

> **"La verdad incómoda: Los grandes esperan movimientos grandes. Los pequeños viven del ruido."** -- *Filosofía de Crecimiento de Cuenta Pequeña*

Este documento detalla la configuración y lógica para transformar el bot en una máquina de consistencia de alta frecuencia.

---

## 🧠 Filosofía de Operación
*   **❌ Error Común**: Esperar subidas del 2-3% en BTC. Es lento y bloquea tu capital por días.
*   **✅ El Camino**: Capturar **0.4% - 0.5%** muchas veces al día.
*   **Objetivo**: No busques la "gloria". Busca la **consistencia**.
*   **Meta**: Ejecutar ciclos rápidos de compra/venta para aprovechar el interés compuesto.

---

## ⚙️ Configuración Sugerida

Aplica estos valores en el panel de **Configuración** del bot.

### 1. Parámetros de Mercado y Riesgo
| Parámetro | Valor | Razón |
| :--- | :--- | :--- |
| **Intervalo (Vela)** | `1m` | Necesario para detectar micro-movimientos. |
| **Take Profit** | `0.5%` | Objetivo rápido y realista para scalping. |
| **Stop Loss** | `0.6` | **Importante**: Ponlo positivo. El bot corta pérdidas ahí. |
| **DCA / Sniper** | `OFF` | Para esta estrategia, mejor una entrada precisa. |
| **Sell Mode** | `Full` | Vender todo al tocar el objetivo para liberar capital. |

### 2. Indicadores Técnicos
| Parámetro | Valor | Nota |
| :--- | :--- | :--- |
| **RSI Compra** | `35` | Entra un poco antes que el estándar (30). |
| **RSI Venta** | `65` | Salida rápida ante señales de sobrecompra. |
| **EMA Length** | `55` | Filtro de tendencia rápida. |
| **MACD** | `8 / 21 / 5` | Configuración ultra-rápida para 1 minuto. |

---

## 💡 Recomendación Estelar: Scalping Maestro
Si quieres que el bot sea **más inteligente**, selecciona esta estrategia en el panel:

> [!TIP]
> **Estrategia Activa**: `Scalping Maestro (BBands + Vol + Tendencia)`
>
> **¿Qué la hace mejor?**
> *   **Bollinger Bands**: El bot analiza si el precio se salió de su rango normal para comprar el rebote.
> *   **Volumen**: Solo entra si hay "fuego" (actividad) en el mercado, evitando señales falsas.
> *   **EMA 55**: Solo compra si el precio está por encima de la media, asegurando que vas a favor del mercado.

---

## 📉 Lógica del "Scalper"
Con esta configuración, el bot:
1.  Detecta una micro-caída con volumen.
2.  Entra rápido cuando toca la banda inferior o RSI 35.
3.  Cierra la operación apenas ve un 0.5% de profit o toca la banda superior.
4.  **Repite el ciclo**. 

### Matemática de Cuenta Pequeña
$$ 0.5\% \times 5 \text{ trades exitosos} = 2.5\% \text{ diario} $$
*Hacer esto cada día es cómo se rompe el techo de una cuenta pequeña.*

---

## 📋 Proceso de Activación
1.  Asegúrate de que el bot esté en **1m**.
2.  Configura el **Stop Loss** en `0.6` y **Take Profit** en `0.5`.
3.  En la sección de indicadores, pon RSI `35 / 65`.
4.  Selecciona **Scalping Maestro** en el menú de Estrategia Activa.
5.  **Dale a Guardar y observa la terminal.** 

> [!WARNING]
> Si en 48 horas no ves actividad, revisa que el mercado tenga volatilidad. Si el precio no se mueve, el bot (inteligentemente) no arriesgará tu dinero.
