# 🚀 Guía Completa: Binance Trading Bot Pro

Esta guía te explicará detalladamente cómo funciona tu bot, qué herramientas tiene y cómo ejecutarlo correctamente.

---

## 🛠️ Requisitos de Instalación

### 1. Backend (Servidor Python)
El cerebro del bot está construido con **FastAPI**.
- **Entorno Virtual**: Se recomienda usar `.venv`.
- **Dependencias**: `pandas`, `pandas_ta`, `python-binance`, `fastapi`, `uvicorn`, `sqlite3`.
- **Ejecución**:
  ```bash
  cd backend
  uvicorn main:app --reload
  ```

### 2. Frontend (Panel de Control Visual)
La interfaz gráfica está hecha con **React + Vite**.
- **Dependencias**: `lightweight-charts` (para los gráficos profesionales).
- **Ejecución**:
  ```bash
  cd frontend
  npm install
  npm run dev
  ```

---

## 🧠 Características Principales

### 1. Sistema de Login Dinámico 🔐
No necesitas editar archivos `.env` manualmente. Al abrir el bot, verás una pantalla de login para ingresar tu **API Key** y **API Secret** de Binance Testnet.

### 2. Monitorización en Tiempo Real 📈
- **Gráfico de Velas**: Visualiza el movimiento del mercado en tiempo real usando el motor de TradingView (`lightweight-charts`).
- **Métricas Vivas**: Saldo, PnL (Ganancias/Pérdidas) y precio actual actualizados cada 3 segundos.
- **RSI Dinámico**: El indicador de fuerza relativa se calcula al vuelo para detectar oportunidades.

### 3. Selector de Estrategias ⚙️
El bot ahora es modular:
- **RSI Estándar (Automático)**: El bot compra cuando el RSI es bajo (sobreventa) y vende cuando es alto (sobrecompra).
- **Modo Manual**: El bot te permite comprar/vender tú mismo, pero manteniendo las protecciones de seguridad activas.

### 4. Gestión de Riesgos: Stop Loss 🛡️
Esta es la herramienta más importante para un profesional.
- **Cómo funciona**: Al activarlo, el bot recuerda el precio de compra. Si el mercado baja del porcentaje configurado (ej: 1.5%), el bot vende **inmediatamente** (Market Order) para evitar que pierdas más capital.
- **Persistencia**: La configuración se guarda en una base de datos SQLite (`bot_data.db`), por lo que no se borra al cerrar el bot.

---

## 📂 Estructura del Proyecto

```text
Binance/
├── backend/
│   ├── bot_logic.py     # Lógica de trading y Stop Loss
│   ├── binance_wrapper.py # Conexión oficial con Binance API
│   ├── main.py          # Servidor API (Endpoints)
│   ├── database.py      # Persistencia de datos (SQLite)
│   └── bot_data.db      # Tus configuraciones y trades guardados
└── frontend/
    └── src/
        ├── App.jsx      # Panel de control principal
        └── MarketChart.jsx # Componente del gráfico profesional
```

---

## 💡 Consejos Pro
- **Testnet Primero**: Usa siempre llaves de la Testnet de Binance antes de pasar a Real.
- **Cero (0) = Desactivado**: En el campo de Stop Loss, poner 0 desactivará la protección.
- **Historial Desplegable**: Haz clic en el título de "Trade History" para ocultar/mostrar la tabla y tener más espacio en pantalla.

---
*Bot desarrollado para trading autónomo y gestión de capital pro.*
