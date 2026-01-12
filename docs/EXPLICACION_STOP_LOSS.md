# 🛡️ Guía del Stop Loss: Protegiendo tu Capital

El **Stop Loss** (Cierre de Pérdida) es la herramienta más importante para cualquier trader. Es como un **seguro automático** para tu dinero.

---

## 🧐 ¿Qué es eso de "Stop Loss"?
Imagina que compras un diamante por $100 esperando que suba de precio. Pero, por si acaso baja, le dices a un guardián: *"Si el precio llega a bajar a $98, vende el diamante inmediatamente. No quiero arriesgarme a perder más de $2"*.

Eso es el Stop Loss: una orden de **vender por emergencia** cuando el mercado se mueve en tu contra.

---

## ⚙️ ¿Cómo funciona en tu bot?

Tu bot sigue estos 3 pasos exactos:

1.  **Recuerda tu Precio de Entrada**: El momento en que el bot hace una compra (ya sea por RSI o manual), guarda ese precio.
    *   *Ejemplo: Compraste BTC a $60,000.*

2.  **Calcula tu "Línea Roja"**: Según el porcentaje (%) que tú pongas en el panel amarillo, el bot calcula el precio límite.
    *   *Si pones **1% de Stop Loss**:*
    *   *Saca la cuenta: $60,000 - 1% = **$59,400**.*
    *   *Esta es tu "Línea Roja".*

3.  **Vigilancia 24/7**: Cada 3 segundos, el bot mira el precio actual del mercado.
    *   Si el precio es $59,800... **No hace nada** (sigues dentro).
    *   Si el precio toca o baja de **$59,400**... **¡ZAS!** El bot lanza una orden de venta inmediata para salvar el resto de tu dinero.

---

## 📊 Ejemplo Real en el Bot

| Acción | Precio | Nota |
| :--- | :--- | :--- |
| **COMPRA** | $30,000 | El bot guarda "$30,000" como entrada. |
| **Configuración** | 2% SL | Tu "Línea Roja" se fija en $29,400. |
| **Mercado Baja** | $29,600 | El bot vigila, pero no vende. |
| **Mercado Cae** | $29,350 | **ACCIONADO**: Vende al instante. |

---

## ⌨️ ¿Cómo usarlo en la Pantalla?

1.  Busca el panel amarillo que dice **"🛡️ Gestión de Riesgo: Stop Loss"**.
2.  En el cuadro de texto, escribe el porcentaje de pérdida que estás dispuesto a aceptar.
    *   **Sugerencia pro**: Entre 1% y 3% es lo que usan la mayoría de traders.
    *   **Poner 0**: Significa que el Stop Loss está **desactivado**.
3.  El bot guardará este valor automáticamente.

### ⚠️ Importante
El Stop Loss es una **Venta a Mercado**. Esto significa que el bot vende al precio que haya en ese momento para asegurar que salgas rápido de la operación antes de que el precio siga cayendo.

---
*Con un Stop Loss bien configurado, nunca te despertarás con la sorpresa de que tu balance está en cero.*
