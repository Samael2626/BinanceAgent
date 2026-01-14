# Documentación del Módulo Predictivo 🔮

Este documento explica cómo funciona el "Cerebro" predictivo del bot y qué significan las señales que genera.

## Conceptos Clave

### 1. Score de Mercado (0-100)
Es una puntuación global de la salud del mercado.
- **> 65 (Alcista Fuerte)**: El mercado tiene fuerza, buen momento para compras.
- **< 35 (Bajista Fuerte)**: El mercado está cayendo con fuerza, cuidado con las compras, mejor buscar ventas.
- **50 (Neutral)**: Mercado lateral o indeciso.

### 2. RVOL (Volumen Relativo)
Mide el interés actual comparado con el promedio.
- Si el RVOL es **1.0**, el volumen es normal.
- Si el RVOL es **> 1.2** (120%), hay un interés inusual. Esto suele preceder a movimientos grandes.
- **Interpretación**: Un RVOL alto valida (confirma) una ruptura de precio.

### 3. Divergencias (RSI)
Son las señales más potentes de una posible reversión.
- **Divergencia Alcista (Bull)**: El precio cae (hace nuevos mínimos), pero el RSI sube. Indica que la presión de venta se está agotando. -> *Posible rebote al alza.*
- **Divergencia Bajista (Bear)**: El precio sube (hace nuevos máximos), pero el RSI baja. Indica que la compra se está debilitando. -> *Posible caída.*

### 4. Probabilidad de Ruptura
Estima la probabilidad de que el precio rompa un rango lateral.
Se basa en la "Compresión" (cuando las Bandas de Bollinger se estrechan mucho) y el aumento de volumen.
- **> 60%**: Prepararse para un movimiento explosivo inminente.

### 5. Zonas de Liquidez
Son precios donde históricamente ha habido muchas órdenes.
- **Soporte**: Un "suelo" donde el precio suele rebotar hacia arriba.
- **Resistencia/Target**: Un "techo" donde el precio suele ser rechazado hacia abajo.

---

## Cómo leer el Resumen del Bot

### No más códigos oscuros 🖥️
Ahora, directamente en el Dashboard del bot, verás una sección llamada **"Cerebro Predictivo"**. Esta sección traduce todos los números complejos a un lenguaje que cualquier trader puede entender.

El bot genera un resumen en texto plano como este:

> • Estado: Alcista Moderado 📈 (Score: 60/100)
> • Volumen: Alto (1.5x promedio). ¡Atentos a movimientos bruscos!
> • Divergencias: ⚠️ Div Alcista (Bull)
> • Prob. Ruptura: Alta (70%). El precio está comprimido.

Esto significa: "El mercado está sano, hay mucho volumen entrando, hemos detectado una posible reversión al alza y el precio está a punto de explotar". **Es una configuración de compra muy fuerte.**

### Elementos Visuales
- **Radar de Mercado**: Una representación visual del score de salud y probabilidad de ruptura.
- **Tarjetas de Métricas**: Valores rápidos de RVOL, Velocidad, Sesión y Ruptura.
- **Resumen del Analista**: El texto explicativo generado por el motor predictivo.

